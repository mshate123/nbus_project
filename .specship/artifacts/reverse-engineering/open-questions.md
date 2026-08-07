# Open Questions

1. **Scope:** Is this a greenfield cutover with no data migration, or must existing PostgreSQL data be imported?
2. **Deployment:** Should the rebuild support Docker Compose only, or also Minikube/Kubernetes?
3. **Export:** Is S3 statement export required? No implementation exists despite LocalStack configuration.
4. **Rates:** Which tier names/values are authoritative, and where is an account's tier stored?
5. **Auth:** Is a stub bearer token sufficient, and should it protect every API route or only admin operations?
6. **Missing accounts:** Preserve current zero/empty response semantics or introduce 404 errors?
7. **E2E:** The `pnpm e2e` invocation was aborted by the tool runner twice; should the build use a containerized Playwright command as the sole supported path?
8. **Seed data:** Should the clean app start with a chart of accounts and demo entries? Current migration seeds rates only, so live accounts are empty.
9. **Auditability:** Are immutable posted rows, an audit log, and operator identity required beyond the current reversal link?
10. **Accrual policy:** Should accrual process every active account, only customer liability accounts, or accounts with explicit tiers; how are negative balances handled?
