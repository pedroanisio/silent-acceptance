#!/usr/bin/env tsx
// Resume: upload files to existing draft 19401267 and publish

import { Zenodo, ZenodoError } from "../src/index.js";
import { resolve } from "node:path";

const TOKEN = process.env.ZENODO_TOKEN!;
const zen = new Zenodo({ token: TOKEN });
const ROOT = resolve(import.meta.dirname, "../..");
const DRAFT_ID = 19401267;

async function main() {
  // Fetch existing draft
  console.log(`Fetching draft ${DRAFT_ID}...`);
  const dep = await zen.depositions.get(DRAFT_ID);
  console.log(`  State: ${dep.state}`);
  console.log(`  Bucket: ${dep.links.bucket}\n`);

  // Upload files
  console.log("Uploading files...");
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

  // Publish
  console.log("\nPublishing...");
  const published = await zen.depositions.publish(DRAFT_ID);

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
      for (const e of err.errors) {
        console.error(`  ${e.field ?? "-"}: ${e.message}`);
      }
    }
  } else {
    console.error(err);
  }
  process.exit(1);
});
