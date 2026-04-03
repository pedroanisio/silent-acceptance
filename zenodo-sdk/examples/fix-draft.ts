#!/usr/bin/env tsx
import { Zenodo, ZenodoError } from "../src/index.js";

const zen = new Zenodo({ token: process.env.ZENODO_TOKEN! });
const DRAFT_ID = 19401346;

async function main() {
  const draft = await zen.depositions.get(DRAFT_ID);
  console.log("State:", draft.state);

  const files = await zen.files.list(DRAFT_ID);
  console.log("Files:", files.map((f) => f.name));

  // Update metadata with publication_date
  await zen.depositions.update(DRAFT_ID, {
    ...draft.metadata,
    publication_date: "2026-04-03",
  });
  console.log("Metadata updated.");

  // Publish
  const published = await zen.depositions.publish(DRAFT_ID);
  console.log("\n========================================");
  console.log("  NEW VERSION PUBLISHED");
  console.log("========================================");
  console.log(`  DOI:        ${published.doi}`);
  console.log(`  DOI URL:    ${published.doi_url}`);
  console.log(`  Record URL: ${published.links.record_html}`);
  console.log("========================================");
}

main().catch((err) => {
  if (err instanceof ZenodoError) {
    console.error(`Zenodo API error [${err.status}]: ${err.message}`);
  } else {
    console.error(err);
  }
  process.exit(1);
});
