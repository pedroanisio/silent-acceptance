#!/usr/bin/env tsx
// ─────────────────────────────────────────────────────────────
// Fix: Create new version with frontmatter stripped from the
// Markdown file (Zenodo renders YAML frontmatter as raw text).
// ─────────────────────────────────────────────────────────────

import { Zenodo, ZenodoError } from "../src/index.js";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const TOKEN = process.env.ZENODO_TOKEN!;
const zen = new Zenodo({ token: TOKEN });
const ROOT = resolve(import.meta.dirname, "../..");
const PUBLISHED_ID = 19401267;

/** Strip YAML frontmatter (--- ... ---) from Markdown content. */
function stripFrontmatter(md: string): string {
  const match = md.match(/^---\n[\s\S]*?\n---\n*/);
  if (!match) return md;
  return md.slice(match[0].length);
}

async function main() {
  // ── 1. Create new version ────────────────────────────────
  console.log(`Creating new version from record ${PUBLISHED_ID}...`);
  const original = await zen.depositions.newVersion(PUBLISHED_ID);

  // Extract new draft ID from latest_draft link
  const latestDraftUrl = original.links.latest_draft;
  const newId = Number(latestDraftUrl.split("/").pop());
  console.log(`  New draft ID: ${newId}`);

  const draft = await zen.depositions.get(newId);
  console.log(`  State: ${draft.state}`);

  // ── 2. Delete old files from the new draft ───────────────
  console.log("\nRemoving old files from draft...");
  const existingFiles = await zen.files.list(newId);
  for (const f of existingFiles) {
    await zen.files.delete(newId, f.id);
    console.log(`  deleted: ${f.name}`);
  }

  // ── 3. Upload cleaned spec (no frontmatter) ──────────────
  console.log("\nUploading cleaned files...");

  // Spec: strip frontmatter
  const specRaw = await readFile(resolve(ROOT, "PALS_LAW-v1.5.4.md"), "utf-8");
  const specClean = stripFrontmatter(specRaw);
  const specBuffer = new TextEncoder().encode(specClean);
  const r1 = await zen.files.upload(draft, "PALS_LAW-v1.5.4.md", specBuffer);
  console.log(`  uploaded: ${r1.key} (${r1.size} bytes)`);

  // JSON artifacts: upload as-is
  const jsonFiles = [
    "output/pals_law_schema.json",
    "output/pals_law_report.json",
    "output/pals_law_certificate.json",
  ];
  for (const rel of jsonFiles) {
    const name = rel.split("/").pop()!;
    const result = await zen.files.uploadFromPath(draft, resolve(ROOT, rel), name);
    console.log(`  uploaded: ${result.key} (${result.size} bytes)`);
  }

  // ── 4. Fix metadata (publication_date required for new versions) ──
  console.log("\nUpdating metadata...");
  await zen.depositions.update(newId, {
    ...draft.metadata,
    publication_date: "2026-04-03",
  });

  // ── 5. Publish ───────────────────────────────────────────
  console.log("Publishing new version...");
  const published = await zen.depositions.publish(newId);

  console.log("\n========================================");
  console.log("  NEW VERSION PUBLISHED");
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
      for (const e of err.errors) {
        console.error(`  ${e.field ?? "-"}: ${e.message}`);
      }
    }
  } else {
    console.error(err);
  }
  process.exit(1);
});
