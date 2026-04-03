import { describe, it, expect } from "vitest";
import { readFile, stat } from "node:fs/promises";
import { resolve } from "node:path";
import { HttpClient } from "../client.js";
import { Files } from "../modules/files.js";
import { createMockFetch, mockResponse, testConfig, FIXTURES } from "./helpers.js";

/** Path to the real PALS_LAW-v1.5.4.md in the parent repo. */
const PALS_LAW_PATH = resolve(import.meta.dirname, "../../../PALS_LAW-v1.5.4.md");

function setup(...responses: Response[]) {
  const mock = createMockFetch(...responses);
  const http = new HttpClient(testConfig(mock.fetch));
  const files = new Files(http);
  return { files, mock };
}

describe("Files", () => {
  describe("list", () => {
    it("lists files for a deposition", async () => {
      const { files, mock } = setup(mockResponse([FIXTURES.depositionFile]));
      const result = await files.list(99001);

      expect(result).toHaveLength(1);
      expect(result[0].name).toBe("PALS_LAW-v1.5.4.md");
      expect(mock.calls[0].url).toContain("/deposit/depositions/99001/files");
    });
  });

  describe("upload", () => {
    it("PUTs binary data to the bucket URL", async () => {
      const { files, mock } = setup(mockResponse(FIXTURES.bucketFile));
      const data = new TextEncoder().encode("# Test content");

      const result = await files.upload(FIXTURES.deposition, "test.md", data);

      expect(result.key).toBe("PALS_LAW-v1.5.4.md");
      expect(mock.calls[0].url).toBe(
        "https://sandbox.zenodo.org/api/files/bucket-uuid-1234/test.md"
      );
      expect(mock.calls[0].init.method).toBe("PUT");
    });

    it("defaults to application/octet-stream", async () => {
      const { files, mock } = setup(mockResponse(FIXTURES.bucketFile));
      const data = new TextEncoder().encode("{}");
      await files.upload(FIXTURES.deposition, "schema.json", data);

      const headers = mock.calls[0].init.headers as Record<string, string>;
      expect(headers["Content-Type"]).toBe("application/octet-stream");
    });

    it("uses provided content type over default", async () => {
      const { files, mock } = setup(mockResponse(FIXTURES.bucketFile));
      const data = new TextEncoder().encode("# markdown");
      await files.upload(FIXTURES.deposition, "doc.md", data, "text/x-markdown");

      const headers = mock.calls[0].init.headers as Record<string, string>;
      expect(headers["Content-Type"]).toBe("text/x-markdown");
    });

    it("encodes filename in URL", async () => {
      const { files, mock } = setup(mockResponse(FIXTURES.bucketFile));
      const data = new TextEncoder().encode("data");
      await files.upload(FIXTURES.deposition, "file with spaces.md", data);

      expect(mock.calls[0].url).toContain("file%20with%20spaces.md");
    });
  });

  describe("uploadFromPath — real PALS_LAW-v1.5.4.md", () => {
    it("reads and uploads the actual spec file", async () => {
      // Verify the fixture file exists
      const info = await stat(PALS_LAW_PATH);
      expect(info.isFile()).toBe(true);
      expect(info.size).toBeGreaterThan(0);

      const fileContent = await readFile(PALS_LAW_PATH);

      const { files, mock } = setup(mockResponse({
        ...FIXTURES.bucketFile,
        key: "PALS_LAW-v1.5.4.md",
        size: fileContent.byteLength,
      }));

      const result = await files.uploadFromPath(FIXTURES.deposition, PALS_LAW_PATH);

      // Verify correct filename extracted from path
      expect(mock.calls[0].url).toContain("PALS_LAW-v1.5.4.md");
      // Verify response
      expect(result.key).toBe("PALS_LAW-v1.5.4.md");
      expect(result.size).toBe(fileContent.byteLength);
    });

    it("allows overriding the upload filename", async () => {
      const { files, mock } = setup(mockResponse(FIXTURES.bucketFile));
      await files.uploadFromPath(FIXTURES.deposition, PALS_LAW_PATH, "pals-law-spec.md");

      expect(mock.calls[0].url).toContain("pals-law-spec.md");
      expect(mock.calls[0].url).not.toContain("PALS_LAW-v1.5.4.md");
    });

    it("sends the full file content as PUT body", async () => {
      const fileContent = await readFile(PALS_LAW_PATH);
      const { files, mock } = setup(mockResponse(FIXTURES.bucketFile));

      await files.uploadFromPath(FIXTURES.deposition, PALS_LAW_PATH);

      // The raw body should be a Buffer with the same byte length
      const sentBody = mock.calls[0].init.body as Uint8Array;
      expect(sentBody.byteLength).toBe(fileContent.byteLength);
    });
  });

  describe("uploadLegacy", () => {
    it("sends multipart form data to files endpoint", async () => {
      const { files, mock } = setup(mockResponse(FIXTURES.depositionFile));
      const data = new TextEncoder().encode("# Test");

      const result = await files.uploadLegacy(99001, "test.md", data);

      expect(result.name).toBe("PALS_LAW-v1.5.4.md");
      expect(mock.calls[0].url).toContain("/deposit/depositions/99001/files");
      expect(mock.calls[0].init.method).toBe("POST");
      // Body should be FormData
      expect(mock.calls[0].init.body).toBeInstanceOf(FormData);
    });
  });

  describe("sort", () => {
    it("sends PUT with file ordering", async () => {
      const { files, mock } = setup(mockResponse([FIXTURES.depositionFile]));
      await files.sort(99001, [{ id: "file-uuid-1" }, { id: "file-uuid-2" }]);

      expect(mock.calls[0].init.method).toBe("PUT");
      const body = JSON.parse(mock.calls[0].init.body as string);
      expect(body).toEqual([{ id: "file-uuid-1" }, { id: "file-uuid-2" }]);
    });
  });

  describe("get", () => {
    it("fetches single file metadata", async () => {
      const { files, mock } = setup(mockResponse(FIXTURES.depositionFile));
      const result = await files.get(99001, "file-uuid-1");

      expect(result.id).toBe("file-uuid-1");
      expect(mock.calls[0].url).toContain("/deposit/depositions/99001/files/file-uuid-1");
    });
  });

  describe("delete", () => {
    it("sends DELETE for a file", async () => {
      const { files, mock } = setup(mockResponse(undefined, { status: 204 }));
      await files.delete(99001, "file-uuid-1");

      expect(mock.calls[0].init.method).toBe("DELETE");
      expect(mock.calls[0].url).toContain("/deposit/depositions/99001/files/file-uuid-1");
    });
  });
});
