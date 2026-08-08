import { expect, test } from "@playwright/test";

import { runPreflight } from "./helpers/preflight";

/**
 * Preflight checks verify that all services are reachable and properly
 * configured before running the main E2E suite. These should run first
 * and fail fast with clear diagnostics if the stack is unhealthy.
 */

test("backend API is alive (health endpoint)", async ({ request }) => {
  const directBaseUrl = process.env.E2E_DIRECT_API_URL ?? "http://api:8000";
  const resp = await request.get(`${directBaseUrl}/health`);
  expect(resp.status()).toBe(200);
  expect(await resp.json()).toEqual({ status: "ok" });
});

test("backend database is ready (ready endpoint)", async ({ request }) => {
  const directBaseUrl = process.env.E2E_DIRECT_API_URL ?? "http://api:8000";
  const resp = await request.get(`${directBaseUrl}/ready`);
  expect(resp.status()).toBe(200);
  expect(await resp.json()).toEqual({ status: "ok" });
});

test("frontend is reachable (serves HTML at /)", async ({ request, baseURL }) => {
  const resp = await request.get(baseURL ?? "http://frontend");
  expect(resp.status()).toBe(200);
});

test("database is seeded (accounts exist)", async ({ request }) => {
  const directBaseUrl = process.env.E2E_DIRECT_API_URL ?? "http://api:8000";
  const resp = await request.get(`${directBaseUrl}/api/accounts`);
  expect(resp.status()).toBe(200);
  const accounts = await resp.json();
  expect(Array.isArray(accounts)).toBe(true);
  expect(accounts.length).toBeGreaterThan(0);
});

test("direct backend and frontend proxy preserve /api prefix", async ({
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

test("reports direct and proxy status separately", async ({ request, baseURL }) => {
  const result = await runPreflight(request, {
    proxyBaseUrl: baseURL ?? "http://frontend",
  });

  expect(result.direct.label).toBe("direct");
  expect(result.proxy.label).toBe("proxy");
  expect(result.direct.url).toContain("/api/rate-schedule");
  expect(result.proxy.url).toContain("/api/rate-schedule");
});
