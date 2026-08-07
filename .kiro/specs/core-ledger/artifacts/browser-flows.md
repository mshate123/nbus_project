# Browser Flows

## Canonical execution

Run only from the browser-equipped frontend test container:

```text
docker compose --profile test run --rm frontend-test pnpm exec playwright test --config /e2e/playwright.config.ts --reporter=line
```

The host Playwright command is optional developer setup and is not CI/canonical because the host may lack Chromium.

## Flow 1: Smoke and proxy diagnosis

1. Preflight direct backend `/api/rate-schedule`; record URL/status/body shape.
2. Preflight frontend `/api/rate-schedule` through nginx; record URL/status/body shape.
3. Fail with a routing-specific diagnostic if direct is 200 and proxy is not 200.
4. Open the frontend root.
5. Assert accessible page heading, account list, and at least one seeded rate row.

## Flow 2: Account statement

1. Select the first seeded account.
2. Assert loading state transitions to statement or empty state.
3. Assert statement lines show debit, credit, and running balance.
4. At mobile viewport, assert content remains usable without horizontal clipping.

## Flow 3: Post, verify, reverse

1. Open posting form.
2. Select two seeded accounts and enter equal Decimal debit/credit values.
3. Submit and assert success feedback.
4. Refresh/query the selected account and assert the new entry appears with updated balance.
5. Trigger reverse on the new entry and confirm.
6. Assert the reversal label/link appears and the final derived balance returns to its prior value.
7. Submit an invalid/unbalanced entry and assert `{error}` text is presented without a false success state.

## Browser assertions

- No API request may be made to `/rate-schedule` when the browser requested `/api/rate-schedule`.
- All interactive controls have accessible names and keyboard focus.
- Loading, empty, error, success, and responsive states are covered.
