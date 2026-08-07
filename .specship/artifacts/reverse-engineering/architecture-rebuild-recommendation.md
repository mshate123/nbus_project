# Clean Rebuild Recommendation

## Target shape
1. **Domain layer:** typed value objects for money, account type, normal balance, entry status, and accrual policy; enforce invariants in one place.
2. **Persistence layer:** repositories/unit-of-work around SQLAlchemy; database constraints for valid normal balances, line sides, entry immutability, and accrual uniqueness.
3. **Application layer:** posting, balance/statement, reversal, and accrual use cases with explicit transaction ownership and typed result/errors.
4. **API layer:** versioned schemas, auth dependency, stable error envelope, UUID path validation, health/readiness endpoints, and route tests.
5. **Job layer:** executable accrual command with date input, migration readiness, retry policy, structured output, and exit status.
6. **UI layer:** accessible account/statement/rate/post/reverse workflows using shared primitives and complete state handling.
7. **Verification layer:** unit + real-Postgres integration + property tests that exercise persistence + deterministic containerized Playwright flows.

## First rebuild milestones
- M0: Decide cutover, rates, auth, deployment, export, and seed policy.
- M1: Schema/domain and migration with invariant tests.
- M2: Posting/balance/reversal API contract and integration tests.
- M3: Accrual use case and executable job with idempotency tests.
- M4: UI shell and read workflows with browser proof.
- M5: Write/reversal UI and end-to-end flow; includes REBUILD-T0.1 browser orchestration stabilization.
- M6: Deployment hardening, coverage gates, observability, and teardown of unused infrastructure.

## Non-goals for the first cutover
Do not preserve broken K8s port assumptions, missing job references, unused S3 plumbing, stale README claims, weak coverage commands, or test fixtures as production seed authority.
