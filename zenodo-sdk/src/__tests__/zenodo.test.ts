import { describe, it, expect } from "vitest";
import { Zenodo } from "../zenodo.js";
import { Depositions } from "../modules/depositions.js";
import { Files } from "../modules/files.js";
import { Records } from "../modules/records.js";
import { Licenses } from "../modules/licenses.js";
import { createMockFetch, mockResponse, testConfig } from "./helpers.js";

describe("Zenodo", () => {
  it("exposes all four modules", () => {
    const mock = createMockFetch();
    const zen = new Zenodo(testConfig(mock.fetch));

    expect(zen.depositions).toBeInstanceOf(Depositions);
    expect(zen.files).toBeInstanceOf(Files);
    expect(zen.records).toBeInstanceOf(Records);
    expect(zen.licenses).toBeInstanceOf(Licenses);
  });

  it("exposes the raw HTTP client", () => {
    const mock = createMockFetch();
    const zen = new Zenodo(testConfig(mock.fetch));

    expect(zen.http).toBeDefined();
    expect(zen.http.baseUrl).toBe("https://sandbox.zenodo.org/api");
  });

  describe("isSandbox", () => {
    it("returns true for sandbox config", () => {
      const mock = createMockFetch();
      const zen = new Zenodo(testConfig(mock.fetch));
      expect(zen.isSandbox).toBe(true);
    });

    it("returns false for production config", () => {
      const mock = createMockFetch();
      const zen = new Zenodo({ token: "t", fetchImpl: mock.fetch });
      expect(zen.isSandbox).toBe(false);
    });
  });

  describe("ping", () => {
    it("returns true when depositions.list succeeds", async () => {
      const mock = createMockFetch(mockResponse([]));
      const zen = new Zenodo(testConfig(mock.fetch));
      expect(await zen.ping()).toBe(true);
    });

    it("returns false when depositions.list fails", async () => {
      const mock = createMockFetch(
        mockResponse({ message: "Unauthorized", status: 401 }, { status: 401 })
      );
      const zen = new Zenodo(testConfig(mock.fetch));
      expect(await zen.ping()).toBe(false);
    });
  });
});
