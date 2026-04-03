#!/usr/bin/env tsx
// ─────────────────────────────────────────────────────────────
// Example: Publish PALS's Law v1.5.4 to Zenodo
// ─────────────────────────────────────────────────────────────
//
// Usage:
//   ZENODO_TOKEN=<your-token> npx tsx examples/publish-pals-law.ts
//
// Set ZENODO_SANDBOX=1 to use the sandbox environment.
// ─────────────────────────────────────────────────────────────

import { Zenodo, ZenodoError } from "../src/index.js";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const SANDBOX = process.env.ZENODO_SANDBOX === "1";
const TOKEN = process.env.ZENODO_TOKEN;

if (!TOKEN) {
  console.error("Error: ZENODO_TOKEN environment variable is required.");
  console.error(
    SANDBOX
      ? "Create one at: https://sandbox.zenodo.org/account/settings/applications/tokens/new/"
      : "Create one at: https://zenodo.org/account/settings/applications/tokens/new/"
  );
  console.error("Required scopes: deposit:write, deposit:actions");
  process.exit(1);
}

const zen = new Zenodo({ token: TOKEN, sandbox: SANDBOX });

async function main() {
  // ── Verify connection ───────────────────────────────────
  const ok = await zen.ping();
  if (!ok) {
    console.error("Failed to connect. Check your token and network.");
    process.exit(1);
  }
  console.log(`Connected to ${zen.isSandbox ? "SANDBOX" : "PRODUCTION"}`);

  // ── Create deposition ─────────────────────────────────
  console.log("\n1. Creating deposition draft...");
  const dep = await zen.depositions.create({
    title: "PALS's Law: A Formal Specification of LLM Output Unreliability as an Architectural Invariant",
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
        // orcid: "0000-0000-0000-0000", // ← fill in your ORCID
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
      // Link to the theoretical foundations cited in the spec
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
  console.log(`   Draft ID:      ${dep.id}`);
  console.log(`   Reserved DOI:  ${doi}`);
  console.log(`   Edit URL:      ${dep.links.html}`);

  // ── Upload files ──────────────────────────────────────
  console.log("\n2. Uploading files...");

  const artifactDir = resolve(process.cwd());
  const filesToUpload = [
    "PALS_LAW-v1.5.4.md",
    "pals_law_schema.json",
    "pals_law_report.json",
    "pals_law_certificate.json",
  ];

  for (const filename of filesToUpload) {
    const path = resolve(artifactDir, filename);
    try {
      const result = await zen.files.uploadFromPath(dep, path, filename);
      console.log(`   ✓ ${result.key} (${result.size} bytes, ${result.checksum})`);
    } catch (err) {
      if (err instanceof ZenodoError) {
        console.error(`   ✗ ${filename}: ${err.message}`);
      } else {
        throw err;
      }
    }
  }

  // ── Summary ───────────────────────────────────────────
  console.log("\n3. Summary");
  console.log(`   Deposition ID: ${dep.id}`);
  console.log(`   Reserved DOI:  ${doi}`);
  console.log(`   Status:        ${dep.state} (unpublished)`);
  console.log(`   Edit URL:      ${dep.links.html}`);

  console.log("\n── Next steps ─────────────────────────────────");
  console.log("   • Review the draft at the Edit URL above");
  console.log("   • When ready, publish with:");
  console.log(`     await zen.depositions.publish(${dep.id})`);
  console.log("   • Or publish from the Zenodo web UI");
  console.log("   ⚠  Publishing registers the DOI and is irreversible for files.");
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
