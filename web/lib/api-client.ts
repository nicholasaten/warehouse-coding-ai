import { getAccessToken, setAccessToken } from "./token-store";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function rawFetch(path: string, init?: RequestInit): Promise<Response> {
  const token = getAccessToken();
  const headers = new Headers(init?.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(`${API_URL}${path}`, { ...init, headers, credentials: "include" });
}

async function tryRefresh(): Promise<boolean> {
  const res = await fetch(`${API_URL}/auth/refresh`, { method: "POST", credentials: "include" });
  if (!res.ok) return false;
  const data = await res.json();
  setAccessToken(data.access_token);
  return true;
}

/** Fetch wrapper: attaches the Bearer token, sends the refresh cookie, and
 * retries once through /auth/refresh on a 401 -- except for auth endpoints
 * themselves, where that retry would just recurse. */
export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  let res = await rawFetch(path, init);
  const isAuthEndpoint = path === "/auth/refresh" || path === "/auth/login";
  if (res.status === 401 && !isAuthEndpoint) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      res = await rawFetch(path, init);
    }
  }
  return res;
}

export async function apiJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await apiFetch(path, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      // response wasn't JSON -- keep statusText
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}
