#!/usr/bin/env python3
"""Read-only diagnostic: find where the '爬虫监控' emails live in Gmail and
which data dates they cover. Does NOT modify or commit any data."""
import email
import html
import imaplib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from email.utils import parsedate_to_datetime

IMAP_HOST = os.environ.get("GMAIL_IMAP_HOST", "imap.gmail.com")
IMAP_PORT = int(os.environ.get("GMAIL_IMAP_PORT", "993"))
USER = os.environ.get("GMAIL_USER", "")
PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
SUBJECT_FILTER = os.environ.get("EMAIL_SUBJECT_FILTER", "爬虫监控")
SINCE_DATE = os.environ.get("SINCE_DATE", "01-May-2026")  # IMAP dd-Mon-yyyy


def dec(value):
    if not value:
        return ""
    out = []
    for part, charset in decode_header(value):
        if isinstance(part, bytes):
            out.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            out.append(part)
    return "".join(out)


def msg_date(value):
    try:
        p = parsedate_to_datetime(value)
    except Exception:
        return None
    if p is None:
        return None
    if p.tzinfo is None:
        p = p.replace(tzinfo=timezone.utc)
    return p.astimezone(timezone.utc)


def body_text(msg):
    if msg.is_multipart():
        texts, htmls = [], []
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            try:
                t = payload.decode(charset, errors="replace")
            except LookupError:
                t = payload.decode("utf-8", errors="replace")
            if part.get_content_type() == "text/plain":
                texts.append(t)
            elif part.get_content_type() == "text/html":
                htmls.append(t)
        return "\n".join(texts) if texts else "\n".join(htmls)
    payload = msg.get_payload(decode=True)
    if payload is None:
        return ""
    charset = msg.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def strip_html(t):
    return re.sub(r"<[^>]+>", "", html.unescape(t))


def extract_json(text):
    if not text:
        return None
    text = strip_html(text)
    for start in range(len(text)):
        if text[start] != "{":
            continue
        depth = 0
        for end in range(start, len(text)):
            c = text[end]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    cand = text[start:end + 1].strip()
                    try:
                        data = json.loads(cand)
                    except json.JSONDecodeError:
                        break
                    if isinstance(data, dict):
                        return data
                    break
    return None


def list_folders(mail):
    print("=== FOLDERS ===")
    status, boxes = mail.list()
    all_mail = None
    names = []
    if status == "OK":
        for raw in boxes:
            line = raw.decode(errors="replace") if isinstance(raw, bytes) else str(raw)
            print("  " + line)
            # flags are in parentheses at the start, name is the last quoted token
            m = re.search(r'"([^"]*)"\s*$', line)
            name = m.group(1) if m else line.split()[-1]
            names.append(name)
            if "\\All" in line:
                all_mail = name
    return names, all_mail


def scan_folder(mail, folder):
    try:
        status, _ = mail.select(f'"{folder}"', readonly=True)
    except Exception as e:
        print(f"  [select failed] {folder}: {e}")
        return []
    if status != "OK":
        print(f"  [select not OK] {folder}")
        return []
    status, data = mail.search(None, "SINCE", SINCE_DATE)
    if status != "OK" or not data or not data[0]:
        print(f"  [{folder}] no messages since {SINCE_DATE}")
        return []
    ids = data[0].split()
    matches = []
    for mid in ids:
        status, hd = mail.fetch(mid, "(BODY.PEEK[HEADER.FIELDS (SUBJECT DATE)])")
        if status != "OK" or not hd:
            continue
        hbytes = None
        for item in hd:
            if isinstance(item, tuple):
                hbytes = item[1]
                break
        if not hbytes:
            continue
        h = email.message_from_bytes(hbytes)
        subj = dec(h.get("Subject"))
        if SUBJECT_FILTER not in subj:
            continue
        d = msg_date(h.get("Date"))
        matches.append((d, mid, subj))
    print(f"  [{folder}] scanned {len(ids)} msgs, {len(matches)} match subject '{SUBJECT_FILTER}'")
    return matches


def main():
    if not USER or not PASSWORD:
        print("Missing credentials")
        return 2
    print(f"Login {USER} @ {IMAP_HOST}")
    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    mail.login(USER, PASSWORD)

    names, all_mail = list_folders(mail)
    print(f"\nAll Mail folder detected: {all_mail!r}\n")

    # Prefer All Mail (covers inbox + archived + labeled); fall back to INBOX.
    targets = []
    if all_mail:
        targets.append(all_mail)
    targets.append("INBOX")
    # de-dup preserving order
    seen = set()
    targets = [t for t in targets if not (t in seen or seen.add(t))]

    all_matches = []
    print("=== SCAN ===")
    for folder in targets:
        all_matches.extend([(folder,) + m for m in scan_folder(mail, folder)])

    print("\n=== MATCHED EMAILS (folder | received | subject) ===")
    all_matches.sort(key=lambda x: (x[1] or datetime.min.replace(tzinfo=timezone.utc)))
    data_dates = set()
    for folder, d, mid, subj in all_matches:
        dstr = d.isoformat() if d else "?"
        # fetch body to see which data dates it carries
        status, md = mail.select(f'"{folder}"', readonly=True)
        status, msgd = mail.fetch(mid, "(RFC822)")
        carried = []
        if status == "OK" and msgd:
            raw = None
            for item in msgd:
                if isinstance(item, tuple):
                    raw = item[1]
                    break
            if raw:
                msg = email.message_from_bytes(raw)
                payload = extract_json(body_text(msg))
                if isinstance(payload, dict):
                    ds = set()
                    for plat, dates in payload.items():
                        if isinstance(dates, dict):
                            ds.update(dates.keys())
                    carried = sorted(ds)
                    data_dates.update(ds)
        print(f"  {folder} | {dstr} | {subj} | data-dates={carried}")

    print("\n=== SUMMARY ===")
    print(f"Total matched emails: {len(all_matches)}")
    print(f"Distinct data-dates found: {len(data_dates)}")
    if data_dates:
        print(f"Range: {min(data_dates)} .. {max(data_dates)}")
        print("All data-dates:", ", ".join(sorted(data_dates)))

    # Compare against what's actually missing in job-data.json (as of 2026-07-02)
    targets_missing = [
        "2026-05-04", "2026-05-08", "2026-05-19", "2026-05-20",
        "2026-06-10", "2026-06-11", "2026-06-12", "2026-06-13", "2026-06-14",
        "2026-06-15", "2026-06-16", "2026-06-17", "2026-06-18", "2026-06-19",
        "2026-06-20", "2026-06-21", "2026-06-22", "2026-06-24", "2026-06-26",
        "2026-06-29", "2026-06-30", "2026-07-01", "2026-07-02",
    ]
    covered = sorted(d for d in targets_missing if d in data_dates)
    still = sorted(d for d in targets_missing if d not in data_dates)
    print(f"\nOf {len(targets_missing)} missing target dates: {len(covered)} recoverable, {len(still)} not in mailbox")
    print("Recoverable:", ", ".join(covered) if covered else "(none)")
    print("Not found  :", ", ".join(still) if still else "(none)")

    mail.logout()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
