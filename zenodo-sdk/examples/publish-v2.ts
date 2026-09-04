#!/usr/bin/env tsx
// ─────────────────────────────────────────────────────────────
// Publish Silent Acceptance v2.0.0 as a new version (v4 record)
// under the existing Zenodo concept DOI 10.5281/zenodo.19401266.
//
// Modes (default is a local dry run that touches no network state):
//   tsx publish-v2.ts                          # dry run: list files + metadata, ping only
//   tsx publish-v2.ts --draft                  # create the new-version draft and upload files
//   tsx publish-v2.ts --publish                # draft + publish (mints the DOI; irreversible)
//   tsx publish-v2.ts --publish --draft-id N   # publish an already-inspected draft as is
//
// Requires ZENODO_TOKEN in the environment (see .env).
// ─────────────────────────────────────────────────────────────

import { Zenodo, ZenodoError } from "../src/index.js";
import { readFile, stat } from "node:fs/promises";
import { resolve } from "node:path";
import type { DepositionMetadataInput } from "../src/types.js";

const ROOT = resolve(import.meta.dirname, "../..");

/** Latest published version of the concept record (v2.1.0, record 22308202). Bump with SPEC_VERSION. */
const LATEST_RECORD_ID = 22308202;
const CONCEPT_DOI = "10.5281/zenodo.19401266";

const SPEC_VERSION = "2.1.0";
const SPEC_NAME = `SILENT_ACCEPTANCE-v${SPEC_VERSION}.md`;
const PDF_NAME = `SILENT_ACCEPTANCE-v${SPEC_VERSION}.pdf`;

const mode = process.argv.includes("--publish")
  ? "publish"
  : process.argv.includes("--draft")
    ? "draft"
    : "dry-run";

/** `--draft-id N`: publish this existing, already-inspected draft without touching its files. */
const draftIdArg = process.argv.indexOf("--draft-id");
const existingDraftId = draftIdArg >= 0 ? Number(process.argv[draftIdArg + 1]) : undefined;
if (draftIdArg >= 0 && (!Number.isInteger(existingDraftId) || mode !== "publish")) {
  console.error("--draft-id requires an integer id and --publish");
  process.exit(2);
}

/** Strip YAML frontmatter (--- ... ---): Zenodo renders it as raw text. */
export function stripFrontmatter(md: string): string {
  const match = md.match(/^---\n[\s\S]*?\n---\n*/);
  if (!match) return md;
  return md.slice(match[0].length);
}

export function buildMetadata(publicationDate: string): DepositionMetadataInput {
  return {
    title: "Silent Acceptance: LLM Output Error as an Architectural Invariant",
    upload_type: "publication",
    publication_type: "preprint",
    publication_date: publicationDate,
    description:
      "<p><em>Silent acceptance</em> is the defect in which a system passes LLM output " +
      "to a downstream consumer with no declared verification boundary. This specification " +
      "names that defect, states the invariant that makes it a defect (LLM output error is " +
      "a statistical invariant of the model class, not an exceptional condition), and " +
      "prescribes the boundary that removes it: the Verification Boundary Principle.</p>" +
      "<p>Version 2.1.0 applies a structured review of v2.0.0: the semantic specification is " +
      "replaced by an acceptability predicate A(y, x, z) over an evaluation context; the " +
      "operative bound is indexed to solver configuration and distribution and given an " +
      "operational threshold τ; the pipeline corollary uses a conditional-hazard " +
      "decomposition instead of an independence product; the unit of analysis is the solver " +
      "configuration (model, harness, context policy, tools, prompts); the boundary " +
      "declaration has ten fields and a per-class table; and Corollary 6 becomes a " +
      "control-domain requirement on the acceptance authority. Versions 1.x were published as " +
      "<em>PALS's Law</em> under this concept DOI; v2.0.0 introduced the current name and " +
      "structure.</p>" +
      "<p>Contents: formal operative and existential claims, a 9-class error taxonomy, the " +
      "pipeline corollary, the Capability-Detection Asymmetry with an experiment protocol, six " +
      "architectural corollaries, copy-paste practitioner artifacts, a code-side linter, and " +
      "15 references, each resolved by the companion audit with the outcome recorded per " +
      "reference in the included report. The provenance section (§11) states what was " +
      "verified and how. Machine-readable schema, report, and certificate JSON are included.</p>",
    creators: [
      {
        name: "de Luna e Silva, Pedro Anisio",
        affiliation: "Independent",
      },
    ],
    keywords: [
      "LLM",
      "large language models",
      "hallucination",
      "verification",
      "verification boundary",
      "software engineering",
      "architectural invariant",
      "error taxonomy",
      "agent harness",
      "Silent Acceptance",
      "PALS's Law",
    ],
    license: "cc-by-4.0",
    access_right: "open",
    notes:
      "Formerly published as PALS's Law (versions 1.x). Machine-readable artifacts " +
      "included: pals_law_schema.json (symbol table), pals_law_report.json (reference " +
      "verification report), pals_law_certificate.json (integrity certificate). " +
      "Document drafted by the author with AI assistance (Claude Fable 5.1 via Claude Code); " +
      "see the Acknowledgments and Provenance section.",
    related_identifiers: [
      { identifier: "https://github.com/pedroanisio/silent-acceptance", relation: "isSupplementedBy" },
      { identifier: "10.1145/3618260.3649777", relation: "references" },
      { identifier: "https://arxiv.org/abs/2401.11817", relation: "references" },
      { identifier: "https://arxiv.org/abs/2608.26218", relation: "references" },
      { identifier: "https://arxiv.org/abs/2609.00069", relation: "references" },
      { identifier: "https://arxiv.org/abs/2607.24300", relation: "references" },
    ],
    version: SPEC_VERSION,
  };
}

async function exists(path: string): Promise<boolean> {
  try {
    await stat(path);
    return true;
  } catch {
    return false;
  }
}

async function main() {
  // Local calendar date, so it matches the date printed in the document itself.
  const publicationDate = new Date().toLocaleDateString("en-CA");
  const metadata = buildMetadata(publicationDate);

  const specRaw = await readFile(resolve(ROOT, SPEC_NAME), "utf-8");
  const specClean = new TextEncoder().encode(stripFrontmatter(specRaw));

  const uploads: Array<{ name: string; path?: string; data?: Uint8Array }> = [
    { name: SPEC_NAME, data: specClean },
    { name: "pals_law_schema.json", path: resolve(ROOT, "output/pals_law_schema.json") },
    { name: "pals_law_report.json", path: resolve(ROOT, "output/pals_law_report.json") },
    { name: "pals_law_certificate.json", path: resolve(ROOT, "output/pals_law_certificate.json") },
  ];
  const pdfPath = resolve(ROOT, "output", PDF_NAME);
  if (await exists(pdfPath)) {
    uploads.splice(1, 0, { name: PDF_NAME, path: pdfPath });
  } else {
    console.warn(`  (no ${PDF_NAME} in output/ — run \`make pdf\` first to include it)`);
  }

  console.log(`Mode: ${mode}`);
  console.log(`Concept DOI: ${CONCEPT_DOI}  (new version of record ${LATEST_RECORD_ID})`);
  console.log(`Title: ${metadata.title}`);
  console.log(`Version: ${metadata.version}  Publication date: ${publicationDate}`);
  console.log("Files:");
  for (const u of uploads) console.log(`  - ${u.name}`);

  const TOKEN = process.env.ZENODO_TOKEN;
  if (!TOKEN) {
    console.error("\nZENODO_TOKEN is required for --draft/--publish (and for the ping in dry run).");
    process.exit(mode === "dry-run" ? 0 : 1);
  }
  const zen = new Zenodo({ token: TOKEN });

  console.log("\nConnecting to Zenodo (PRODUCTION)...");
  const ok = await zen.ping();
  if (!ok) {
    console.error("Failed to connect. Check your token.");
    process.exit(1);
  }
  console.log("Connected.");

  if (mode === "dry-run") {
    console.log("\nDry run complete. Re-run with --draft to create the new version draft.");
    return;
  }

  if (existingDraftId !== undefined) {
    const draft = await zen.depositions.get(existingDraftId);
    if (draft.state !== "unsubmitted" && draft.state !== "inprogress") {
      console.error(`Draft ${existingDraftId} is in state ${draft.state}; nothing to publish.`);
      process.exit(1);
    }
    console.log(`\nPublishing existing draft ${existingDraftId} (${draft.files.length} files)...`);
    const published = await zen.depositions.publish(existingDraftId);
    console.log("\n========================================");
    console.log("  NEW VERSION PUBLISHED");
    console.log("========================================");
    console.log(`  DOI:        ${published.doi}`);
    console.log(`  DOI URL:    ${published.doi_url}`);
    console.log(`  Record URL: ${published.links.record_html}`);
    console.log(`  Concept:    https://doi.org/${CONCEPT_DOI}`);
    console.log("========================================\n");
    return;
  }

  // ── 1. New version draft ─────────────────────────────────
  console.log(`\nCreating new version from record ${LATEST_RECORD_ID}...`);
  const original = await zen.depositions.newVersion(LATEST_RECORD_ID);
  const newId = Number(original.links.latest_draft.split("/").pop());
  const draft = await zen.depositions.get(newId);
  console.log(`  New draft ID: ${newId}  (state: ${draft.state})`);

  // ── 2. Remove files carried over from the previous version ──
  const existingFiles = await zen.files.list(newId);
  for (const f of existingFiles) {
    await zen.files.delete(newId, f.id);
    // The deposition files endpoint reports `filename`; the typed shape says `name`.
    console.log(`  deleted: ${(f as { filename?: string }).filename ?? f.name}`);
  }

  // ── 3. Upload v2.0.0 files ───────────────────────────────
  for (const u of uploads) {
    const result = u.data
      ? await zen.files.upload(draft, u.name, u.data)
      : await zen.files.uploadFromPath(draft, u.path!, u.name);
    console.log(`  uploaded: ${result.key} (${result.size} bytes)`);
  }

  // ── 4. Metadata ──────────────────────────────────────────
  await zen.depositions.update(newId, metadata);
  console.log("  metadata updated");
  console.log(`  Draft URL: ${draft.links.html}`);

  if (mode === "draft") {
    console.log("\nDraft ready. Inspect it on Zenodo, then re-run with --publish (irreversible for files).");
    return;
  }

  // ── 5. Publish ───────────────────────────────────────────
  console.log("\nPublishing (mints the DOI; irreversible for files)...");
  const published = await zen.depositions.publish(newId);
  console.log("\n========================================");
  console.log("  NEW VERSION PUBLISHED");
  console.log("========================================");
  console.log(`  DOI:        ${published.doi}`);
  console.log(`  DOI URL:    ${published.doi_url}`);
  console.log(`  Record URL: ${published.links.record_html}`);
  console.log(`  Concept:    https://doi.org/${CONCEPT_DOI}`);
  console.log("========================================\n");
}

main().catch((err) => {
  if (err instanceof ZenodoError) {
    console.error(`\nZenodo API error [${err.status}]: ${err.message}`);
    if (err.errors) {
      for (const e of err.errors) {
        console.error(`  ${e.field ?? "-"}: ${e.message}`);
      }
    }
  } else {
    console.error(err);
  }
  process.exit(1);
});
