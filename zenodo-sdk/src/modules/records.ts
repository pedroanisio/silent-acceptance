// ─────────────────────────────────────────────────────────────
// Zenodo SDK — Records Module
// ─────────────────────────────────────────────────────────────

import type { HttpClient } from "../client.js";
import type { ZenodoRecord, SearchParams, SearchResult } from "../types.js";

export class Records {
  constructor(private readonly http: HttpClient) {}

  /** Search published records. */
  async search(params?: SearchParams): Promise<SearchResult<ZenodoRecord>> {
    return this.http.get<SearchResult<ZenodoRecord>>("/records/", {
      q: params?.q,
      sort: params?.sort,
      page: params?.page,
      size: params?.size,
      all_versions: params?.all_versions,
    });
  }

  /** Retrieve a single published record by ID. */
  async get(id: number): Promise<ZenodoRecord> {
    return this.http.get<ZenodoRecord>(`/records/${id}`);
  }
}
