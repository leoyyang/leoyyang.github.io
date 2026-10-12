#!/usr/bin/env python3
"""Validate a daily aggregate and append it without rewriting historical values."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

TZ = dt.timezone(dt.timedelta(hours=8))
PLATFORMS = {'58', 'zl', 'qcwy', 'boss', 'liepin'}
METHOD = 'stored-records-by-crawl-time-v1'

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)

def validate(payload, now=None):
    now = now or dt.datetime.now(TZ)
    expected = {'schema_version', 'report_date', 'timezone', 'period_start', 'period_end',
                'generated_at', 'method', 'complete', 'counts'}
    if not isinstance(payload, dict) or set(payload) != expected:
        raise ValueError('Unexpected aggregate schema')
    if type(payload['schema_version']) is not int or payload['schema_version'] != 1:
        raise ValueError('Unsupported schema version')
    if payload['timezone'] != 'Asia/Shanghai' or payload['method'] != METHOD or payload['complete'] is not True:
        raise ValueError('Unrecognized method/timezone or incomplete aggregate')
    day = dt.date.fromisoformat(payload['report_date'])
    if day.isoformat() != payload['report_date'] or day >= now.astimezone(TZ).date():
        raise ValueError('Report date must be a completed day')
    if day < now.astimezone(TZ).date() - dt.timedelta(days=7):
        raise ValueError('Daily import window exceeded; use a reviewed backfill')
    start = dt.datetime.combine(day, dt.time(), TZ)
    if payload['period_start'] != start.isoformat() or payload['period_end'] != (start + dt.timedelta(days=1)).isoformat():
        raise ValueError('Incorrect daily interval')
    generated = dt.datetime.fromisoformat(payload['generated_at'].replace('Z', '+00:00'))
    if generated.tzinfo is None or generated < start + dt.timedelta(days=1) or generated > now + dt.timedelta(minutes=10):
        raise ValueError('Invalid generation timestamp')
    counts = payload['counts']
    if not isinstance(counts, dict) or set(counts) != PLATFORMS:
        raise ValueError('All five platforms are required')
    if any(type(v) is not int or v < 0 or v > 9007199254740991 for v in counts.values()):
        raise ValueError('Counts must be nonnegative safe integers')
    return day.isoformat()

def merge(existing, payload):
    day = payload['report_date']
    if not isinstance(existing, dict) or set(existing) != PLATFORMS:
        raise ValueError('Unexpected existing website schema')
    result = json.loads(json.dumps(existing))
    # Validate all conflicts before changing any file.
    for platform in sorted(PLATFORMS):
        series = result[platform]
        if not isinstance(series, dict):
            raise ValueError('Invalid existing series')
        if day in series and (type(series[day]) is not int or series[day] != payload['counts'][platform]):
            raise ValueError('Historical value conflict: {} {}'.format(platform, day))
        latest = max(series, default='')
        if day not in series and latest and day != (dt.date.fromisoformat(latest) + dt.timedelta(days=1)).isoformat():
            raise ValueError('Refusing to create a gap in {}'.format(platform))
    for platform in sorted(PLATFORMS):
        result[platform][day] = payload['counts'][platform]
    return result

def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

def freshness(existing, now=None):
    now = now or dt.datetime.now(TZ)
    yesterday = (now.astimezone(TZ).date() - dt.timedelta(days=1)).isoformat()
    if set(existing) != PLATFORMS or any(yesterday not in existing[k] or type(existing[k][yesterday]) is not int or existing[k][yesterday] < 0 for k in PLATFORMS):
        raise ValueError('Missing complete daily data for {}'.format(yesterday))
    return yesterday

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--payload')
    parser.add_argument('--check-freshness', action='store_true')
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    root = Path(args.root)
    data_path = root / 'job-tracker/data/job-data.json'
    existing = json.loads(data_path.read_text())
    if args.check_freshness:
        print('Fresh complete data:', freshness(existing))
        return
    if args.payload:
        payload = json.loads(Path(args.payload).read_text())
    else:
        event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
        payload = json.loads(event['inputs']['aggregate'])
        if event['inputs'].get('report_date') != payload.get('report_date'):
            raise ValueError('Input date mismatch')
    day = validate(payload)
    merged = merge(existing, payload)
    receipt_path = root / ('job-tracker/data/ingestion/' + day + '.json')
    digest = hashlib.sha256(canonical(payload).encode()).hexdigest()
    receipt = {'aggregate_sha256': digest, 'aggregate': payload}
    if receipt_path.exists() and json.loads(receipt_path.read_text()) != receipt:
        raise ValueError('Conflicting immutable daily aggregate')
    if args.validate_only:
        print('Validated:', day, digest)
        return
    if merged != existing:
        write_json(data_path, merged)
    if not receipt_path.exists():
        write_json(receipt_path, receipt)
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write('update_date={}\n'.format(day))
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as f:
            f.write('Validated complete daily aggregate: **{}**. SHA-256 `{}`. Existing values preserved.\n'.format(day, digest))
    print('Accepted aggregate:', day, digest)

if __name__ == '__main__':
    main()
