# Preserved Behaviors and Tear-Down Candidates

## Preserve as domain behavior
1. Every accepted journal entry has at least two one-sided lines and equal total debits/credits.
2. Monetary arithmetic uses Decimal-like exact precision and rejects more than four decimal places rather than silently rounding.
3. Posting is atomic and locks all referenced accounts in deterministic order.
4. Posted account balances are derived from posted journal lines, adjusted by normal balance direction; no stored balance can drift.
5. Accounts with no posted activity currently report zero balance; missing account currently yields zero/empty read responses.
6. Posted entries are reversed by a new offsetting entry, never deleted; reversal links to the original and a reversal cannot itself be reversed.
7. Daily accrual is intended to use `balance * annual_rate / 365`, round half-up to four places, and be idempotent per account/date.
8. Account and rate schedule reads return direct JSON arrays/objects currently consumed by the frontend.
9. UI account selection expands a statement; statement shows running balances and reversal labels.

## Preserve only if reconfirmed in rebuild contract
- Development Docker Compose workflow.
- FastAPI `/health` shape and `/api/*` paths.
- Missing-account zero/empty semantics.
- Seed rate values and tier names; current migration and fixtures disagree.
- LocalStack statement-export intent; no implementation currently exists.
- Minikube deployment shape; current manifests are not operationally coherent.

## Tear down or replace
- Flat import/PYTHONPATH coupling.
- Unused S3/LocalStack configuration if export is not in scope.
- Missing CronJob target and current K8s deployment assumptions.
- Weak coverage thresholds and shallow component tests.
- Unused VITE API environment variable.
- Disabled `.kiro/hooks` are process tooling, not runtime architecture; preserve only if desired by the rebuild workflow.
- `factories.py` claims about nonexistent seed/mock consumers.
