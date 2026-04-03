// ─────────────────────────────────────────────────────────────
// Zenodo SDK — Type Definitions
// ─────────────────────────────────────────────────────────────

// ── Upload & Publication Types ──────────────────────────────

export type UploadType =
  | "publication"
  | "poster"
  | "presentation"
  | "dataset"
  | "image"
  | "video"
  | "software"
  | "lesson"
  | "physicalobject"
  | "other";

export type PublicationType =
  | "annotationcollection"
  | "book"
  | "section"
  | "conferencepaper"
  | "datamanagementplan"
  | "article"
  | "patent"
  | "preprint"
  | "deliverable"
  | "milestone"
  | "proposal"
  | "report"
  | "softwaredocumentation"
  | "taxonomictreatment"
  | "technicalnote"
  | "thesis"
  | "workingpaper"
  | "other";

export type ImageType =
  | "figure"
  | "plot"
  | "drawing"
  | "diagram"
  | "photo"
  | "other";

export type AccessRight = "open" | "embargoed" | "restricted" | "closed";

export type DepositionState = "inprogress" | "done" | "error";

// ── Relation Types ──────────────────────────────────────────

export type RelationType =
  | "isCitedBy"
  | "cites"
  | "isSupplementTo"
  | "isSupplementedBy"
  | "isContinuedBy"
  | "continues"
  | "isDescribedBy"
  | "describes"
  | "hasMetadata"
  | "isMetadataFor"
  | "isNewVersionOf"
  | "isPreviousVersionOf"
  | "isPartOf"
  | "hasPart"
  | "isReferencedBy"
  | "references"
  | "isDocumentedBy"
  | "documents"
  | "isCompiledBy"
  | "compiles"
  | "isVariantFormOf"
  | "isOriginalFormof"
  | "isIdenticalTo"
  | "isAlternateIdentifier"
  | "isReviewedBy"
  | "reviews"
  | "isDerivedFrom"
  | "isSourceOf"
  | "requires"
  | "isRequiredBy"
  | "isObsoletedBy"
  | "obsoletes";

export type ContributorType =
  | "ContactPerson"
  | "DataCollector"
  | "DataCurator"
  | "DataManager"
  | "Distributor"
  | "Editor"
  | "HostingInstitution"
  | "Producer"
  | "ProjectLeader"
  | "ProjectManager"
  | "ProjectMember"
  | "RegistrationAgency"
  | "RegistrationAuthority"
  | "RelatedPerson"
  | "Researcher"
  | "ResearchGroup"
  | "RightsHolder"
  | "Supervisor"
  | "Sponsor"
  | "WorkPackageLeader"
  | "Other";

// ── Creator / Contributor ───────────────────────────────────

export interface Creator {
  name: string; // "Family name, Given names"
  affiliation?: string;
  orcid?: string;
  gnd?: string;
}

export interface Contributor extends Creator {
  type: ContributorType;
}

// ── Related Identifiers ─────────────────────────────────────

export interface RelatedIdentifier {
  identifier: string;
  relation: RelationType;
  resource_type?: string;
}

// ── Community / Grant ───────────────────────────────────────

export interface Community {
  identifier: string;
}

export interface Grant {
  id: string;
}

// ── DOI Reservation ─────────────────────────────────────────

export interface PrereserveDoi {
  doi: string;
  recid: number;
}

// ── Deposition Metadata ─────────────────────────────────────

export interface DepositionMetadata {
  upload_type: UploadType;
  publication_type?: PublicationType;
  image_type?: ImageType;
  publication_date?: string; // YYYY-MM-DD
  title: string;
  creators: Creator[];
  description: string;
  access_right?: AccessRight;
  license?: string;
  embargo_date?: string;
  access_conditions?: string;
  doi?: string;
  prereserve_doi?: PrereserveDoi | boolean;
  keywords?: string[];
  notes?: string;
  related_identifiers?: RelatedIdentifier[];
  contributors?: Contributor[];
  references?: string[];
  communities?: Community[];
  grants?: Grant[];
  version?: string;
  language?: string;
}

// ── Deposition Metadata (input — partial for updates) ───────

export type DepositionMetadataInput = Partial<DepositionMetadata> &
  Pick<DepositionMetadata, "title" | "upload_type" | "description" | "creators">;

// ── Deposition Links ────────────────────────────────────────

export interface DepositionLinks {
  bucket: string;
  discard: string;
  edit: string;
  files: string;
  html: string;
  latest_draft: string;
  latest_draft_html: string;
  publish: string;
  self: string;
  record?: string;
  record_html?: string;
  badge?: string;
  latest?: string;
  latest_html?: string;
}

// ── Deposition File ─────────────────────────────────────────

export interface DepositionFile {
  checksum: string;
  name: string;
  id: string;
  filesize: number;
  links: {
    self: string;
    download: string;
  };
}

// ── Bucket File (new API response) ──────────────────────────

export interface BucketFile {
  key: string;
  mimetype: string;
  checksum: string;
  version_id: string;
  size: number;
  created: string;
  updated: string;
  links: {
    self: string;
    version: string;
    uploads: string;
  };
  is_head: boolean;
  delete_marker: boolean;
}

// ── Deposition ──────────────────────────────────────────────

export interface Deposition {
  conceptrecid: string;
  created: string;
  doi?: string;
  doi_url?: string;
  files: DepositionFile[];
  id: number;
  links: DepositionLinks;
  metadata: DepositionMetadata & { prereserve_doi?: PrereserveDoi };
  modified: string;
  owner: number;
  record_id?: number;
  record_url?: string;
  state: DepositionState;
  submitted: boolean;
  title: string;
}

// ── Record (published) ──────────────────────────────────────

export interface ZenodoRecord {
  conceptrecid: string;
  created: string;
  doi: string;
  doi_url: string;
  files: Array<{
    bucket: string;
    checksum: string;
    key: string;
    links: { self: string };
    size: number;
    type: string;
  }>;
  id: number;
  links: {
    self: string;
    html: string;
    badge: string;
    files: string;
    bucket: string;
    latest: string;
    latest_html: string;
    doi: string;
  };
  metadata: DepositionMetadata & {
    doi: string;
    publication_date: string;
    resource_type: { type: string; subtype?: string; title: string };
    relations: { version: Array<{ index: number; is_last: boolean }> };
  };
  modified: string;
  owner: number;
  record_id: number;
  revision: number;
  stats?: {
    downloads: number;
    unique_downloads: number;
    views: number;
    unique_views: number;
    version_downloads: number;
    version_unique_downloads: number;
    version_views: number;
    version_unique_views: number;
  };
  updated: string;
}

// ── License ─────────────────────────────────────────────────

export interface License {
  id: string;
  title: string;
  url?: string;
  metadata?: {
    id: string;
    title: string;
    url: string;
    family?: string;
    maintainer?: string;
    domain_content?: boolean;
    domain_data?: boolean;
    domain_software?: boolean;
    od_conformance?: string;
    osd_conformance?: string;
  };
}

// ── Pagination / Search ─────────────────────────────────────

export interface SearchParams {
  q?: string;
  status?: "draft" | "published";
  sort?: "bestmatch" | "mostrecent" | "-mostrecent";
  page?: number;
  size?: number;
  all_versions?: boolean;
}

export interface SearchResult<T> {
  hits: {
    hits: T[];
    total: number;
  };
  aggregations?: Record<string, unknown>;
  links?: {
    self: string;
    next?: string;
    prev?: string;
  };
}

// ── Error ───────────────────────────────────────────────────

export interface ZenodoErrorResponse {
  message: string;
  status: number;
  errors?: Array<{
    field?: string;
    message: string;
  }>;
}

// ── Client Config ───────────────────────────────────────────

export interface ZenodoConfig {
  /** Personal access token (required) */
  token: string;
  /** Base URL — defaults to https://zenodo.org/api */
  baseUrl?: string;
  /** Use sandbox (https://sandbox.zenodo.org/api) — overrides baseUrl */
  sandbox?: boolean;
  /** Request timeout in ms (default: 30_000) */
  timeout?: number;
  /** Custom fetch implementation (for testing / Node 16) */
  fetchImpl?: typeof fetch;
}
