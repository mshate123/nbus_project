# Implementation Plan: Ledger Clean Rewrite

## Overview

This plan turns the approved ledger rewrite into bounded coding tasks. Every leaf task names exact target files, a RED test and one-shot command, the implementation step, a GREEN command, requirement references, and acceptance checks. Production tasks must follow RED -> command -> minimal implementation -> command -> GREEN before refactoring. No task is optional: all five design properties and the Canonical_E2E are blocking.

**Spec location note:** this plan is stored in `.kiro/specs/core-ledger/` as a Kiro-native artifact. Source recon/RCA evidence is at `.specship/artifacts/reverse-engineering/`.

**Test ownership note:** backend tests live under `backend/tests/`, frontend Vitest tests live under `frontend/tests/`, and Playwright tests live under repository-level `e2e/`. `api-test`, `frontend-test`, and `e2e-test` are separate one-shot Compose services; no service runs another layer's suite implicitly.

## Milestone 0: Scaffold and contracts

- [x] 0.1 Establish backend/frontend test entrypoints and typed settings.
  - Target files: `backend/config.py`, `backend/main.py`, `backend/tests/unit/test_settings.py`, `frontend/package.json`, `frontend/vitest.config.ts`.
  - RED: add `test_default_stub_token_and_test_database` and `test_health_route_shape` to `backend/tests/unit/test_settings.py`; run `docker compose run --rm api pytest backend/tests/unit/test_settings.py -q` and confirm failure.
  - Implement: define settings, app factory, and test command wiring.
  - GREEN: rerun the exact command; acceptance requires settings load and `/health` shape pass.
  - Requirements: 1.1, 1.2, 2.1.

- [x] 0.2 Define the exact API and error contract helpers.
  - Target files: `backend/api/errors.py`, `backend/api/schemas.py`, `backend/tests/api/test_error_envelopes.py`, `backend/tests/api/test_response_shapes.py`.
  - RED: write `test_validation_error_is_single_error_key`, `test_collections_are_plain_arrays`, and `test_resources_are_direct_objects`; run `docker compose run --rm api pytest backend/tests/api/test_error_envelopes.py backend/tests/api/test_response_shapes.py -q`.
  - Implement: add stable envelope serialization and direct response schemas.
  - GREEN: rerun the command; acceptance requires no `data`/`items` wrapper and exactly one `error` key.
  - Requirements: 2.3, 2.4; `artifacts/api-contract.md`.

- [x] 0.3 Establish test-layer layout and the dedicated Playwright runner.
  - Target files: `docker-compose.yml`, `frontend/Dockerfile`, `frontend/vitest.config.ts`, `frontend/tests/unit/components/RateSchedule.test.tsx`, `e2e/playwright.config.ts`, `e2e/smoke.spec.ts`.
  - RED: run `docker compose --profile test run --rm frontend-test` and confirm it runs Vitest only; run `docker compose --profile app --profile test run --rm e2e-test` and confirm the dedicated service is not yet available.
  - Implement: move frontend tests out of `frontend/src/` into `frontend/tests/`, configure Vitest discovery, keep browser specs under repository-level `e2e/`, and add a separate `e2e-test` service built from the browser-equipped frontend test image. The service shall mount `e2e/` read-only and target the Compose frontend service through Docker DNS.
  - GREEN: run `docker compose --profile test run --rm frontend-test` and `docker compose --profile app --profile test run --rm e2e-test`; acceptance requires the first command to run Vitest only and the second to run Playwright in its own container with Chromium supplied by the image.
  - Requirements: 7.1-7.3; NFR test-layer ownership.

## Milestone 1: Domain, schema, bootstrap, and fixture ownership

- [ ] 1.1 Implement Decimal money and posting validation.
  - Target files: `backend/domain/money.py`, `backend/domain/posting.py`, `backend/tests/unit/test_posting_validation.py`.
  - RED: add `test_rejects_zero_and_both_sided_lines`, `test_rejects_more_than_four_decimal_places`, `test_rejects_unbalanced_entries`, and `test_accepts_balanced_one_sided_entry`; run `docker compose run --rm api pytest backend/tests/unit/test_posting_validation.py -q`.
  - Implement: add Decimal-only value objects and typed validation errors.
  - GREEN: rerun the command; acceptance requires all invalid variants rejected without float conversion.
  - Requirements: 4.1, 4.2, NFR money precision.

- [ ] 1.2 Create persistence models and migration constraints.
  - Target files: `backend/models.py`, `backend/migrations/versions/002_ledger_rewrite.py`, `backend/tests/integration/test_schema_constraints.py`.
  - RED: add `test_rate_tier_constraint`, `test_one_reversal_unique_constraint`, `test_one_accrual_per_account_date`, and `test_posted_rows_are_immutable`; run `docker compose run --rm api pytest backend/tests/integration/test_schema_constraints.py -q`.
  - Implement: add tables, NUMERIC checks, enum/tier constraints, indexes, and immutability guards.
  - GREEN: run `docker compose run --rm api alembic upgrade head && docker compose run --rm api pytest backend/tests/integration/test_schema_constraints.py -q`; acceptance requires all constraints pass on a fresh database.
  - Requirements: 3.3, 5.3, 6.3.

- [ ] 1.3 Own production bootstrap seeds separately from test factories.
  - Target files: `backend/migrations/versions/003_seed_ledger.py`, `backend/seed.py`, `backend/tests/fixtures/factories.py`, `backend/tests/integration/test_seed_equivalence.py`.
  - RED: add `test_production_seed_has_three_rates_and_chart`, `test_seed_entries_are_balanced`, and `test_factory_does_not_define_production_seed_truth`; run `docker compose run --rm api pytest backend/tests/integration/test_seed_equivalence.py -q`.
  - Implement: make migrations/seed command own stable production codes and make `factories.py` generate isolated test data; compare seed contract fields without importing factory rows as truth.
  - GREEN: run `docker compose run --rm api alembic upgrade head && docker compose run --rm api pytest backend/tests/integration/test_seed_equivalence.py -q`; acceptance requires exact rates, valid tiers, balanced demo entries, and separate ownership.
  - Requirements: 1.4, 3.2, 3.4.

- [ ] 1.4 Implement repository and unit-of-work primitives.
  - Target files: `backend/persistence/repositories.py`, `backend/persistence/uow.py`, `backend/tests/integration/test_uow_rollback.py`.
  - RED: add `test_commit_failure_rolls_back_flushed_entry_and_lines` and `test_account_locks_are_sorted_by_uuid`; run `docker compose run --rm api pytest backend/tests/integration/test_uow_rollback.py -q`.
  - Implement: add async repositories, deterministic lock ordering, commit/rollback ownership, and injectable commit failure.
  - GREEN: rerun the command; acceptance requires zero partial rows after simulated commit failure.
  - Requirements: 4.3, 4.6, NFR concurrency.

- [ ] 1.5 Implement mandatory Property 1 test.
  - Target files: `backend/tests/property/test_balanced_posting_invariant.py`.
  - RED: add exactly one Hypothesis test named `test_property_1_balanced_posting_preserves_double_entry_invariant`; run `docker compose run --rm api pytest backend/tests/property/test_balanced_posting_invariant.py -q` and observe the expected failure against the incomplete service.
  - Implement: generate valid and invalid line collections and assert persisted totals or complete rollback; use at least 100 examples and the tag `Feature: core-ledger, Property 1: Balanced posting preserves the double-entry invariant`.
  - GREEN: rerun the same command; acceptance requires 100+ examples and no partial rows.
  - Requirements: 4.1, 4.2, 4.3, 4.6; Design Property 1.

- [ ] 1.6 Checkpoint: verify foundation.
  - Run `docker compose run --rm api pytest backend/tests/unit backend/tests/integration/test_schema_constraints.py backend/tests/integration/test_seed_equivalence.py backend/tests/property/test_balanced_posting_invariant.py -q`; acceptance requires green tests and fresh bootstrap.

## Milestone 2: Ledger services and balance/statement behavior

- [ ] 2.1 Implement posting application service.
  - Target files: `backend/engine/posting_service.py`, `backend/tests/unit/test_posting_service.py`, `backend/tests/integration/test_posting_transaction.py`.
  - RED: add `test_post_balanced_entry`, `test_inactive_account_returns_422_without_write`, `test_missing_account_returns_422_without_write`, and `test_commit_failure_returns_500_without_partial_rows`; run `docker compose run --rm api pytest backend/tests/unit/test_posting_service.py backend/tests/integration/test_posting_transaction.py -q`.
  - Implement: validate account state, lock sorted UUIDs, flush, commit, rollback on failure, and return typed Posted_Entry.
  - GREEN: rerun the command; acceptance requires inactive policy and rollback behavior.
  - Requirements: 4.1-4.3, 4.6, 3.6.

- [ ] 2.2 Implement balance and statement services.
  - Target files: `backend/engine/balance_service.py`, `backend/engine/statement_service.py`, `backend/tests/unit/test_balance_service.py`, `backend/tests/unit/test_statement_service.py`.
  - RED: add `test_debit_and_credit_normal_balance_reference`, `test_existing_zero_balance_account_returns_zero`, `test_existing_account_without_entries_returns_empty_statement`, and `test_missing_account_is_not_zero`; run `docker compose run --rm api pytest backend/tests/unit/test_balance_service.py backend/tests/unit/test_statement_service.py -q`.
  - Implement: derive balances from posted lines, preserve four-place Decimal precision, and order statements deterministically.
  - GREEN: rerun the command; acceptance requires zero/no-entry distinction from missing account.
  - Requirements: 3.5, 4.4, 4.5.

- [ ] 2.3 Implement mandatory Property 2 test.
  - Target files: `backend/tests/property/test_balance_reference.py`.
  - RED: add exactly `test_property_2_derived_balance_matches_reference_model`; run `docker compose run --rm api pytest backend/tests/property/test_balance_reference.py -q`.
  - Implement: generate account normal balances and posted lines, compare service output to a Decimal reference model, include empty collections, 100+ examples, and the required Property 2 tag.
  - GREEN: rerun the command; acceptance requires all generated balances match.
  - Requirements: 3.5, 4.4, 4.5; Design Property 2.

- [ ] 2.4 Checkpoint: verify ledger services.
  - Run `docker compose run --rm api pytest backend/tests/unit/test_posting_service.py backend/tests/unit/test_balance_service.py backend/tests/unit/test_statement_service.py backend/tests/property/test_balance_reference.py -q`; acceptance requires green tests and no mutable balance column.

## Milestone 3: API routes, UUID/error contracts, and reversal

- [ ] 3.1 Implement API routes and deterministic error handlers.
  - Target files: `backend/api/routes.py`, `backend/api/errors.py`, `backend/main.py`, `backend/tests/api/test_api_contract.py`.
  - RED: add `test_malformed_uuid_returns_422_error_envelope_without_lookup`, `test_missing_account_returns_404`, `test_existing_zero_balance_returns_200`, `test_missing_auth_returns_401`, and `test_unexpected_commit_failure_returns_500`; run `docker compose run --rm api pytest backend/tests/api/test_api_contract.py -q`.
  - Implement: wire auth, routes, framework validation normalization, service mappings, direct arrays/objects, and stable envelopes.
  - GREEN: rerun the command; acceptance requires exact status and body shape for every named case.
  - Requirements: 2.1-2.6, 3.5, 4.6; `artifacts/api-contract-tests.md`.

- [ ] 3.2 Implement reversal service and route.
  - Target files: `backend/engine/reversal_service.py`, `backend/api/routes.py`, `backend/tests/unit/test_reversal_service.py`, `backend/tests/integration/test_reversal_conflicts.py`.
  - RED: add `test_reversal_swaps_lines`, `test_duplicate_reversal_is_409_without_mutation`, `test_self_reversal_is_409`, `test_missing_entry_is_404`, and `test_non_posted_entry_is_409`; run `docker compose run --rm api pytest backend/tests/unit/test_reversal_service.py backend/tests/integration/test_reversal_conflicts.py -q`.
  - Implement: append linked offset entry, enforce application and database uniqueness, and preserve history on conflicts.
  - GREEN: rerun the command; acceptance requires one reversal and unchanged prior rows on every conflict.
  - Requirements: 5.1-5.4.

- [ ] 3.3 Implement mandatory Property 3 test.
  - Target files: `backend/tests/property/test_reversal_balance_neutrality.py`.
  - RED: add exactly `test_property_3_reversal_is_offsetting_and_balance_neutral`; run `docker compose run --rm api pytest backend/tests/property/test_reversal_balance_neutrality.py -q`.
  - Implement: generate reversible entries, assert swapped lines, one linked append, zero net per account, 100+ examples, and the required Property 3 tag.
  - GREEN: rerun the command; acceptance requires no duplicate or destructive reversal.
  - Requirements: 5.1, 5.3; Design Property 3.

- [ ] 3.4 Checkpoint: verify API and reversal contracts.
  - Run `docker compose run --rm api pytest backend/tests/api backend/tests/unit/test_reversal_service.py backend/tests/integration/test_reversal_conflicts.py backend/tests/property/test_reversal_balance_neutrality.py -q`; acceptance requires deterministic envelopes and status codes.

## Milestone 4: Accrual policy and command

- [ ] 4.1 Implement tier-aware accrual calculation and skip policy.
  - Target files: `backend/engine/accrual_service.py`, `backend/tests/unit/test_accrual_service.py`.
  - RED: add `test_uses_account_rate_tier`, `test_rounds_half_up_to_four_places`, `test_zero_balance_is_deterministic_skip`, and `test_negative_balance_is_deterministic_skip`; run `docker compose run --rm api pytest backend/tests/unit/test_accrual_service.py -q`.
  - Implement: Decimal calculation, current account tier selection, and structured skip reasons.
  - GREEN: rerun the command; acceptance requires exact amounts and no positive skip posting.
  - Requirements: 6.1, 6.2, 6.4.

- [ ] 4.2 Implement accrual command and idempotency persistence.
  - Target files: `backend/jobs/accrual.py`, `backend/tests/integration/test_accrual_idempotency.py`, `backend/tests/integration/test_accrual_cli.py`.
  - RED: add `test_second_run_is_idempotent`, `test_valid_date_returns_structured_zero_exit`, `test_invalid_date_returns_nonzero_exit`, and `test_database_failure_returns_nonzero_exit`; run `docker compose run --rm api pytest backend/tests/integration/test_accrual_idempotency.py backend/tests/integration/test_accrual_cli.py -q`.
  - Implement: date parsing, uniqueness handling, structured per-account output, commit policy, and exit codes.
  - GREEN: rerun the command; acceptance requires one row per account/date and nonzero failure status.
  - Requirements: 6.3, 6.5.

- [ ] 4.3 Implement mandatory Property 4 test.
  - Target files: `backend/tests/property/test_accrual_rounding_and_tier.py`.
  - RED: add exactly `test_property_4_accrual_uses_tier_and_half_up_rounding`; run `docker compose run --rm api pytest backend/tests/property/test_accrual_rounding_and_tier.py -q`.
  - Implement: generate positive balances, dates, and authoritative tiers, assert Decimal reference result, 100+ examples, and required Property 4 tag.
  - GREEN: rerun the command; acceptance requires exact tier/rate selection and rounding.
  - Requirements: 6.1, 6.2; Design Property 4.

- [ ] 4.4 Implement mandatory Property 5 test.
  - Target files: `backend/tests/property/test_accrual_idempotency.py`.
  - RED: add exactly `test_property_5_accrual_is_idempotent_per_account_date`; run `docker compose run --rm api pytest backend/tests/property/test_accrual_idempotency.py -q`.
  - Implement: generate eligible and skip accounts, run twice, assert at most one entry and equivalent second result, 100+ examples, and required Property 5 tag.
  - GREEN: rerun the command; acceptance requires no duplicate money movement.
  - Requirements: 6.3, 6.4; Design Property 5.

- [ ] 4.5 Checkpoint: verify accrual.
  - Run `docker compose run --rm api pytest backend/tests/unit/test_accrual_service.py backend/tests/integration/test_accrual_idempotency.py backend/tests/integration/test_accrual_cli.py backend/tests/property/test_accrual_rounding_and_tier.py backend/tests/property/test_accrual_idempotency.py -q`; acceptance requires green property and CLI tests.

## Milestone 5: UI read states and proxy

- [ ] 5.1 Implement the API client and read components.
  - Target files: `frontend/src/api/client.ts`, `frontend/src/features/accounts/AccountsPanel.tsx`, `frontend/src/features/rates/RateSchedule.tsx`, `frontend/src/features/statements/StatementPanel.tsx`, `frontend/src/features/ledger/ReadStates.tsx`, `frontend/tests/unit/features/ledger/ReadStates.test.tsx`.
  - RED: add named tests `renders_loading_state`, `renders_empty_accounts_and_rates`, `renders_error_with_retry`, `renders_seeded_happy_state`, and `renders_narrow_responsive_state` in `frontend/tests/unit/features/ledger/ReadStates.test.tsx`; run `docker compose run --rm frontend-test pnpm test -- --run frontend/tests/unit/features/ledger/ReadStates.test.tsx`.
  - Implement: consume plain arrays/direct objects, add accessible empty/error/retry/loading/happy states, and use Tailwind/shadcn primitives without inline styles.
  - GREEN: rerun the command; acceptance requires every state sequence in `artifacts/ui-state-sequences.md`.
  - Requirements: 3.1, 3.2, 4.5, 7.5, 7.7.

- [x] 5.2 Add direct/proxy contract and preflight tests.
  - Target files: `e2e/preflight.spec.ts`, `frontend/nginx.conf`, `e2e/helpers/preflight.ts`, `backend/tests/integration/test_proxy_contract.py`.
  - RED: add `test_direct_backend_and_frontend_proxy_preserve_api_prefix` and `reports_direct_and_proxy_status_separately`; run `docker compose --profile app --profile test run --rm e2e-test pnpm exec playwright test /e2e/preflight.spec.ts --config /e2e/playwright.config.ts --reporter=line`.
  - Implement: preserve `/api` in nginx, install/use Chromium in the image, and print separate direct/proxy URL/status/shape diagnostics.
  - GREEN: rerun the exact command; acceptance requires direct and proxied arrays equivalent and no `/rate-schedule` request.
  - Requirements: 7.1-7.4; confirmed RCA architecture.

- [ ] 5.3 Checkpoint: verify read UI and proxy.
  - Run `docker compose run --rm frontend-test pnpm test -- --run frontend/tests/unit/features/ledger/ReadStates.test.tsx` and `docker compose --profile app --profile test run --rm e2e-test pnpm exec playwright test /e2e/preflight.spec.ts --config /e2e/playwright.config.ts --reporter=line`; acceptance requires all five UI states and separate route diagnostics.

## Milestone 6: UI posting, reversal, and blocking Canonical_E2E

- [ ] 6.1 Implement posting UI with validation and recovery states.
  - Target files: `frontend/src/features/posting/PostEntryForm.tsx`, `frontend/tests/unit/features/posting/PostEntryForm.test.tsx`.
  - RED: add `rejects_unbalanced_entry_and_preserves_form`, `shows_inactive_account_error`, `disables_controls_while_submitting`, `refreshes_after_success`, and `recovers_after_api_error`; run `docker compose run --rm frontend-test pnpm test -- --run frontend/tests/unit/features/posting/PostEntryForm.test.tsx`.
  - Implement: line validation, deterministic 422 display, disabled submitting state, retry affordance, and query invalidation.
  - GREEN: rerun the command; acceptance requires the invalid sequence never shows false success.
  - Requirements: 4.1, 4.2, 3.6, 7.5-7.7.

- [ ] 6.2 Implement reversal UI and conflict preservation.
  - Target files: `frontend/src/features/reversal/ReversalAction.tsx`, `frontend/tests/unit/features/reversal/ReversalAction.test.tsx`.
  - RED: add `confirms_and_refreshes_after_reversal`, `preserves_row_on_conflict`, `shows_reversal_label`, and `cancels_without_mutation`; run `docker compose run --rm frontend-test pnpm test -- --run frontend/tests/unit/features/reversal/ReversalAction.test.tsx`.
  - Implement: confirmation dialog, conflict envelope, original-row preservation, reversal label, and final balance refresh.
  - GREEN: rerun the command; acceptance requires no false success on 409.
  - Requirements: 5.1-5.4, 7.5-7.7.

- [ ] 6.3 Implement the mandatory Canonical_E2E flow.
  - Target files: `e2e/ledger-flow.spec.ts`, `e2e/fixtures/ledger.ts`, `e2e/playwright.config.ts`.
  - RED: add `test('canonical seeded post then reverse flow')`, plus named tests `empty_accounts_and_rates`, `api_error_retry_recovery`, `posting_validation_failure`, `reversal_conflict`, `loading_states`, and `responsive_narrow_view`; run `docker compose --profile app --profile test run --rm e2e-test pnpm exec playwright test --config /e2e/playwright.config.ts --reporter=line` and confirm failures before implementation.
  - Implement: preflight direct backend then proxy, seeded read, statement, post, verify, reverse, verify final balance, and all explicit state sequences; Chromium must come from the dedicated runner image.
  - GREEN: rerun the exact Canonical_E2E command; acceptance requires every named test pass, accessible controls, no API prefix stripping, and no horizontal clipping.
  - Requirements: 7.1-7.7; `artifacts/browser-flows.md`.

- [ ] 6.4 Checkpoint: verify full browser workflow.
  - Run `docker compose --profile app --profile test run --rm e2e-test`; acceptance requires the dedicated Playwright container to pass without host browser dependencies.

## Milestone 7: Compose, coverage, performance, and final gates

- [ ] 7.1 Add bounded Compose smoke and performance tests.
  - Target files: `backend/tests/integration/test_compose_bootstrap.py`, `backend/tests/performance/test_balance_latency.py`, `backend/tests/integration/test_no_aws_dependency.py`.
  - RED: add `test_fresh_volume_runs_migrations_and_seeds`, `test_compose_needs_no_aws_variables`, and `test_balance_p95_under_200ms`; run `docker compose up -d postgres api frontend && docker compose run --rm api pytest backend/tests/integration/test_compose_bootstrap.py backend/tests/integration/test_no_aws_dependency.py backend/tests/performance/test_balance_latency.py -q`.
  - Implement: startup/readiness probes, fresh-volume seed checks, isolated p95 measurement, and no AWS/LocalStack dependency assertions.
  - GREEN: rerun the command; acceptance requires p95 `<200ms` and exact health/readiness shapes.
  - Requirements: 1.1-1.4, NFR performance/deployment.

- [ ] 7.2 Enforce declared coverage gates.
  - Target files: `backend/pyproject.toml`, `frontend/package.json`, `frontend/vitest.config.ts`, `backend/tests/conftest.py`.
  - RED: run `docker compose run --rm api pytest backend/tests/unit backend/tests/property --cov=backend/engine --cov-fail-under=85`, `docker compose run --rm api pytest backend/tests/api --cov=backend/api --cov-fail-under=75`, `docker compose run --rm api pytest backend/tests/unit backend/tests/property backend/tests/api --cov=backend --cov-fail-under=70`, and `docker compose run --rm frontend-test pnpm test -- --run --coverage --coverage.thresholds.lines=60`; confirm at least one gate fails before threshold wiring.
  - Implement: configure separate backend engine/API/overall and frontend thresholds.
  - GREEN: rerun all four exact commands; acceptance requires all thresholds pass.
  - Requirements: NFR coverage gates.

- [ ] 7.3 Final blocking verification.
  - Target files: no new production files; update only `backend/tests/`, `frontend/tests/`, `e2e/`, and test/container configuration if a preceding gate exposes a regression.
  - Run in order: `docker compose run --rm api pytest backend/tests/unit backend/tests/property --cov=backend/engine --cov-fail-under=85`; `docker compose run --rm api pytest backend/tests/api --cov=backend/api --cov-fail-under=75`; `docker compose run --rm api pytest backend/tests/unit backend/tests/property backend/tests/api --cov=backend --cov-fail-under=70`; `docker compose run --rm frontend-test pnpm test -- --run --coverage --coverage.thresholds.lines=60`; `docker compose --profile app --profile test run --rm e2e-test`.
  - Acceptance: all commands exit zero; five property tests and Canonical_E2E are present and blocking; direct/proxy preflight, seed ownership, UUID/error cases, inactive/zero-balance policy, rollback, responsive states, and performance gate are evidenced.
  - Requirements: all requirements and NFRs.

## Notes

- Every task is a coding or automated-test task; no deployment, manual acceptance, training, or documentation work is delegated.
- All test tasks are mandatory. The five property tests and Canonical_E2E have no optional markers.
- Production seed truth belongs to migrations/seed command; shared factories generate tests and only seed equivalence is asserted.
- Backend tests belong under `backend/tests/`; frontend Vitest tests belong under `frontend/tests/`; Playwright specs and fixtures belong under repository-level `e2e/`.
- `api-test` runs pytest only, `frontend-test` runs Vitest only, and `e2e-test` runs Playwright only in a separate browser-equipped container.
- Backend remains `/api/*`; nginx preserves `/api`; direct and proxied preflight checks remain separate.
- The complete artifact list is preserved: `market-research.md`, `artifacts/api-contract.md`, `artifacts/api-contract-tests.md`, `artifacts/browser-flows.md`, `artifacts/edge-cases.md`, `artifacts/test-cases.md`, `artifacts/ui-state-sequences.md`, and `artifacts/reverse-engineering/source.txt`.

## Task Dependency Graph

```json
{
  "waves": [
    {"id": 0, "tasks": ["0.1", "0.2", "0.3"]},
    {"id": 1, "tasks": ["1.1", "1.2", "1.3"]},
    {"id": 2, "tasks": ["1.4", "2.1", "2.2"]},
    {"id": 3, "tasks": ["1.5", "2.3", "3.1"]},
    {"id": 4, "tasks": ["3.2", "4.1", "5.1"]},
    {"id": 5, "tasks": ["3.3", "4.2", "5.2"]},
    {"id": 6, "tasks": ["6.1", "6.2", "4.3", "4.4"]},
    {"id": 7, "tasks": ["7.1", "6.3"]},
    {"id": 8, "tasks": ["7.2"]},
    {"id": 9, "tasks": ["7.3"]}
  ]
}
```
