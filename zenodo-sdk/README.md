# @pals/zenodo-sdk

Modular TypeScript SDK for the [Zenodo REST API](https://developers.zenodo.org/).

## Install

```bash
npm install @pals/zenodo-sdk
```

Requires Node.js ≥ 18 (uses native `fetch`).

## Quick Start

```typescript
import { Zenodo } from "@pals/zenodo-sdk";

const zen = new Zenodo({
  token: process.env.ZENODO_TOKEN!,
  sandbox: true, // use sandbox for testing
});

// 1. Create a deposition draft
const dep = await zen.depositions.create({
  title: "PALS's Law — v1.5.4",
  upload_type: "publication",
  publication_type: "preprint",
  description: "Formal specification of LLM output unreliability as an architectural invariant.",
  creators: [
    { name: "de Luna e Silva, Pedro Anisio", affiliation: "Independent" },
  ],
  keywords: ["LLM", "verification", "hallucination", "software-engineering"],
  license: "cc-by-4.0",
  access_right: "open",
});

console.log(`Draft created: ${dep.id}`);
console.log(`Reserved DOI: ${dep.metadata.prereserve_doi?.doi}`);

// 2. Upload files
await zen.files.uploadFromPath(dep, "./PALS_LAW-v1.5.4.md");
await zen.files.uploadFromPath(dep, "./pals_law_schema.json");
await zen.files.uploadFromPath(dep, "./pals_law_report.json");
await zen.files.uploadFromPath(dep, "./pals_law_certificate.json");

// 3. Publish (⚠ irreversible for files — DOI is minted)
// const published = await zen.depositions.publish(dep.id);
// console.log(`Published: ${published.doi_url}`);
```

## Modules

The SDK is composed of four independent modules, accessible from the main `Zenodo` client:

| Module | Access | Description |
|--------|--------|-------------|
| **Depositions** | `zen.depositions` | Create, update, publish, edit, discard, version, delete |
| **Files** | `zen.files` | Upload (bucket API, up to 50 GB), list, delete |
| **Records** | `zen.records` | Search and retrieve published records |
| **Licenses** | `zen.licenses` | Browse available license identifiers |

Each module can also be instantiated independently with an `HttpClient`:

```typescript
import { HttpClient, Depositions } from "@pals/zenodo-sdk";

const http = new HttpClient({ token: "...", sandbox: true });
const depositions = new Depositions(http);
```

## OAuth Application Setup

If building an app that authenticates other Zenodo users (not just yourself):

1. Go to [Zenodo Applications](https://zenodo.org/account/settings/applications/)
2. Click **New Application**
3. Fill in:
   - **Name:** Your app name
   - **Website URL:** Your app's URL
   - **Redirect URIs:** Your OAuth callback URL(s), one per line. Must be HTTPS (except `localhost`).
   - **Client type:** `Confidential` for server-side apps, `Public` for browser/CLI apps.
4. Required scopes: `deposit:write` and `deposit:actions`

For personal automation (publishing your own papers), use a **Personal Access Token** instead — simpler, no OAuth flow needed. Create one at [Zenodo Tokens](https://zenodo.org/account/settings/applications/tokens/new/).

## Testing

Use the sandbox environment for development:

```typescript
const zen = new Zenodo({
  token: process.env.ZENODO_SANDBOX_TOKEN!,
  sandbox: true,
});
```

The sandbox:
- Requires a **separate** registration at [sandbox.zenodo.org](https://sandbox.zenodo.org)
- Issues test DOIs with prefix `10.5072` (not registered with DataCite)
- Can be cleaned at any time by Zenodo

## Error Handling

```typescript
import { Zenodo, ZenodoError, ZenodoTimeoutError } from "@pals/zenodo-sdk";

try {
  await zen.depositions.publish(id);
} catch (err) {
  if (err instanceof ZenodoError) {
    console.error(`API error [${err.status}]: ${err.message}`);
    console.error("Field errors:", err.errors);
  } else if (err instanceof ZenodoTimeoutError) {
    console.error("Request timed out");
  } else {
    throw err;
  }
}
```

## Versioning a Published Record

```typescript
// Create a new version from an existing published record
const newDraft = await zen.depositions.newVersion(existingId);

// The new draft has a new ID — extract it from the links
const newId = newDraft.id;

// Upload updated files, update metadata, then publish
await zen.depositions.update(newId, { ...updatedMetadata });
await zen.files.uploadFromPath(newDraft, "./updated-file.md");
await zen.depositions.publish(newId);
```

## License

MIT
