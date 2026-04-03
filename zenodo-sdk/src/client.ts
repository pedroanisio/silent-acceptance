// ─────────────────────────────────────────────────────────────
// Zenodo SDK — HTTP Client
// ─────────────────────────────────────────────────────────────

import type { ZenodoConfig, ZenodoErrorResponse } from "./types.js";
import { ZenodoError, ZenodoNetworkError, ZenodoTimeoutError } from "./errors.js";

const PRODUCTION_URL = "https://zenodo.org/api";
const SANDBOX_URL = "https://sandbox.zenodo.org/api";
const DEFAULT_TIMEOUT = 30_000;

export class HttpClient {
  public readonly baseUrl: string;
  private readonly token: string;
  private readonly timeout: number;
  private readonly _fetch: typeof fetch;

  constructor(config: ZenodoConfig) {
    this.token = config.token;
    this.timeout = config.timeout ?? DEFAULT_TIMEOUT;
    this._fetch = config.fetchImpl ?? globalThis.fetch;

    if (config.sandbox) {
      this.baseUrl = SANDBOX_URL;
    } else {
      this.baseUrl = (config.baseUrl ?? PRODUCTION_URL).replace(/\/+$/, "");
    }
  }

  // ── Core request method ─────────────────────────────────

  async request<T>(
    method: string,
    path: string,
    options: {
      body?: unknown;
      rawBody?: BodyInit;
      headers?: Record<string, string>;
      params?: Record<string, string | number | boolean | undefined>;
      /** Use an absolute URL instead of baseUrl + path */
      absoluteUrl?: string;
      /** Skip JSON parsing (for 204 No Content) */
      noContent?: boolean;
    } = {}
  ): Promise<T> {
    const url = new URL(options.absoluteUrl ?? `${this.baseUrl}${path}`);

    if (options.params) {
      for (const [k, v] of Object.entries(options.params)) {
        if (v !== undefined) url.searchParams.set(k, String(v));
      }
    }

    const headers: Record<string, string> = {
      Authorization: `Bearer ${this.token}`,
      ...options.headers,
    };

    let body: BodyInit | undefined;
    if (options.rawBody !== undefined) {
      body = options.rawBody;
    } else if (options.body !== undefined) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(options.body);
    }

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);

    let response: Response;
    try {
      response = await this._fetch(url.toString(), {
        method,
        headers,
        body,
        signal: controller.signal,
      });
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === "AbortError") {
        throw new ZenodoTimeoutError(url.toString(), this.timeout);
      }
      throw new ZenodoNetworkError(
        `Network error: ${err instanceof Error ? err.message : String(err)}`,
        err
      );
    } finally {
      clearTimeout(timer);
    }

    if (options.noContent && response.status === 204) {
      return undefined as T;
    }

    const text = await response.text();
    let json: unknown;
    try {
      json = text ? JSON.parse(text) : undefined;
    } catch {
      // Non-JSON response on error
      if (!response.ok) {
        throw new ZenodoError({
          message: text || response.statusText,
          status: response.status,
        });
      }
    }

    if (!response.ok) {
      throw new ZenodoError(json as ZenodoErrorResponse);
    }

    return json as T;
  }

  // ── Convenience verbs ───────────────────────────────────

  get<T>(path: string, params?: Record<string, string | number | boolean | undefined>) {
    return this.request<T>("GET", path, { params });
  }

  post<T>(path: string, body?: unknown) {
    return this.request<T>("POST", path, { body: body ?? {} });
  }

  put<T>(path: string, body?: unknown) {
    return this.request<T>("PUT", path, { body });
  }

  delete<T = void>(path: string) {
    return this.request<T>("DELETE", path, { noContent: true });
  }

  /** PUT raw binary data (for file uploads to bucket URL) */
  putBinary<T>(absoluteUrl: string, data: BodyInit, contentType: string) {
    return this.request<T>("PUT", "", {
      absoluteUrl,
      rawBody: data,
      headers: { "Content-Type": contentType },
    });
  }
}
