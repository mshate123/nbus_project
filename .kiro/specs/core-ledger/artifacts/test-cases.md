# Test Cases

Each case is an implementation seed for a RED test. Required tests run in the declared Docker containers.

| ID | Area | Scenario | Expected result |
|---|---|---|---|
| TC-01 | Bootstrap | Fresh PostgreSQL volume | migrations, chart accounts, demo entries, and three rates exist; no legacy import |
| TC-02 | Health | DB ready then `/health` and `/ready` | 200 with exact shapes |
| TC-03 | Auth | Missing, invalid, valid bearer on `/api/accounts` | 401, 401, 200 with `{error}` on failures |
| TC-04 | Accounts | List seeded accounts | plain array ordered by code; includes `rate_tier` |
| TC-05 | Rates | Read schedule | exactly standard/premium/savings at 0.035000/0.045000/0.050000 |
| TC-06 | Posting | Balanced two-line Decimal entry | 201, one posted entry, exact string amounts |
| TC-07 | Posting errors | Unbalanced, zero, both-sided, >4dp, missing account | 422; no rows written |
| TC-08 | Concurrency | Ten concurrent balanced posts sharing accounts | no deadlock; exact final derived balance |
| TC-09 | Balance | Debit-normal and credit-normal accounts | reference-model result and deterministic statement order |
| TC-10 | Missing account | Unknown UUID balance/statement | 404 `{error}` |
| TC-11 | Reversal | Reverse posted entry | one linked offset entry; final contribution zero |
| TC-12 | Reversal conflicts | duplicate, self, missing, non-posted | 409/404 stable errors; no mutation |
| TC-13 | Accrual | Positive balance for each rate tier | Decimal `balance*rate/365`, half-up 4dp, assigned tier used |
| TC-14 | Accrual skip | zero/negative balance | no positive accrual; structured skip reason |
| TC-15 | Accrual idempotency | Same account/date twice | one accrual row; second result idempotent |
| TC-16 | Accrual CLI | valid date and invalid date/database failure | structured output; success 0; failure nonzero |
| TC-17 | Proxy | Direct backend and nginx `/api/rate-schedule` | both 200 with same plain array |
| TC-18 | UI read states | loading, empty, error, seeded happy, narrow viewport | accessible and responsive states render |
| TC-19 | UI write | post valid/invalid entry | success refreshes; invalid displays error and preserves form context |
| TC-20 | UI reverse | confirm reversal/conflict | label and final balance update; conflict visible |
| TC-21 | Canonical E2E | seeded load -> statement -> post -> reverse | Chromium launches in container; full flow passes |
