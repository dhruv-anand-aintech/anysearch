/** Thin fetch wrapper that normalizes provider errors. */

import {
  AuthenticationError,
  BadRequestError,
  ProviderConnectionError,
  ProviderError,
  ProviderTimeoutError,
  RateLimitError,
} from "./errors.js";

export const USER_AGENT = "anysearch-js/0.1.0";

export interface PreparedRequest {
  method: string;
  url: string;
  headers?: Record<string, string>;
  /** Query string params (scalars). */
  params?: Record<string, string | number | boolean | undefined>;
  /** JSON request body. */
  json?: unknown;
  /** Form-encoded body (e.g. DuckDuckGo HTML endpoint). */
  form?: Record<string, string>;
}

export interface HttpResponse {
  status: number;
  headers: Headers;
  text: string;
  data: any;
}

function short(text: string, limit = 500): string {
  const t = (text || "").trim().replace(/\s+/g, " ");
  return t.length <= limit ? t : t.slice(0, limit) + "…";
}

function errorMessage(res: HttpResponse): string {
  const body = res.data;
  if (body && typeof body === "object") {
    for (const key of ["error", "message", "detail", "error_message", "Message"]) {
      let val = (body as Record<string, unknown>)[key];
      if (val && typeof val === "object") {
        const v = val as Record<string, unknown>;
        val = (v.message as string) || (v.detail as string) || JSON.stringify(val);
      }
      if (val) return short(String(val));
    }
    return short(JSON.stringify(body));
  }
  return short(res.text);
}

function raiseForStatus(provider: string, res: HttpResponse): void {
  const code = res.status;
  if (code < 400) return;
  const message = errorMessage(res);
  const opts = { provider, statusCode: code, response: res.data ?? res.text };
  if (code === 401 || code === 403) throw new AuthenticationError(message, opts);
  if (code === 429) throw new RateLimitError(message, opts);
  if (code === 400 || code === 422) throw new BadRequestError(message, opts);
  throw new ProviderError(message, opts);
}

function buildUrl(url: string, params?: PreparedRequest["params"]): string {
  if (!params) return url;
  const usp = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue;
    usp.append(key, String(value));
  }
  const qs = usp.toString();
  return qs ? `${url}${url.includes("?") ? "&" : "?"}${qs}` : url;
}

export async function send(
  provider: string,
  prepared: PreparedRequest,
  timeoutMs = 30000,
): Promise<HttpResponse> {
  const headers: Record<string, string> = {
    "User-Agent": USER_AGENT,
    Accept: "application/json",
    ...(prepared.headers ?? {}),
  };

  let body: string | undefined;
  if (prepared.json !== undefined) {
    body = JSON.stringify(prepared.json);
    headers["Content-Type"] = headers["Content-Type"] ?? "application/json";
  } else if (prepared.form !== undefined) {
    body = new URLSearchParams(prepared.form).toString();
    headers["Content-Type"] = "application/x-www-form-urlencoded";
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let response: Response;
  try {
    response = await fetch(buildUrl(prepared.url, prepared.params), {
      method: prepared.method,
      headers,
      body,
      signal: controller.signal,
      redirect: "follow",
    });
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new ProviderTimeoutError(`Request timed out after ${timeoutMs}ms`, { provider });
    }
    throw new ProviderConnectionError(String(err), { provider });
  } finally {
    clearTimeout(timer);
  }

  const text = await response.text();
  let data: any = undefined;
  try {
    data = text ? JSON.parse(text) : undefined;
  } catch {
    data = undefined;
  }
  const result: HttpResponse = { status: response.status, headers: response.headers, text, data };
  raiseForStatus(provider, result);
  return result;
}
