#!/usr/bin/env python3
import email
import html
import imaplib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from email.message import Message
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(os.environ.get("GITHUB_WORKSPACE", Path.cwd()))
DATA_FILE = REPO_ROOT / "job-tracker/data/job-data.json"

IMAP_HOST = os.environ.get("GMAIL_IMAP_HOST") or os.environ.get("EMAIL_HOST") or "imap.gmail.com"
IMAP_PORT = int(os.environ.get("GMAIL_IMAP_PORT") or os.environ.get("EMAIL_PORT") or "993")
EMAIL_USER = os.environ.get("GMAIL_USER") or os.environ.get("EMAIL_USER") or ""
EMAIL_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD") or os.environ.get("EMAIL_PASSWORD") or ""
EMAIL_FOLDER = os.environ.get("EMAIL_FOLDER", "INBOX")
EMAIL_SUBJECT_FILTER = os.environ.get("EMAIL_SUBJECT_FILTER", "")
EMAIL_SEARCH_DAYS = int(os.environ.get("EMAIL_SEARCH_DAYS", "3"))


def decode_mime_header(value: Optional[str]) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    decoded: list[str] = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


def parse_message_date(value: Optional[str]) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        parsed = parsedate_to_datetime(value)
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def extract_payload_text(msg: Message) -> str:
    if msg.is_multipart():
        text_parts = []
        html_parts = []
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            content_type = part.get_content_type()
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            try:
                text = payload.decode(charset, errors="replace")
            except LookupError:
                text = payload.decode("utf-8", errors="replace")
            if content_type == "text/plain":
                text_parts.append(text)
            elif content_type == "text/html":
                html_parts.append(text)
        if text_parts:
            return "\n".join(text_parts)
        if html_parts:
            return "\n".join(html_parts)
        return ""

    payload = msg.get_payload(decode=True)
    if payload is None:
        return ""
    charset = msg.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def strip_html(text: str) -> str:
    text = html.unescape(text)
    return re.sub(r"<[^>]+>", "", text)


def extract_json(text: str) -> Optional[Dict[str, Dict[str, int]]]:
    if not text:
        return None
    text = strip_html(text)
    for start in range(len(text)):
        if text[start] != "{":
            continue
        depth = 0
        for end in range(start, len(text)):
            char = text[end]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start : end + 1].strip()
                    try:
                        data = json.loads(candidate)
                    except json.JSONDecodeError:
                        break
                    if isinstance(data, dict):
                        return data
                    break
    return None


def load_existing_data() -> Dict[str, Dict[str, int]]:
    if not DATA_FILE.exists():
        return {}
    with DATA_FILE.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, dict):
        return data
    return {}


def save_data(data: Dict[str, Dict[str, int]]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=4, ensure_ascii=True)
        handle.write("\n")


def apply_updates(
    existing: Dict[str, Dict[str, int]], updates: Dict[str, Dict[str, int]]
) -> Tuple[bool, set]:
    changed = False
    updated_dates = set()
    for platform, dates in updates.items():
        if not isinstance(dates, dict):
            continue
        platform_key = str(platform)
        platform_data = existing.setdefault(platform_key, {})
        for date_key, value in dates.items():
            date_str = str(date_key)
            try:
                value_int = int(value)
            except (TypeError, ValueError):
                continue
            if platform_data.get(date_str) != value_int:
                platform_data[date_str] = value_int
                changed = True
                updated_dates.add(date_str)
    return changed, updated_dates


def folders_to_search(mail: imaplib.IMAP4_SSL) -> List[str]:
    """Determine which mailboxes to search.

    The monitoring emails do not reliably stay in INBOX: some are auto-archived
    (only in "All Mail") and some get flagged as spam (only in Spam). Detect the
    Gmail special folders by their IMAP special-use flags (\\All, \\Junk) so this
    works regardless of the account's display language, and always include INBOX.
    """
    folders: List[str] = []
    special: Dict[str, str] = {}
    status, boxes = mail.list()
    if status == "OK" and boxes:
        for raw in boxes:
            line = raw.decode(errors="replace") if isinstance(raw, bytes) else str(raw)
            match = re.search(r'"([^"]*)"\s*$', line)
            name = match.group(1) if match else line.split()[-1]
            if "\\All" in line:
                special["all"] = name
            elif "\\Junk" in line:
                special["junk"] = name
    for key in ("all", "junk"):
        if special.get(key):
            folders.append(special[key])
    folders.append(EMAIL_FOLDER)  # INBOX (or configured default) as a fallback
    seen: set = set()
    return [f for f in folders if not (f in seen or seen.add(f))]


def find_recent_messages(mail: imaplib.IMAP4_SSL, max_count: Optional[int] = None) -> List[email.message.Message]:
    """Return matching messages received within the search window.

    Searches every relevant folder, de-duplicates by Message-ID (a message can
    carry both the INBOX and All Mail labels), and returns messages sorted newest
    first. If *max_count* is given, only that many newest messages are returned.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=EMAIL_SEARCH_DAYS)).strftime("%d-%b-%Y")

    candidates = []  # (received_at, folder, message_id)
    seen_msgids: set = set()
    for folder in folders_to_search(mail):
        status, _ = mail.select(f'"{folder}"', readonly=True)
        if status != "OK":
            continue
        status, data = mail.search(None, "SINCE", since)
        if status != "OK" or not data or not data[0]:
            continue
        for message_id in data[0].split():
            status, header_data = mail.fetch(
                message_id, "(BODY.PEEK[HEADER.FIELDS (SUBJECT DATE MESSAGE-ID)])"
            )
            if status != "OK" or not header_data:
                continue
            header_bytes = None
            for item in header_data:
                if isinstance(item, tuple):
                    header_bytes = item[1]
                    break
            if not header_bytes:
                continue
            header_msg = email.message_from_bytes(header_bytes)
            subject = decode_mime_header(header_msg.get("Subject"))
            if EMAIL_SUBJECT_FILTER and EMAIL_SUBJECT_FILTER not in subject:
                continue
            msgid = (header_msg.get("Message-ID") or "").strip()
            dedup_key = msgid or f"{folder}:{message_id.decode() if isinstance(message_id, bytes) else message_id}"
            if dedup_key in seen_msgids:
                continue
            seen_msgids.add(dedup_key)
            received_at = parse_message_date(header_msg.get("Date"))
            candidates.append((received_at, folder, message_id))

    if not candidates:
        return []

    # Newest first
    candidates.sort(key=lambda item: item[0], reverse=True)
    if max_count is not None:
        candidates = candidates[:max_count]

    messages = []
    for _, folder, msg_id in candidates:
        # Re-select the folder this id belongs to before fetching the body.
        status, _ = mail.select(f'"{folder}"', readonly=True)
        if status != "OK":
            continue
        status, msg_data = mail.fetch(msg_id, "(RFC822)")
        if status != "OK" or not msg_data:
            continue
        raw_email = None
        for item in msg_data:
            if isinstance(item, tuple):
                raw_email = item[1]
                break
        if raw_email:
            messages.append(email.message_from_bytes(raw_email))
    return messages


def write_github_output(name: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


def main() -> int:
    if not EMAIL_USER or not EMAIL_PASSWORD:
        print("Missing Gmail credentials. Set GMAIL_USER and GMAIL_APP_PASSWORD.")
        return 2

    if EMAIL_SEARCH_DAYS < 1:
        print("EMAIL_SEARCH_DAYS must be at least 1.")
        return 2

    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    mail.login(EMAIL_USER, EMAIL_PASSWORD)

    try:
        messages = find_recent_messages(mail, max_count=None)
    finally:
        try:
            mail.close()
        except Exception:
            pass
        mail.logout()

    if not messages:
        print("No matching email found in the recent window.")
        return 0

    existing = load_existing_data()
    all_updated_dates: set = set()
    any_changed = False

    for i, message in enumerate(messages):
        subject = decode_mime_header(message.get("Subject"))
        print(f"Checking email {i + 1}/{len(messages)}: {subject}")

        body = extract_payload_text(message)
        updates = extract_json(body)
        if not updates:
            print("  No JSON payload, skipping.")
            continue

        changed, updated_dates = apply_updates(existing, updates)
        if changed:
            any_changed = True
            all_updated_dates.update(updated_dates)
            print(f"  New data found for: {', '.join(sorted(updated_dates))}")
        else:
            print("  Data already up to date, skipping.")

    if not any_changed:
        print("No changes needed in job-data.json.")
        return 0

    save_data(existing)
    if all_updated_dates:
        write_github_output("update_date", max(all_updated_dates))
    print(f"job-data.json updated with dates: {', '.join(sorted(all_updated_dates))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
