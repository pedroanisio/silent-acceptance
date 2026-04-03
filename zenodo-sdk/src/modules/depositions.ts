// ─────────────────────────────────────────────────────────────
// Zenodo SDK — Depositions Module
// ─────────────────────────────────────────────────────────────

import type { HttpClient } from "../client.js";
import type {
  Deposition,
  DepositionMetadataInput,
  SearchParams,
} from "../types.js";

export class Depositions {
  constructor(private readonly http: HttpClient) {}

  // ── List / Search ─────────────────────────────────────────

  /**
   * List depositions for the authenticated user.
   * Supports search, pagination, and filtering.
   */
  async list(params?: SearchParams): Promise<Deposition[]> {
    return this.http.get<Deposition[]>("/deposit/depositions", {
      q: params?.q,
      status: params?.status,
      sort: params?.sort,
      page: params?.page,
      size: params?.size,
      all_versions: params?.all_versions,
    });
  }

  // ── Get ───────────────────────────────────────────────────

  /** Retrieve a single deposition by ID. */
  async get(id: number): Promise<Deposition> {
    return this.http.get<Deposition>(`/deposit/depositions/${id}`);
  }

  // ── Create ────────────────────────────────────────────────

  /**
   * Create an empty deposition draft.
   * Optionally pass metadata to pre-fill it.
   */
  async create(metadata?: DepositionMetadataInput): Promise<Deposition> {
    const body = metadata ? { metadata } : {};
    return this.http.post<Deposition>("/deposit/depositions", body);
  }

  // ── Update Metadata ───────────────────────────────────────

  /** Replace deposition metadata (full replace, not patch). */
  async update(id: number, metadata: DepositionMetadataInput): Promise<Deposition> {
    return this.http.put<Deposition>(`/deposit/depositions/${id}`, {
      metadata,
    });
  }

  // ── Actions ───────────────────────────────────────────────

  /**
   * Publish a deposition — makes it publicly available and registers the DOI.
   * ⚠ This action is irreversible for the files (metadata can still be edited).
   */
  async publish(id: number): Promise<Deposition> {
    return this.http.post<Deposition>(
      `/deposit/depositions/${id}/actions/publish`
    );
  }

  /** Unlock a published deposition for metadata editing. */
  async edit(id: number): Promise<Deposition> {
    return this.http.post<Deposition>(
      `/deposit/depositions/${id}/actions/edit`
    );
  }

  /** Discard changes on an in-progress deposition. */
  async discard(id: number): Promise<Deposition> {
    return this.http.post<Deposition>(
      `/deposit/depositions/${id}/actions/discard`
    );
  }

  /**
   * Create a new version of a published deposition.
   * Returns the new draft deposition (files are not copied automatically).
   */
  async newVersion(id: number): Promise<Deposition> {
    return this.http.post<Deposition>(
      `/deposit/depositions/${id}/actions/newversion`
    );
  }

  // ── Delete ────────────────────────────────────────────────

  /** Delete an unpublished deposition. Published depositions cannot be deleted. */
  async delete(id: number): Promise<void> {
    return this.http.delete(`/deposit/depositions/${id}`);
  }
}
