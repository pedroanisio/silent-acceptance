// ─────────────────────────────────────────────────────────────
// Zenodo SDK — Licenses Module
// ─────────────────────────────────────────────────────────────

import type { HttpClient } from "../client.js";
import type { License } from "../types.js";

export class Licenses {
  constructor(private readonly http: HttpClient) {}

  /** Search available licenses. */
  async search(query?: string): Promise<License[]> {
    const result = await this.http.get<{ hits: { hits: License[] } }>(
      "/licenses/",
      { q: query }
    );
    return result.hits.hits;
  }

  /** Retrieve a single license by ID (e.g., "cc-by-4.0"). */
  async get(id: string): Promise<License> {
    return this.http.get<License>(`/licenses/${encodeURIComponent(id)}`);
  }
}
