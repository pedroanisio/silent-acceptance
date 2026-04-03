#!/usr/bin/env tsx
// ─────────────────────────────────────────────────────────────
// Publish new version with PDF to Zenodo (PRODUCTION)
// ─────────────────────────────────────────────────────────────

import { Zenodo, ZenodoError } from "../src/index.js";
import { resolve } from "node:path";

const TOKEN = process.env.ZENODO_TOKEN!;
const zen = new Zenodo({ token: TOKEN });
const ROOT = resolve(import.meta.dirname, "../..");
const PUBLISHED_ID = 19401346; // current latest version

async function main() {
  // ── 1. Create new version ────────────────────────────────
  console.log(`Creating new version from record ${PUBLISHED_ID}...`);
  const original = await zen.depositions.newVersion(PUBLISHED_ID);
  const newId = Number(original.links.latest_draft.split("/").pop());
  console.log(`  New draft ID: ${newId}`);

  const draft = await zen.depositions.get(newId);
  console.log(`  State: ${draft.state}`);

  // ── 2. Remove old files ──────────────────────────────────
  console.log("\nRemoving old files...");
  const existingFiles = await zen.files.list(newId);
  for (const f of existingFiles) {
    await zen.files.delete(newId, f.id);
    console.log(`  deleted: ${f.name}`);
  }

  // ── 3. Upload new files (PDF + LaTeX source + JSON artifacts)
  console.log("\nUploading files...");

  const files = [
    { path: resolve(ROOT, "output/PALS_LAW-v1.5.4.pdf"), name: "PALS_LAW-v1.5.4.pdf" },
    { path: resolve(ROOT, "output/PALS_LAW-v1.5.4.tex"), name: "PALS_LAW-v1.5.4.tex" },
    { path: resolve(ROOT, "output/pals_law_schema.json"), name: "pals_law_schema.json" },
    { path: resolve(ROOT, "output/pals_law_report.json"), name: "pals_law_report.json" },
    { path: resolve(ROOT, "output/pals_law_certificate.json"), name: "pals_law_certificate.json" },
  ];

  for (const file of files) {
    const result = await zen.files.uploadFromPath(draft, file.path, file.name);
    console.log(`  uploaded: ${result.key} (${result.size} bytes)`);
  }

  // ── 4. Update metadata ───────────────────────────────────
  console.log("\nUpdating metadata...");
  await zen.depositions.update(newId, {
    ...draft.metadata,
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
      "(8 empirical, 4 theoretical), and machine-readable schema/report/certificate JSON.</p>" +
      "<p><strong>This version:</strong> Full LaTeX/PDF typeset with proper tables, " +
      "equations, and table of contents. Includes .tex source for reproducibility.</p>",
  });

  // ── 5. Publish ───────────────────────────────────────────
  console.log("Publishing...");
  const published = await zen.depositions.publish(newId);

  console.log("\n========================================");
  console.log("  PUBLISHED SUCCESSFULLY");
  console.log("========================================");
  console.log(`  DOI:        ${published.doi}`);
  console.log(`  DOI URL:    ${published.doi_url}`);
  console.log(`  Record URL: ${published.links.record_html}`);
  console.log("========================================\n");
}

main().catch((err) => {
  if (err instanceof ZenodoError) {
    console.error(`\nZenodo API error [${err.status}]: ${err.message}`);
    if (err.errors) {
      for (const e of err.errors) console.error(`  ${e.field ?? "-"}: ${e.message}`);
    }
  } else {
    console.error(err);
  }
  process.exit(1);
});
