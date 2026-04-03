// ─────────────────────────────────────────────────────────────
// Zenodo SDK — Files Module
// ─────────────────────────────────────────────────────────────

import type { HttpClient } from "../client.js";
import type { BucketFile, Deposition, DepositionFile } from "../types.js";
import { readFile } from "node:fs/promises";
import { basename } from "node:path";

export class Files {
  constructor(private readonly http: HttpClient) {}

  // ── List ──────────────────────────────────────────────────

  /** List all files attached to a deposition. */
  async list(depositionId: number): Promise<DepositionFile[]> {
    return this.http.get<DepositionFile[]>(
      `/deposit/depositions/${depositionId}/files`
    );
  }

  // ── Upload (new bucket API — supports up to 50 GB) ────────

  /**
   * Upload a file to a deposition's bucket using the new API.
   *
   * @param deposition - The deposition object (needs `links.bucket`).
   * @param filename   - The filename to use on Zenodo.
   * @param data       - File content as Buffer, Uint8Array, or ReadableStream.
   * @param contentType - MIME type (auto-detected from filename if omitted).
   */
  async upload(
    deposition: Pick<Deposition, "links">,
    filename: string,
    data: Uint8Array | ReadableStream<Uint8Array>,
    contentType?: string
  ): Promise<BucketFile> {
    const mime = contentType ?? "application/octet-stream";
    const url = `${deposition.links.bucket}/${encodeURIComponent(filename)}`;
    return this.http.putBinary<BucketFile>(url, data as BodyInit, mime);
  }

  /**
   * Upload a file from the local filesystem.
   *
   * @param deposition - The deposition object (needs `links.bucket`).
   * @param filePath   - Absolute or relative path to the local file.
   * @param filename   - Override the filename on Zenodo (defaults to basename).
   */
  async uploadFromPath(
    deposition: Pick<Deposition, "links">,
    filePath: string,
    filename?: string
  ): Promise<BucketFile> {
    const name = filename ?? basename(filePath);
    const data = await readFile(filePath);
    return this.upload(deposition, name, data);
  }

  // ── Upload (old API — 100 MB limit, simpler) ──────────────

  /**
   * Upload via the legacy deposition files endpoint.
   * Simpler but limited to 100 MB per file.
   */
  async uploadLegacy(
    depositionId: number,
    filename: string,
    data: Uint8Array
  ): Promise<DepositionFile> {
    // The legacy endpoint expects multipart/form-data
    const form = new FormData();
    form.append("name", filename);
    // Copy to a clean ArrayBuffer to satisfy the BlobPart type constraint
    // (Node's Buffer.buffer may be SharedArrayBuffer, which Blob rejects at the type level)
    const ab = data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength) as ArrayBuffer;
    form.append("file", new Blob([ab]), filename);

    return this.http.request<DepositionFile>(
      "POST",
      `/deposit/depositions/${depositionId}/files`,
      { rawBody: form }
    );
  }

  // ── Sort ──────────────────────────────────────────────────

  /**
   * Update the file ordering of a deposition.
   * Pass an array of objects with `{ id: fileId }` in the desired order.
   */
  async sort(
    depositionId: number,
    order: Array<{ id: string }>
  ): Promise<DepositionFile[]> {
    return this.http.put<DepositionFile[]>(
      `/deposit/depositions/${depositionId}/files`,
      order
    );
  }

  // ── Get ───────────────────────────────────────────────────

  /** Retrieve metadata for a single file. */
  async get(depositionId: number, fileId: string): Promise<DepositionFile> {
    return this.http.get<DepositionFile>(
      `/deposit/depositions/${depositionId}/files/${fileId}`
    );
  }

  // ── Delete ────────────────────────────────────────────────

  /** Delete a file from an unpublished deposition. */
  async delete(depositionId: number, fileId: string): Promise<void> {
    return this.http.delete(
      `/deposit/depositions/${depositionId}/files/${fileId}`
    );
  }
}
