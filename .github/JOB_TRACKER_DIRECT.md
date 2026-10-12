# Job Tracker daily data

`Update Job Data` accepts a complete daily aggregate through `workflow_dispatch`.
It no longer searches an email inbox. The existing engineering monitor is independent.

The payload contains only public aggregate counts: schema version 1, a completed
Asia/Shanghai date and its exact midnight interval, generation time, method
`stored-records-by-crawl-time-v1`, `complete: true`, and all five platform counts.
Production credentials and raw job records must never enter the payload.

The importer rejects incomplete/current/future/older-than-seven-day payloads,
invalid counts, date gaps and conflicting historical values. Identical retries
are safe. Each accepted aggregate has an immutable receipt under
`job-tracker/data/ingestion/YYYY-MM-DD.json` with its SHA-256.

The recruitment server produces and submits the previous day's aggregate at
00:15 Beijing time, after the midnight boundary. It retries at 00:45 and 01:15;
an already-current website makes these runs harmless no-ops. The former management
host relay is disabled and is not needed at runtime.
The workflow is the only automated writer of website data, uses the existing
`PAGES_TOKEN` for publication, and serializes updates. The old Gmail Secrets are
no longer referenced by this workflow. The server uses a dedicated fine-grained
token scoped to this repository's Actions read/write permission plus required
Metadata read access, with no Contents write permission. Its expiry is 2027-10-12.
GitHub scopes this permission to a repository, not to one specific workflow.

The scheduled run at 03:17 Beijing time only checks that yesterday's data is
present. Missing data fails visibly instead of reporting an empty successful run.
External dispatch success alone does not prove publication: the producer checks
the Action result, the live receipt hash, and all five live counts.

Historical correction/backfill needs a separately reviewed change. Do not weaken
conflict validation or overwrite previous daily receipts to conceal a mismatch.
