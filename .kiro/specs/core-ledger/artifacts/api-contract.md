# API Contract

All `/api/*` routes require `Authorization: Bearer <configured stub token>`. Health/readiness are unauthenticated. Successful collections are plain arrays; successful resources are direct objects; errors are always `{ "error": "message" }`.

| Endpoint | Method | Request | Response (exact shape) | Status |
|---|---|---|---|---|
| `/health` | GET | none | `{ "status": "ok" }` | 200; 503 `{error}` if liveness dependency fails |
| `/ready` | GET | none | `{ "status": "ready" }` | 200 when DB/schema ready; 503 `{error}` otherwise |
| `/api/accounts` | GET | bearer auth | `[ { "id": UUID, "code": string, "name": string, "type": string, "normal_balance": "DEBIT"|"CREDIT", "rate_tier": "standard"|"premium"|"savings", "active": boolean } ]` | 200; 401 `{error}` |
| `/api/accounts/{account_id}/balance` | GET | UUID path, bearer auth | `{ "account_id": UUID, "balance": decimal-string }` | 200; 401/404 `{error}` |
| `/api/accounts/{account_id}/statement` | GET | UUID path, bearer auth | `{ "account_id": UUID, "lines": [ { "entry_id": UUID, "posted_at": ISO-8601, "debit": decimal-string, "credit": decimal-string, "running_balance": decimal-string, "reversal_of_id": UUID|null } ] }` | 200; 401/404 `{error}` |
| `/api/rate-schedule` | GET | bearer auth | `[ { "tier": "standard"|"premium"|"savings", "annual_rate": decimal-string } ]` | 200; 401 `{error}` |
| `/api/journal-entries` | POST | `{ "lines": [ { "account_id": UUID, "debit": decimal-string, "credit": decimal-string } ] }` with >=2 one-sided lines and equal totals | `{ "id": UUID, "status": "POSTED", "posted_at": ISO-8601, "reversal_of_id": UUID|null, "is_accrual": boolean, "lines": [ { "id": UUID, "account_id": UUID, "debit": decimal-string, "credit": decimal-string } ], "created_at": ISO-8601 }` | 201; 401/422 `{error}` |
| `/api/journal-entries/{entry_id}/reverse` | POST | UUID path, bearer auth, empty body | same direct journal-entry object, with `reversal_of_id` set | 201; 401/404/409 `{error}` |

## Proxy contract

A browser request to `http://frontend/api/rate-schedule` MUST arrive at the backend as `/api/rate-schedule`, not `/rate-schedule`. The canonical test must check both direct backend and proxied URLs and report each status separately. Nginx configuration must not use a URI-suffix `proxy_pass` that strips `/api/`.

## Error contract

- 401: `{"error":"authentication required"}`
- 404: `{"error":"account not found"}` or resource-specific stable message
- 409: `{"error":"entry is already reversed"}` or conflict-specific stable message
- 422: `{"error":"<validation message>"}`
- 503: `{"error":"service not ready"}`
