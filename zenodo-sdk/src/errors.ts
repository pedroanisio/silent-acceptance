// ─────────────────────────────────────────────────────────────
// Zenodo SDK — Error Handling
// ─────────────────────────────────────────────────────────────

import type { ZenodoErrorResponse } from "./types.js";

export class ZenodoError extends Error {
  public readonly status: number;
  public readonly errors?: Array<{ field?: string; message: string }>;
  public readonly raw: ZenodoErrorResponse;

  constructor(response: ZenodoErrorResponse) {
    const detail = response.errors
      ?.map((e) => (e.field ? `${e.field}: ${e.message}` : e.message))
      .join("; ");

    const msg = detail
      ? `[${response.status}] ${response.message} — ${detail}`
      : `[${response.status}] ${response.message}`;

    super(msg);
    this.name = "ZenodoError";
    this.status = response.status;
    this.errors = response.errors;
    this.raw = response;
  }
}

export class ZenodoNetworkError extends Error {
  public readonly cause: unknown;

  constructor(message: string, cause?: unknown) {
    super(message);
    this.name = "ZenodoNetworkError";
    this.cause = cause;
  }
}

export class ZenodoTimeoutError extends Error {
  constructor(url: string, timeoutMs: number) {
    super(`Request to ${url} timed out after ${timeoutMs}ms`);
    this.name = "ZenodoTimeoutError";
  }
}
