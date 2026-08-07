import type { APIRequestContext } from "@playwright/test";

export type EndpointDiagnostic = {
  label: "direct" | "proxy";
  url: string;
  status: number;
  shape: string;
  body: unknown;
};

export type PreflightResult = {
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
  const directUrl = `${directBaseUrl.replace(/\/$/, "")}${path}`;
  const proxyUrl = `${options.proxyBaseUrl.replace(/\/$/, "")}${path}`;

  const [direct, proxy] = await Promise.all([
    inspectEndpoint(request, "direct", directUrl),
    inspectEndpoint(request, "proxy", proxyUrl),
  ]);

  return { direct, proxy };
}
