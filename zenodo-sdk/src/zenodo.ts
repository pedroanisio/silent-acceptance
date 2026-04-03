// ─────────────────────────────────────────────────────────────
// Zenodo SDK — Main Client
// ─────────────────────────────────────────────────────────────

import type { ZenodoConfig } from "./types.js";
import { HttpClient } from "./client.js";
import { Depositions } from "./modules/depositions.js";
import { Files } from "./modules/files.js";
import { Records } from "./modules/records.js";
import { Licenses } from "./modules/licenses.js";

export class Zenodo {
  /** Raw HTTP client — for escape-hatch requests. */
  public readonly http: HttpClient;

  /** Create, update, publish, and manage depositions. */
  public readonly depositions: Depositions;

  /** Upload, list, and delete files on depositions. */
  public readonly files: Files;

  /** Search and retrieve published records. */
  public readonly records: Records;

  /** Browse available licenses. */
  public readonly licenses: Licenses;

  constructor(config: ZenodoConfig) {
    this.http = new HttpClient(config);
    this.depositions = new Depositions(this.http);
    this.files = new Files(this.http);
    this.records = new Records(this.http);
    this.licenses = new Licenses(this.http);
  }

  /** Quick check: verify the token works by listing depositions. */
  async ping(): Promise<boolean> {
    try {
      await this.depositions.list({ size: 1 });
      return true;
    } catch {
      return false;
    }
  }

  /** Convenience: is this client pointing at the sandbox? */
  get isSandbox(): boolean {
    return this.http.baseUrl.includes("sandbox.zenodo.org");
  }
}
