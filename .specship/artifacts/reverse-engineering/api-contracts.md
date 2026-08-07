# Existing API Contracts

Evidence: `backend/api/routes.py` and `frontend/src/lib/api.ts`.

| Endpoint | Method | Request | Response | Current errors/notes |
|---|---|---|---|---|
| `/health` | GET | none | `{status: "ok"}` | 503 with `{detail: "database unavailable"}` on SQLAlchemy failure |
| `/api/accounts` | GET | none | plain array of `{id, code, name, type, normal_balance, active}` | No auth; includes inactive accounts |
| `/api/journal-entries` | POST | `{lines:[{account_id: UUID, debit: Decimal>=0, credit: Decimal>=0}, ...]}` min 2 | 201 direct entry object with string IDs/amounts and lines | PostingError -> 422 with FastAPI `{detail}` |
| `/api/journal-entries/{entry_id}/reverse` | POST | path string | 201 direct reversing entry object | ReversalError -> 409 `{detail}`; malformed ID can become server/service error |
| `/api/accounts/{account_id}/balance` | GET | UUID path | direct `{account_id, balance}` | Missing account returns zero rather than 404 |
| `/api/accounts/{account_id}/statement` | GET | UUID path | direct `{account_id, lines:[...]}` | Missing account returns empty lines |
| `/api/rate-schedule` | GET | none | plain array of `{tier, annual_rate}` | No auth |

## Rebuild contract decisions to make
- Standardize errors to either FastAPI `{detail}` or the SpecShip preferred `{error}`; do not leave both implicit.
- Decide whether missing account is zero/empty compatibility or a 404 domain error.
- Define auth behavior because `AUTH_STUB_TOKEN` is documented but unused.
- Define mutation and accrual-run endpoints/runner contract if the clean rebuild includes operational workflows.
