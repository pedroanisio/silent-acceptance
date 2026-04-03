// ─────────────────────────────────────────────────────────────
// Zenodo SDK — Public API
// ─────────────────────────────────────────────────────────────

export { Zenodo } from "./zenodo.js";

// Modules (for advanced composition / testing)
export { Depositions } from "./modules/depositions.js";
export { Files } from "./modules/files.js";
export { Records } from "./modules/records.js";
export { Licenses } from "./modules/licenses.js";

// Client (for escape-hatch usage)
export { HttpClient } from "./client.js";

// Errors
export { ZenodoError, ZenodoNetworkError, ZenodoTimeoutError } from "./errors.js";

// Types
export type {
  // Config
  ZenodoConfig,
  // Entities
  Deposition,
  DepositionMetadata,
  DepositionMetadataInput,
  DepositionLinks,
  DepositionFile,
  BucketFile,
  ZenodoRecord,
  License,
  // Sub-entities
  Creator,
  Contributor,
  RelatedIdentifier,
  Community,
  Grant,
  PrereserveDoi,
  // Search
  SearchParams,
  SearchResult,
  // Enums
  UploadType,
  PublicationType,
  ImageType,
  AccessRight,
  DepositionState,
  RelationType,
  ContributorType,
  // Error
  ZenodoErrorResponse,
} from "./types.js";
