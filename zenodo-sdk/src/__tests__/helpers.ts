// ─────────────────────────────────────────────────────────────
// Test Helpers — Mock fetch factory for Zenodo SDK tests
// ─────────────────────────────────────────────────────────────

import type { ZenodoConfig } from "../types.js";

/**
 * Build a mock Response that behaves like the native fetch Response.
 */
export function mockResponse(
  body: unknown,
  init: { status?: number; headers?: Record<string, string> } = {}
): Response {
  const status = init.status ?? 200;
  const text = body === undefined ? "" : JSON.stringify(body);
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 204 ? "No Content" : "OK",
    headers: new Headers(init.headers),
    text: async () => text,
    json: async () => JSON.parse(text),
  } as Response;
}

/**
 * Create a mock fetch that returns queued responses in order.
 * After all queued responses are consumed, returns a 500.
 */
export function createMockFetch(
  ...responses: Response[]
): { fetch: typeof globalThis.fetch; calls: Array<{ url: string; init: RequestInit }> } {
  const calls: Array<{ url: string; init: RequestInit }> = [];
  let index = 0;

  const fetchImpl = async (
    input: string | URL | Request,
    init?: RequestInit
  ): Promise<Response> => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    calls.push({ url, init: init ?? {} });
    if (index < responses.length) {
      return responses[index++];
    }
    return mockResponse({ message: "No more mocked responses", status: 500 }, { status: 500 });
  };

  return { fetch: fetchImpl as typeof globalThis.fetch, calls };
}

/**
 * Standard test config pointing at sandbox with a mock fetch.
 */
export function testConfig(
  fetchImpl: typeof globalThis.fetch
): ZenodoConfig {
  return {
    token: "test-token-abc123",
    sandbox: true,
    timeout: 5_000,
    fetchImpl,
  };
}

// ── Fixture data ──────────────────────────────────────────────

export const FIXTURES = {
  deposition: {
    conceptrecid: "123456",
    created: "2026-04-03T00:00:00+00:00",
    doi: "",
    doi_url: "",
    files: [],
    id: 99001,
    links: {
      bucket: "https://sandbox.zenodo.org/api/files/bucket-uuid-1234",
      discard: "https://sandbox.zenodo.org/api/deposit/depositions/99001/actions/discard",
      edit: "https://sandbox.zenodo.org/api/deposit/depositions/99001/actions/edit",
      files: "https://sandbox.zenodo.org/api/deposit/depositions/99001/files",
      html: "https://sandbox.zenodo.org/deposit/99001",
      latest_draft: "https://sandbox.zenodo.org/api/deposit/depositions/99001",
      latest_draft_html: "https://sandbox.zenodo.org/deposit/99001",
      publish: "https://sandbox.zenodo.org/api/deposit/depositions/99001/actions/publish",
      self: "https://sandbox.zenodo.org/api/deposit/depositions/99001",
    },
    metadata: {
      title: "PALS's Law — v1.5.4",
      upload_type: "publication" as const,
      publication_type: "preprint" as const,
      description: "Test deposition",
      creators: [{ name: "de Luna e Silva, Pedro Anisio" }],
      prereserve_doi: { doi: "10.5072/zenodo.99001", recid: 99001 },
      access_right: "open" as const,
      license: "cc-by-4.0",
      keywords: ["LLM", "verification"],
    },
    modified: "2026-04-03T00:00:00+00:00",
    owner: 1,
    record_id: 99001,
    state: "inprogress" as const,
    submitted: false,
    title: "PALS's Law — v1.5.4",
  },

  publishedDeposition: {
    conceptrecid: "123456",
    created: "2026-04-03T00:00:00+00:00",
    doi: "10.5072/zenodo.99001",
    doi_url: "https://doi.org/10.5072/zenodo.99001",
    files: [],
    id: 99001,
    links: {
      bucket: "https://sandbox.zenodo.org/api/files/bucket-uuid-1234",
      discard: "https://sandbox.zenodo.org/api/deposit/depositions/99001/actions/discard",
      edit: "https://sandbox.zenodo.org/api/deposit/depositions/99001/actions/edit",
      files: "https://sandbox.zenodo.org/api/deposit/depositions/99001/files",
      html: "https://sandbox.zenodo.org/deposit/99001",
      latest_draft: "https://sandbox.zenodo.org/api/deposit/depositions/99001",
      latest_draft_html: "https://sandbox.zenodo.org/deposit/99001",
      publish: "https://sandbox.zenodo.org/api/deposit/depositions/99001/actions/publish",
      self: "https://sandbox.zenodo.org/api/deposit/depositions/99001",
      record: "https://sandbox.zenodo.org/api/records/99001",
      record_html: "https://sandbox.zenodo.org/records/99001",
    },
    metadata: {
      title: "PALS's Law — v1.5.4",
      upload_type: "publication" as const,
      publication_type: "preprint" as const,
      description: "Test deposition",
      creators: [{ name: "de Luna e Silva, Pedro Anisio" }],
      prereserve_doi: { doi: "10.5072/zenodo.99001", recid: 99001 },
      access_right: "open" as const,
      license: "cc-by-4.0",
    },
    modified: "2026-04-03T00:00:00+00:00",
    owner: 1,
    record_id: 99001,
    state: "done" as const,
    submitted: true,
    title: "PALS's Law — v1.5.4",
  },

  bucketFile: {
    key: "PALS_LAW-v1.5.4.md",
    mimetype: "text/markdown",
    checksum: "md5:abc123def456",
    version_id: "version-uuid-1",
    size: 42_000,
    created: "2026-04-03T00:00:00+00:00",
    updated: "2026-04-03T00:00:00+00:00",
    links: {
      self: "https://sandbox.zenodo.org/api/files/bucket-uuid-1234/PALS_LAW-v1.5.4.md",
      version: "https://sandbox.zenodo.org/api/files/bucket-uuid-1234/PALS_LAW-v1.5.4.md?versionId=version-uuid-1",
      uploads: "https://sandbox.zenodo.org/api/files/bucket-uuid-1234/PALS_LAW-v1.5.4.md?uploads",
    },
    is_head: true,
    delete_marker: false,
  },

  depositionFile: {
    checksum: "abc123def456",
    name: "PALS_LAW-v1.5.4.md",
    id: "file-uuid-1",
    filesize: 42_000,
    links: {
      self: "https://sandbox.zenodo.org/api/deposit/depositions/99001/files/file-uuid-1",
      download: "https://sandbox.zenodo.org/api/deposit/depositions/99001/files/file-uuid-1/download",
    },
  },

  record: {
    conceptrecid: "123456",
    created: "2026-04-03T00:00:00+00:00",
    doi: "10.5072/zenodo.99001",
    doi_url: "https://doi.org/10.5072/zenodo.99001",
    files: [{
      bucket: "bucket-uuid",
      checksum: "md5:abc123",
      key: "PALS_LAW-v1.5.4.md",
      links: { self: "https://sandbox.zenodo.org/api/files/bucket-uuid/PALS_LAW-v1.5.4.md" },
      size: 42_000,
      type: "md",
    }],
    id: 99001,
    links: {
      self: "https://sandbox.zenodo.org/api/records/99001",
      html: "https://sandbox.zenodo.org/records/99001",
      badge: "https://sandbox.zenodo.org/badge/doi/10.5072/zenodo.99001.svg",
      files: "https://sandbox.zenodo.org/api/files/bucket-uuid",
      bucket: "https://sandbox.zenodo.org/api/files/bucket-uuid",
      latest: "https://sandbox.zenodo.org/api/records/99001",
      latest_html: "https://sandbox.zenodo.org/records/99001",
      doi: "https://doi.org/10.5072/zenodo.99001",
    },
    metadata: {
      title: "PALS's Law — v1.5.4",
      upload_type: "publication" as const,
      publication_type: "preprint" as const,
      description: "Test",
      creators: [{ name: "de Luna e Silva, Pedro Anisio" }],
      doi: "10.5072/zenodo.99001",
      publication_date: "2026-04-03",
      resource_type: { type: "publication", subtype: "preprint", title: "Preprint" },
      relations: { version: [{ index: 0, is_last: true }] },
      access_right: "open" as const,
      license: "cc-by-4.0",
    },
    modified: "2026-04-03T00:00:00+00:00",
    owner: 1,
    record_id: 99001,
    revision: 1,
    updated: "2026-04-03T00:00:00+00:00",
  },

  license: {
    id: "cc-by-4.0",
    title: "Creative Commons Attribution 4.0 International",
    url: "https://creativecommons.org/licenses/by/4.0/legalcode",
  },
} as const;
