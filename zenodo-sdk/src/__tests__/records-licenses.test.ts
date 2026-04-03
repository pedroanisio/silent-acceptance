import { describe, it, expect } from "vitest";
import { HttpClient } from "../client.js";
import { Records } from "../modules/records.js";
import { Licenses } from "../modules/licenses.js";
import { createMockFetch, mockResponse, testConfig, FIXTURES } from "./helpers.js";

describe("Records", () => {
  function setup(...responses: Response[]) {
    const mock = createMockFetch(...responses);
    const http = new HttpClient(testConfig(mock.fetch));
    const records = new Records(http);
    return { records, mock };
  }

  describe("search", () => {
    it("returns search result envelope", async () => {
      const { records } = setup(
        mockResponse({
          hits: { hits: [FIXTURES.record], total: 1 },
          links: { self: "https://sandbox.zenodo.org/api/records/" },
        })
      );

      const result = await records.search({ q: "PALS Law" });
      expect(result.hits.total).toBe(1);
      expect(result.hits.hits[0].doi).toBe("10.5072/zenodo.99001");
    });

    it("passes search params", async () => {
      const { records, mock } = setup(
        mockResponse({ hits: { hits: [], total: 0 } })
      );
      await records.search({ q: "PALS", sort: "mostrecent", page: 2, size: 10 });

      const url = new URL(mock.calls[0].url);
      expect(url.searchParams.get("q")).toBe("PALS");
      expect(url.searchParams.get("sort")).toBe("mostrecent");
      expect(url.searchParams.get("page")).toBe("2");
      expect(url.searchParams.get("size")).toBe("10");
    });
  });

  describe("get", () => {
    it("fetches a single record by ID", async () => {
      const { records, mock } = setup(mockResponse(FIXTURES.record));
      const rec = await records.get(99001);

      expect(rec.id).toBe(99001);
      expect(rec.doi).toBe("10.5072/zenodo.99001");
      expect(rec.metadata.title).toBe("PALS's Law — v1.5.4");
      expect(mock.calls[0].url).toContain("/records/99001");
    });
  });
});

describe("Licenses", () => {
  function setup(...responses: Response[]) {
    const mock = createMockFetch(...responses);
    const http = new HttpClient(testConfig(mock.fetch));
    const licenses = new Licenses(http);
    return { licenses, mock };
  }

  describe("search", () => {
    it("returns license array from hits envelope", async () => {
      const { licenses } = setup(
        mockResponse({ hits: { hits: [FIXTURES.license] } })
      );
      const result = await licenses.search("creative commons");
      expect(result).toHaveLength(1);
      expect(result[0].id).toBe("cc-by-4.0");
    });

    it("passes query string", async () => {
      const { licenses, mock } = setup(
        mockResponse({ hits: { hits: [] } })
      );
      await licenses.search("MIT");

      const url = new URL(mock.calls[0].url);
      expect(url.searchParams.get("q")).toBe("MIT");
    });
  });

  describe("get", () => {
    it("fetches single license by ID", async () => {
      const { licenses, mock } = setup(mockResponse(FIXTURES.license));
      const lic = await licenses.get("cc-by-4.0");

      expect(lic.id).toBe("cc-by-4.0");
      expect(lic.title).toContain("Creative Commons");
      expect(mock.calls[0].url).toContain("/licenses/cc-by-4.0");
    });
  });
});
