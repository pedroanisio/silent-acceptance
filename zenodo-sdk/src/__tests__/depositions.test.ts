import { describe, it, expect } from "vitest";
import { HttpClient } from "../client.js";
import { Depositions } from "../modules/depositions.js";
import { createMockFetch, mockResponse, testConfig, FIXTURES } from "./helpers.js";

function setup(...responses: Response[]) {
  const mock = createMockFetch(...responses);
  const http = new HttpClient(testConfig(mock.fetch));
  const depositions = new Depositions(http);
  return { depositions, mock };
}

describe("Depositions", () => {
  describe("list", () => {
    it("returns deposition array", async () => {
      const { depositions } = setup(mockResponse([FIXTURES.deposition]));
      const result = await depositions.list();
      expect(result).toHaveLength(1);
      expect(result[0].id).toBe(99001);
    });

    it("passes search params", async () => {
      const { depositions, mock } = setup(mockResponse([]));
      await depositions.list({ q: "PALS", status: "draft", size: 5 });

      const url = new URL(mock.calls[0].url);
      expect(url.searchParams.get("q")).toBe("PALS");
      expect(url.searchParams.get("status")).toBe("draft");
      expect(url.searchParams.get("size")).toBe("5");
    });
  });

  describe("get", () => {
    it("fetches single deposition by ID", async () => {
      const { depositions, mock } = setup(mockResponse(FIXTURES.deposition));
      const dep = await depositions.get(99001);

      expect(dep.id).toBe(99001);
      expect(dep.title).toBe("PALS's Law — v1.5.4");
      expect(mock.calls[0].url).toContain("/deposit/depositions/99001");
    });
  });

  describe("create", () => {
    it("creates empty deposition when no metadata given", async () => {
      const { depositions, mock } = setup(mockResponse(FIXTURES.deposition));
      await depositions.create();

      const body = JSON.parse(mock.calls[0].init.body as string);
      expect(body).toEqual({});
    });

    it("creates deposition with metadata", async () => {
      const { depositions, mock } = setup(mockResponse(FIXTURES.deposition));
      await depositions.create({
        title: "PALS's Law — v1.5.4",
        upload_type: "publication",
        publication_type: "preprint",
        description: "Test",
        creators: [{ name: "de Luna e Silva, Pedro Anisio" }],
      });

      const body = JSON.parse(mock.calls[0].init.body as string);
      expect(body.metadata.title).toBe("PALS's Law — v1.5.4");
      expect(body.metadata.upload_type).toBe("publication");
      expect(body.metadata.creators).toHaveLength(1);
    });

    it("returns deposition with prereserved DOI", async () => {
      const { depositions } = setup(mockResponse(FIXTURES.deposition));
      const dep = await depositions.create({
        title: "Test",
        upload_type: "publication",
        description: "Test",
        creators: [{ name: "Test, Author" }],
      });

      expect(dep.metadata.prereserve_doi?.doi).toBe("10.5072/zenodo.99001");
    });
  });

  describe("update", () => {
    it("sends PUT with full metadata replacement", async () => {
      const { depositions, mock } = setup(mockResponse(FIXTURES.deposition));
      await depositions.update(99001, {
        title: "Updated Title",
        upload_type: "publication",
        description: "Updated",
        creators: [{ name: "Test, Author" }],
      });

      expect(mock.calls[0].init.method).toBe("PUT");
      expect(mock.calls[0].url).toContain("/deposit/depositions/99001");
      const body = JSON.parse(mock.calls[0].init.body as string);
      expect(body.metadata.title).toBe("Updated Title");
    });
  });

  describe("publish", () => {
    it("posts to publish action endpoint", async () => {
      const { depositions, mock } = setup(mockResponse(FIXTURES.publishedDeposition));
      const result = await depositions.publish(99001);

      expect(mock.calls[0].url).toContain("/deposit/depositions/99001/actions/publish");
      expect(mock.calls[0].init.method).toBe("POST");
      expect(result.state).toBe("done");
      expect(result.submitted).toBe(true);
      expect(result.doi).toBe("10.5072/zenodo.99001");
    });
  });

  describe("edit", () => {
    it("posts to edit action endpoint", async () => {
      const { depositions, mock } = setup(mockResponse(FIXTURES.deposition));
      await depositions.edit(99001);
      expect(mock.calls[0].url).toContain("/deposit/depositions/99001/actions/edit");
    });
  });

  describe("discard", () => {
    it("posts to discard action endpoint", async () => {
      const { depositions, mock } = setup(mockResponse(FIXTURES.deposition));
      await depositions.discard(99001);
      expect(mock.calls[0].url).toContain("/deposit/depositions/99001/actions/discard");
    });
  });

  describe("newVersion", () => {
    it("posts to newversion action endpoint", async () => {
      const { depositions, mock } = setup(mockResponse(FIXTURES.deposition));
      await depositions.newVersion(99001);
      expect(mock.calls[0].url).toContain("/deposit/depositions/99001/actions/newversion");
    });
  });

  describe("delete", () => {
    it("sends DELETE request", async () => {
      const { depositions, mock } = setup(mockResponse(undefined, { status: 204 }));
      await depositions.delete(99001);
      expect(mock.calls[0].init.method).toBe("DELETE");
      expect(mock.calls[0].url).toContain("/deposit/depositions/99001");
    });
  });
});
