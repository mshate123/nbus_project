# API Contract Tests

Contract tests must assert exact status, headers where relevant, and JSON shape. They run against the Compose API and proxy.

1. `GET /health` returns 200 and exactly `{status:"ok"}` without bearer.
2. `GET /ready` returns 200 `{status:"ready"}` after migration and 503 `{error}` while unavailable.
3. `/api/accounts` without bearer returns 401 `{error:string}`; valid bearer returns a JSON array, never `{items:...}`.
4. Every returned account contains `id`, `code`, `name`, `type`, `normal_balance`, `rate_tier`, `active`; tier is one of three authoritative values.
5. `/api/rate-schedule` returns exactly three objects and exact decimal strings.
6. Unknown UUID balance and statement return 404 `{error:string}`.
7. Valid post returns 201 direct entry object with `POSTED` status and string monetary fields.
8. Invalid post returns 422 `{error:string}` and database row counts do not change.
9. Valid reverse returns 201 direct entry with non-null `reversal_of_id`.
10. Duplicate/self/non-posted reverse returns the specified 404/409 `{error:string}` without mutation.
11. Missing/invalid bearer returns 401 on every `/api/*` route.
12. Direct backend `/api/rate-schedule` and frontend-proxy `/api/rate-schedule` both return 200 and equivalent arrays.
13. Proxy diagnostics must include both request URLs and statuses; a direct 200/proxy 404 is a failed proxy contract, not a skipped test.
14. No successful endpoint may introduce `data`, `items`, or other wrapper keys not listed in `api-contract.md`.
