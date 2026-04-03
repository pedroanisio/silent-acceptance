import { describe, it, expect } from "vitest";
import { readFile, stat } from "node:fs/promises";
import { resolve } from "node:path";
import { Zenodo } from "../zenodo.js";
import type { Deposition, BucketFile } from "../types.js";
import { createMockFetch, mockResponse, testConfig, FIXTURES } from "./helpers.js";

/**
 * End-to-end workflow test: create → upload files → publish.
 * Uses the real PALS_LAW-v1.5.4.md and the JSON output artifacts as fixtures.
 */

const ROOT = resolve(import.meta.dirname, "../../..");
const ARTIFACTS = {
  spec: resolve(ROOT, "PALS_LAW-v1.5.4.md"),
  schema: resolve(ROOT, "output/pals_law_schema.json"),
  report: resolve(ROOT, "output/pals_law_report.json"),
  certificate: resolve(ROOT, "output/pals_law_certificate.json"),
};

describe("Full publication workflow", () => {
  it("creates deposition, uploads PALS_LAW-v1.5.4.md + artifacts, and publishes", async () => {
    // ── Verify all source files exist ──────────────────────
    const specStat = await stat(ARTIFACTS.spec);
    expect(specStat.isFile()).toBe(true);
    const specContent = await readFile(ARTIFACTS.spec);
    expect(specContent.byteLength).toBeGreaterThan(10_000); // spec is substantial

    // ── Mock responses for the full workflow ────────────────
    // 1. ping (list depositions)
    // 2. create deposition
    // 3-6. upload 4 files
    // 7. publish

    const uploadResponses = Object.entries(ARTIFACTS).map(([key, path]) => {
      const filename = path.split("/").pop()!;
      return mockResponse({
        ...FIXTURES.bucketFile,
        key: filename,
        mimetype: filename.endsWith(".json") ? "application/json" : "text/markdown",
      } satisfies BucketFile);
    });

    const mock = createMockFetch(
      // 1. ping
      mockResponse([]),
      // 2. create
      mockResponse(FIXTURES.deposition),
      // 3-6. file uploads
      ...uploadResponses,
      // 7. publish
      mockResponse(FIXTURES.publishedDeposition),
    );

    const zen = new Zenodo(testConfig(mock.fetch));

    // ── Step 1: Ping ───────────────────────────────────────
    const connected = await zen.ping();
    expect(connected).toBe(true);

    // ── Step 2: Create deposition ──────────────────────────
    const dep = await zen.depositions.create({
      title: "PALS's Law: A Formal Specification of LLM Output Unreliability as an Architectural Invariant",
      upload_type: "publication",
      publication_type: "preprint",
      publication_date: "2026-04-03",
      description: "<p>PALS's Law v1.5.4</p>",
      creators: [
        { name: "de Luna e Silva, Pedro Anisio", affiliation: "Independent" },
      ],
      keywords: ["LLM", "hallucination", "verification", "PALS's Law"],
      license: "cc-by-4.0",
      access_right: "open",
      version: "1.5.4",
    });

    expect(dep.id).toBe(99001);
    expect(dep.state).toBe("inprogress");
    expect(dep.metadata.prereserve_doi?.doi).toBe("10.5072/zenodo.99001");

    // Verify create request body
    const createBody = JSON.parse(mock.calls[1].init.body as string);
    expect(createBody.metadata.title).toContain("PALS's Law");
    expect(createBody.metadata.version).toBe("1.5.4");

    // ── Step 3: Upload all files ───────────────────────────
    const uploaded: BucketFile[] = [];
    for (const [, filePath] of Object.entries(ARTIFACTS)) {
      const result = await zen.files.uploadFromPath(dep, filePath);
      uploaded.push(result);
    }

    expect(uploaded).toHaveLength(4);
    // Verify each upload went to the bucket URL
    for (let i = 0; i < 4; i++) {
      const callIndex = 2 + i; // offset by ping + create
      expect(mock.calls[callIndex].url).toContain("bucket-uuid-1234");
      expect(mock.calls[callIndex].init.method).toBe("PUT");
    }

    // Verify the spec file was uploaded with correct filename
    expect(mock.calls[2].url).toContain("PALS_LAW-v1.5.4.md");
    // Verify JSON artifacts
    expect(mock.calls[3].url).toContain("pals_law_schema.json");
    expect(mock.calls[4].url).toContain("pals_law_report.json");
    expect(mock.calls[5].url).toContain("pals_law_certificate.json");

    // ── Step 4: Publish ────────────────────────────────────
    const published = await zen.depositions.publish(dep.id);

    expect(published.state).toBe("done");
    expect(published.submitted).toBe(true);
    expect(published.doi).toBe("10.5072/zenodo.99001");
    expect(published.doi_url).toBe("https://doi.org/10.5072/zenodo.99001");

    // Verify publish hit the correct endpoint
    expect(mock.calls[6].url).toContain("/deposit/depositions/99001/actions/publish");

    // ── Total requests: 7 (ping + create + 4 uploads + publish)
    expect(mock.calls).toHaveLength(7);
  });

  it("creates deposition and uploads real spec without publishing (dry run)", async () => {
    const mock = createMockFetch(
      mockResponse(FIXTURES.deposition),
      mockResponse({
        ...FIXTURES.bucketFile,
        key: "PALS_LAW-v1.5.4.md",
      }),
    );

    const zen = new Zenodo(testConfig(mock.fetch));

    // Create draft
    const dep = await zen.depositions.create({
      title: "PALS's Law — v1.5.4 (dry run)",
      upload_type: "publication",
      publication_type: "preprint",
      description: "Dry run — will not be published.",
      creators: [{ name: "de Luna e Silva, Pedro Anisio" }],
    });
    expect(dep.state).toBe("inprogress");

    // Upload only the spec
    const result = await zen.files.uploadFromPath(dep, ARTIFACTS.spec);
    expect(result.key).toBe("PALS_LAW-v1.5.4.md");

    // Verify the uploaded content is the real file
    const realContent = await readFile(ARTIFACTS.spec);
    const sentBody = mock.calls[1].init.body as Uint8Array;
    expect(sentBody.byteLength).toBe(realContent.byteLength);

    // No publish call — only 2 requests
    expect(mock.calls).toHaveLength(2);
  });

  it("handles versioning workflow: newVersion → upload updated file → publish", async () => {
    const newDraft: Deposition = {
      ...FIXTURES.deposition,
      id: 99002,
      links: {
        ...FIXTURES.deposition.links,
        bucket: "https://sandbox.zenodo.org/api/files/bucket-uuid-5678",
        self: "https://sandbox.zenodo.org/api/deposit/depositions/99002",
        publish: "https://sandbox.zenodo.org/api/deposit/depositions/99002/actions/publish",
      },
    };

    const mock = createMockFetch(
      // 1. newVersion returns original record with latest_draft link
      mockResponse({
        ...FIXTURES.publishedDeposition,
        links: {
          ...FIXTURES.publishedDeposition.links,
          latest_draft: "https://sandbox.zenodo.org/api/deposit/depositions/99002",
        },
      }),
      // 2. fetch the new draft
      mockResponse(newDraft),
      // 3. upload file to new draft
      mockResponse({ ...FIXTURES.bucketFile, key: "PALS_LAW-v1.5.4.md" }),
      // 4. publish new version
      mockResponse({
        ...FIXTURES.publishedDeposition,
        id: 99002,
        doi: "10.5072/zenodo.99002",
      }),
    );

    const zen = new Zenodo(testConfig(mock.fetch));

    // Step 1: Create new version
    const original = await zen.depositions.newVersion(99001);
    expect(mock.calls[0].url).toContain("/actions/newversion");

    // Step 2: Fetch the actual new draft (from latest_draft link)
    const draft = await zen.depositions.get(99002);
    expect(draft.id).toBe(99002);

    // Step 3: Upload updated spec
    const uploaded = await zen.files.uploadFromPath(draft, ARTIFACTS.spec);
    expect(mock.calls[2].url).toContain("bucket-uuid-5678");

    // Step 4: Publish
    const pub = await zen.depositions.publish(draft.id);
    expect(pub.doi).toBe("10.5072/zenodo.99002");

    expect(mock.calls).toHaveLength(4);
  });
});

describe("Workflow: metadata validation", () => {
  it("verifies PALS_LAW-v1.5.4.md content is parseable and non-empty", async () => {
    const content = await readFile(ARTIFACTS.spec, "utf-8");

    // The spec must contain the title
    expect(content).toContain("PALS's LAW");
    // Must contain frontmatter
    expect(content).toMatch(/^---\n/);
    // Must contain the version
    expect(content).toContain("1.5.4");
    // Must have substantial content (not just a stub)
    expect(content.length).toBeGreaterThan(10_000);
    // Must contain formal sections
    expect(content).toContain("## 1. Preamble");
  });

  it("verifies output JSON artifacts are valid JSON", async () => {
    for (const key of ["schema", "report", "certificate"] as const) {
      const path = ARTIFACTS[key];
      try {
        const raw = await readFile(path, "utf-8");
        const parsed = JSON.parse(raw);
        expect(parsed).toBeDefined();
        expect(typeof parsed).toBe("object");
      } catch (err) {
        if ((err as NodeJS.ErrnoException).code === "ENOENT") {
          // File may not exist in CI — skip gracefully
          console.warn(`Skipping ${key}: file not found at ${path}`);
        } else {
          throw err;
        }
      }
    }
  });
});
