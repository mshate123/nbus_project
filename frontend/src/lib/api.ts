/**
 * API client — thin wrapper around fetch.
 * All requests go through the /api prefix, proxied by nginx to the backend.
 */

const BASE = "/api";

/** Generic fetch helper — throws on non-2xx responses. */
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail?.detail ?? `HTTP ${res.status}`);
  }

  return res.json() as Promise<T>;
}

// ── Types ────────────────────────────────────────────────────────────────────

export interface Account {
  id: string;
  code: string;
  name: string;
  type: "ASSET" | "LIABILITY" | "EQUITY" | "REVENUE" | "EXPENSE";
  normal_balance: "DEBIT" | "CREDIT";
  active: boolean;
}

export interface BalanceResponse {
  account_id: string;
  balance: string;
}

export interface StatementLine {
  entry_id: string;
  posted_at: string;
  debit: string;
  credit: string;
  running_balance: string;
  reversal_of_id?: string | null;
}

export interface AccountStatement {
  account_id: string;
  lines: StatementLine[];
}

export interface RateScheduleEntry {
  tier: string;
  annual_rate: string;
}

// ── API functions ─────────────────────────────────────────────────────────────

/** Fetch all accounts. */
export const getAccounts = (): Promise<Account[]> =>
  request<Account[]>("/accounts");

/** Fetch real-time balance for an account. */
export const getBalance = (accountId: string): Promise<BalanceResponse> =>
  request<BalanceResponse>(`/accounts/${accountId}/balance`);

/** Fetch statement with running balance for an account. */
export const getStatement = (accountId: string): Promise<AccountStatement> =>
  request<AccountStatement>(`/accounts/${accountId}/statement`);

/** Fetch the full interest rate schedule. */
export const getRateSchedule = (): Promise<RateScheduleEntry[]> =>
  request<RateScheduleEntry[]>("/rate-schedule");
