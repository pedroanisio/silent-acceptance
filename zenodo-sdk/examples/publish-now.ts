#!/usr/bin/env tsx
// ─────────────────────────────────────────────────────────────
// Publish PALS's Law v1.5.4 to Zenodo (PRODUCTION)
// ─────────────────────────────────────────────────────────────

import { Zenodo, ZenodoError } from "../src/index.js";
import { resolve } from "node:path";

const TOKEN = process.env.ZENODO_TOKEN;
if (!TOKEN) {
  console.error("ZENODO_TOKEN is required.");
  process.exit(1);
}

const zen = new Zenodo({ token: TOKEN }); // production by default

const ROOT = resolve(import.meta.dirname, "../..");

async function main() {
  // ── 1. Verify connection ─────────────────────────────────
  console.log("Connecting to Zenodo (PRODUCTION)...");
  const ok = await zen.ping();
  if (!ok) {
    console.error("Failed to connect. Check your token.");
    process.exit(1);
  }
  console.log("Connected.\n");

  // ── 2. Create deposition draft ───────────────────────────
  console.log("Step 1: Creating deposition draft...");
  const dep = await zen.depositions.create({
    title:
      "PALS's Law: A Formal Specification of LLM Output Unreliability as an Architectural Invariant",
    upload_type: "publication",
    publication_type: "preprint",
    publication_date: "2026-04-03",
    description:
      "<p>PALS's Law is an engineering principle asserting that LLM output error " +
      "is not an exceptional condition but a statistical invariant of the model class, " +
      "and that any system failing to treat it as such contains an architectural defect — " +
      "regardless of how correct the output appears at inspection time.</p>" +
      "<p>The document provides: a formal operative claim (non-negligible expected error " +
      "rate across realistic distributions), a 9-class error taxonomy, a pipeline compounding " +
      "corollary, 5 architectural corollaries, and copy-paste practitioner artifacts " +
      "(contract blocks, inline banners, CLAUDE.md integration).</p>" +
      "<p>Version 1.5.4 — includes reference verification pass, 12 cited references " +
      "(8 empirical, 4 theoretical), and machine-readable schema/report/certificate JSON.</p>",
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
      "software engineering",
      "architectural invariant",
      "error taxonomy",
      "PALS's Law",
    ],
    license: "cc-by-4.0",
    access_right: "open",
    notes:
      "Machine-readable artifacts included: pals_law_schema.json (symbol table), " +
      "pals_law_report.json (reference verification report), " +
      "pals_law_certificate.json (integrity certificate). " +
      "Document generated with assistance from Claude (Anthropic).",
    related_identifiers: [
      {
        identifier: "10.1145/3618260.3649777",
        relation: "references",
      },
      {
        identifier: "https://arxiv.org/abs/2401.11817",
        relation: "references",
      },
    ],
    version: "1.5.4",
  });

  const doi = dep.metadata.prereserve_doi?.doi ?? "(not reserved)";
  console.log(`  Draft ID:      ${dep.id}`);
  console.log(`  Reserved DOI:  ${doi}`);
  console.log(`  Edit URL:      ${dep.links.html}\n`);

  // ── 3. Upload files ──────────────────────────────────────
  console.log("Step 2: Uploading files...");

  const filesToUpload = [
    { path: resolve(ROOT, "PALS_LAW-v1.5.4.md"), name: "PALS_LAW-v1.5.4.md" },
    { path: resolve(ROOT, "output/pals_law_schema.json"), name: "pals_law_schema.json" },
    { path: resolve(ROOT, "output/pals_law_report.json"), name: "pals_law_report.json" },
    { path: resolve(ROOT, "output/pals_law_certificate.json"), name: "pals_law_certificate.json" },
  ];

  for (const file of filesToUpload) {
    const result = await zen.files.uploadFromPath(dep, file.path, file.name);
    console.log(`  uploaded: ${result.key} (${result.size} bytes, ${result.checksum})`);
  }

  // ── 4. Publish ───────────────────────────────────────────
  console.log("\nStep 3: Publishing (this mints the DOI and is irreversible for files)...");
  const published = await zen.depositions.publish(dep.id);

  console.log("\n========================================");
  console.log("  PUBLISHED SUCCESSFULLY");
  console.log("========================================");
  console.log(`  DOI:        ${published.doi}`);
  console.log(`  DOI URL:    ${published.doi_url}`);
  console.log(`  Record URL: ${published.links.record_html}`);
  console.log(`  Record ID:  ${published.record_id}`);
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
