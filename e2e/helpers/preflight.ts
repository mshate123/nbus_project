import type { APIRequestContext } from "@playwright/test";

export type EndpointDiagnostic = {
  label: "direct" | "proxy";
  url: string;
  status: number;
  shape: string;
  body: unknown;
};

export type PreflightResult = {
  backendHealth: { status: number; body: unknown };
  backendReady: { status: number; body: unknown };
  frontendReachable: { status: number };
  accountsSeeded: { status: number; count: number };
  direct: EndpointDiagnostic;
  proxy: EndpointDiagnostic;
};

function responseShape(body: unknown): string {
  if (Array.isArray(body)) return "array";
  if (body === null) return "null";
  return typeof body;
}

function parseResponseBody(text: string): unknown {
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

async function inspectEndpoint(
  request: APIRequestContext,
  label: EndpointDiagnostic["label"],
  url: string,
): Promise<EndpointDiagnostic> {
  const response = await request.get(url);
  const body = parseResponseBody(await response.text());
  const diagnostic: EndpointDiagnostic = {
    label,
    url,
    status: response.status(),
    shape: responseShape(body),
    body,
  };

  console.log(
    `[preflight] ${label} url=${diagnostic.url} status=${diagnostic.status} shape=${diagnostic.shape}`,
  );
  return diagnostic;
}

export async function runPreflight(
  request: APIRequestContext,
  options: {
    directBaseUrl?: string;
    proxyBaseUrl: string;
    path?: string;
  },
): Promise<PreflightResult> {
  const path = options.path ?? "/api/rate-schedule";
  const directBaseUrl =
    options.directBaseUrl ?? process.env.E2E_DIRECT_API_URL ?? "http://api:8000";
  const proxyBaseUrl = options.proxyBaseUrl.replace(/\/$/, "");
  const directUrl = `${directBaseUrl.replace(/\/$/, "")}${path}`;
  const proxyUrl = `${proxyBaseUrl}${path}`;

  // 1. Backend health check (liveness — no DB required)
  const healthResp = await request.get(`${directBaseUrl.replace(/\/$/, "")}/health`);
  const healthBody = parseResponseBody(await healthResp.text());
  console.log(`[preflight] backend /health status=${healthResp.status()}`);

  // 2. Backend readiness check (DB connectivity)
  const readyResp = await request.get(`${directBaseUrl.replace(/\/$/, "")}/ready`);
  const readyBody = parseResponseBody(await readyResp.text());
  console.log(`[preflight] backend /ready status=${readyResp.status()}`);

  // 3. Frontend reachability (serves HTML at /)
  const frontendResp = await request.get(proxyBaseUrl);
  console.log(`[preflight] frontend / status=${frontendResp.status()}`);

  // 4. Database seeded check (accounts exist)
  const accountsResp = await request.get(
    `${directBaseUrl.replace(/\/$/, "")}/api/accounts`,
  );
  const accountsBody = parseResponseBody(await accountsResp.text());
  const accountsCount = Array.isArray(accountsBody) ? accountsBody.length : 0;
  console.log(
    `[preflight] /api/accounts status=${accountsResp.status()} count=${accountsCount}`,
  );

  // 5. Direct vs proxy comparison on the specified path
  const [direct, proxy] = await Promise.all([
    inspectEndpoint(request, "direct", directUrl),
    inspectEndpoint(request, "proxy", proxyUrl),
  ]);

  return {
    backendHealth: { status: healthResp.status(), body: healthBody },
    backendReady: { status: readyResp.status(), body: readyBody },
    frontendReachable: { status: frontendResp.status() },
    accountsSeeded: { status: accountsResp.status(), count: accountsCount },
    direct,
    proxy,
  };
}
