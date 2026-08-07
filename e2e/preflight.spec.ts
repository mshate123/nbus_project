import { expect, test } from "@playwright/test";

import { runPreflight } from "./helpers/preflight";

test("test_direct_backend_and_frontend_proxy_preserve_api_prefix", async ({
  request,
  baseURL,
}) => {
  const result = await runPreflight(request, {
    proxyBaseUrl: baseURL ?? "http://frontend",
  });

  expect(result.direct.status).toBe(200);
  expect(result.proxy.status).toBe(200);
  expect(result.direct.shape).toBe("array");
  expect(result.proxy.shape).toBe("array");
  expect(result.proxy.body).toEqual(result.direct.body);
  expect(result.proxy.url).toContain("/api/rate-schedule");
});

test("reports_direct_and_proxy_status_separately", async ({ request, baseURL }) => {
  const result = await runPreflight(request, {
    proxyBaseUrl: baseURL ?? "http://frontend",
  });

  expect(result.direct.label).toBe("direct");
  expect(result.proxy.label).toBe("proxy");
  expect(result.direct.url).toContain("/api/rate-schedule");
  expect(result.proxy.url).toContain("/api/rate-schedule");
  expect(result.direct.status).toBe(200);
  expect(result.proxy.status).toBe(200);
  expect(result.direct.shape).toBe("array");
  expect(result.proxy.shape).toBe("array");
});
