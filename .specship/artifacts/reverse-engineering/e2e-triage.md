# REBUILD-T0.1 E2E Playwright Triage

## Status
**Root cause confirmed. No application source fix was applied during recon.** The next rebuild task is ready for implementation.

## Symptom
The existing smoke test in `e2e/smoke.spec.ts` failed while waiting for a successful response from `/api/rate-schedule`. Earlier host invocations appeared to hang or were aborted before returning a result.

## Reproduction evidence

### Host Playwright path
Command:
```text
CI=1 pnpm exec playwright test --config ../e2e/playwright.config.ts --reporter=line
```

Result: Playwright started, recreated host `frontend/node_modules`, then failed three attempts before launching the test browser:
```text
browserType.launch: Executable doesn't exist at ~/Library/Caches/ms-playwright/.../chrome-headless-shell
```

This is a host setup failure, not the application failure. The host has the Playwright package but not its Chromium executable.

### Supported container path
Command:
```text
docker compose --profile test run --rm frontend-test pnpm exec playwright test --config /e2e/playwright.config.ts --reporter=line
```

Result: Chromium launched successfully. The smoke test loaded the frontend, then timed out at `e2e/smoke.spec.ts:15` waiting for `/api/rate-schedule`. The container received a 404 through the frontend proxy.

Direct network checks from the test container:
- `http://host.docker.internal:3000/` -> 200, SPA HTML.
- `http://host.docker.internal:3000/api/rate-schedule` -> 404, `{"detail":"Not Found"}`.
- Direct backend `http://localhost:8000/api/rate-schedule` -> 200 with three rate rows.

## Root cause
`frontend/nginx.conf` declares:
```nginx
location /api/ {
    proxy_pass http://api:8000/;
}
```

The trailing slash on `proxy_pass` causes nginx to replace the matched `/api/` prefix before forwarding. Therefore:
```text
browser:  /api/rate-schedule
nginx:    /rate-schedule
backend:  only defines /api/rate-schedule
result:   404
```

The backend route prefix is confirmed in `backend/api/routes.py`:
```python
router = APIRouter(prefix="/api", tags=["ledger"])
```

## Separate environment issue
The host command cannot be the canonical E2E path unless browser installation is documented and enforced. `frontend/Dockerfile` already installs Chromium in the image, so the containerized path is the correct baseline for CI/rebuild validation. The host package install alone does not install the browser binary.

## Triage decision
Do not patch the backend route or weaken the smoke assertion. The smallest application/config fix is to preserve the `/api` prefix in the nginx upstream request, then rerun the containerized smoke test. The clean rebuild should encode this as an API-proxy contract test or a browser smoke prerequisite.

## Next implementation task
**REBUILD-T0.1a: Make the containerized Playwright smoke path green.**

### Scope
- Update the frontend proxy configuration so browser requests to `/api/*` reach the backend's `/api/*` routes unchanged.
- Keep the canonical E2E command containerized, with Chromium installed by the frontend test image.
- Add an explicit readiness/preflight check so the test fails immediately with the upstream URL and status if the proxy is unavailable.
- Do not change backend route prefixes or the smoke test's business assertion.

### Acceptance criteria
1. From the frontend test container, `/api/rate-schedule` returns HTTP 200 through nginx.
2. `e2e/smoke.spec.ts` passes in one deterministic command with Chromium available in the container.
3. The smoke test still verifies the visible heading and at least one seeded rate row.
4. A direct backend check and frontend-proxy check are both represented in the test/debug output, so a proxy regression is distinguishable from a backend regression.
5. Host execution either documents `pnpm exec playwright install chromium` as an optional developer setup or is removed from the supported workflow; CI must not depend on the host browser cache.
6. No unrelated backend, database, or UI feature changes are included in this task.

### Required verification
```text
docker compose --profile test run --rm frontend-test pnpm exec playwright test --config /e2e/playwright.config.ts --reporter=line
```

Then run the full declared frontend test target and the live API/proxy smoke checks. Capture the exit code and browser output in the build artifact.

## Triage conclusion
The original “hang” had two layers: host Playwright lacked a browser binary, while the real containerized application path exposed a deterministic nginx path-rewrite bug. Fix the proxy contract first; keep browser installation inside the container. This is a rebuild task, not a reason to alter the backend API shape.
