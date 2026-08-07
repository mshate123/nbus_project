# Cross-Cutting Concerns

## Authentication/authorization
Documented as a stub bearer token (`README.md`, `.env.example`, spec), but no FastAPI dependency or route enforcement exists. Current API is unauthenticated.

## Validation and errors
Pydantic validates request shape and nonnegative decimal fields; service validates balance, precision, and one-sided lines. Errors are inconsistently represented as FastAPI `detail`. Row-lock timeout retry/backoff required by `design-errors.md` is not implemented.

## Transactions/concurrency
Posting locks accounts in sorted UUID order and route commits. Dependency rolls back failed sessions. Accrual uses nested savepoints for duplicate isolation. Reversal checks existing reversal before insert but relies on unique index for the final race.

## Persistence integrity
Line-level checks exist. Entry-level balance, posted immutability, valid normal-balance values, and active-account posting are not database-enforced. Migration is deliberately rerunnable with `CREATE TABLE IF NOT EXISTS`, which can mask schema drift and is unsuitable as a complete migration strategy.

## Observability
No structured logging, metrics, tracing, audit log, or operational accrual result endpoint was found. Accrual result is an in-memory dict only.

## Frontend states/accessibility
Loading and error states exist for main queries; empty statement exists. Rate schedule lacks an explicit empty state. Account rows are clickable `<tr>` elements rather than keyboard-accessible controls. No error boundary, retry controls, mutation pending state, responsive-specific behavior, or user-facing auth state is present.

## Security/deployment
Development secrets are embedded in manifests; no auth, CORS policy, rate limiting, or security headers are evident. Kubernetes port mismatch and missing job module make the declared deployment incomplete.
