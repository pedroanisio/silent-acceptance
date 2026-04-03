import { describe, it, expect } from "vitest";
import { HttpClient } from "../client.js";
import { ZenodoError, ZenodoNetworkError, ZenodoTimeoutError } from "../errors.js";
import { createMockFetch, mockResponse, testConfig } from "./helpers.js";

describe("HttpClient", () => {
  describe("constructor", () => {
    it("uses sandbox URL when sandbox: true", () => {
      const mock = createMockFetch();
      const client = new HttpClient(testConfig(mock.fetch));
      expect(client.baseUrl).toBe("https://sandbox.zenodo.org/api");
    });

    it("uses production URL by default", () => {
      const mock = createMockFetch();
      const client = new HttpClient({
        token: "t",
        fetchImpl: mock.fetch,
      });
      expect(client.baseUrl).toBe("https://zenodo.org/api");
    });

    it("respects custom baseUrl", () => {
      const mock = createMockFetch();
      const client = new HttpClient({
        token: "t",
        baseUrl: "https://custom.zenodo.example/api/",
        fetchImpl: mock.fetch,
      });
      expect(client.baseUrl).toBe("https://custom.zenodo.example/api");
    });

    it("sandbox overrides baseUrl", () => {
      const mock = createMockFetch();
      const client = new HttpClient({
        token: "t",
        baseUrl: "https://custom.example/api",
        sandbox: true,
        fetchImpl: mock.fetch,
      });
      expect(client.baseUrl).toBe("https://sandbox.zenodo.org/api");
    });
  });

  describe("request", () => {
    it("sends Bearer token in Authorization header", async () => {
      const mock = createMockFetch(mockResponse({ ok: true }));
      const client = new HttpClient(testConfig(mock.fetch));
      await client.get("/test");

      expect(mock.calls).toHaveLength(1);
      const headers = mock.calls[0].init.headers as Record<string, string>;
      expect(headers["Authorization"]).toBe("Bearer test-token-abc123");
    });

    it("appends query params to URL", async () => {
      const mock = createMockFetch(mockResponse({ ok: true }));
      const client = new HttpClient(testConfig(mock.fetch));
      await client.get("/test", { q: "pals", size: 10 });

      const url = new URL(mock.calls[0].url);
      expect(url.searchParams.get("q")).toBe("pals");
      expect(url.searchParams.get("size")).toBe("10");
    });

    it("omits undefined query params", async () => {
      const mock = createMockFetch(mockResponse({ ok: true }));
      const client = new HttpClient(testConfig(mock.fetch));
      await client.get("/test", { q: "pals", size: undefined });

      const url = new URL(mock.calls[0].url);
      expect(url.searchParams.get("q")).toBe("pals");
      expect(url.searchParams.has("size")).toBe(false);
    });

    it("sends JSON body with Content-Type header for POST", async () => {
      const mock = createMockFetch(mockResponse({ id: 1 }));
      const client = new HttpClient(testConfig(mock.fetch));
      await client.post("/deposit/depositions", { metadata: { title: "Test" } });

      expect(mock.calls[0].init.method).toBe("POST");
      const headers = mock.calls[0].init.headers as Record<string, string>;
      expect(headers["Content-Type"]).toBe("application/json");
      expect(mock.calls[0].init.body).toBe(JSON.stringify({ metadata: { title: "Test" } }));
    });

    it("handles 204 No Content for DELETE", async () => {
      const mock = createMockFetch(mockResponse(undefined, { status: 204 }));
      const client = new HttpClient(testConfig(mock.fetch));
      const result = await client.delete("/deposit/depositions/123");
      expect(result).toBeUndefined();
    });
  });

  describe("error handling", () => {
    it("throws ZenodoError on 4xx with error body", async () => {
      const mock = createMockFetch(
        mockResponse(
          { message: "Validation error", status: 400, errors: [{ field: "metadata.title", message: "Required" }] },
          { status: 400 }
        )
      );
      const client = new HttpClient(testConfig(mock.fetch));

      await expect(client.post("/deposit/depositions", {})).rejects.toThrow(ZenodoError);
      try {
        await client.post("/deposit/depositions", {});
      } catch {
        // already asserted above — mock is consumed
      }
    });

    it("ZenodoError includes field-level detail", async () => {
      const errorBody = {
        message: "Validation error",
        status: 400,
        errors: [
          { field: "metadata.title", message: "Required" },
          { field: "metadata.creators", message: "Must have at least one creator" },
        ],
      };
      const mock = createMockFetch(mockResponse(errorBody, { status: 400 }));
      const client = new HttpClient(testConfig(mock.fetch));

      try {
        await client.post("/test", {});
        expect.unreachable("Should have thrown");
      } catch (err) {
        expect(err).toBeInstanceOf(ZenodoError);
        const zenodoErr = err as ZenodoError;
        expect(zenodoErr.status).toBe(400);
        expect(zenodoErr.errors).toHaveLength(2);
        expect(zenodoErr.message).toContain("metadata.title");
        expect(zenodoErr.message).toContain("metadata.creators");
      }
    });

    it("throws ZenodoNetworkError on fetch failure", async () => {
      const fetchImpl = async () => {
        throw new TypeError("fetch failed");
      };
      const client = new HttpClient(testConfig(fetchImpl as typeof fetch));

      await expect(client.get("/test")).rejects.toThrow(ZenodoNetworkError);
    });

    it("throws ZenodoTimeoutError on abort", async () => {
      const fetchImpl = async (_url: string, init?: RequestInit) => {
        // Simulate abort by listening to the signal
        return new Promise<Response>((_resolve, reject) => {
          if (init?.signal) {
            init.signal.addEventListener("abort", () => {
              const err = new DOMException("The operation was aborted.", "AbortError");
              reject(err);
            });
          }
        });
      };
      const client = new HttpClient({
        token: "t",
        sandbox: true,
        timeout: 50, // very short timeout
        fetchImpl: fetchImpl as typeof fetch,
      });

      await expect(client.get("/test")).rejects.toThrow(ZenodoTimeoutError);
    });
  });

  describe("putBinary", () => {
    it("sends raw body to absolute URL with custom content-type", async () => {
      const mock = createMockFetch(mockResponse({ key: "test.md" }));
      const client = new HttpClient(testConfig(mock.fetch));

      const data = new Uint8Array([72, 101, 108, 108, 111]); // "Hello"
      await client.putBinary(
        "https://sandbox.zenodo.org/api/files/bucket-uuid/test.md",
        data,
        "text/markdown"
      );

      expect(mock.calls[0].url).toBe("https://sandbox.zenodo.org/api/files/bucket-uuid/test.md");
      expect(mock.calls[0].init.method).toBe("PUT");
      const headers = mock.calls[0].init.headers as Record<string, string>;
      expect(headers["Content-Type"]).toBe("text/markdown");
    });
  });
});
