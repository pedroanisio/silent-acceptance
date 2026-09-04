/**
 * silent-acceptance-lint — core.
 *
 * Mechanizes Corollary 4 of the Silent Acceptance specification (§9.5): a call
 * site whose LLM output flows onward with no declared verification boundary is a
 * blocking defect. This is a *presence* check on the declaration, not a dataflow
 * analysis (spec §10.5): it can tell you that a boundary was declared and that
 * the declaration is not empty; it cannot tell you the declared verifier is
 * adequate.
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { extname, join, resolve } from "node:path";
import {
  BOUNDARY_MARKERS,
  COMMENT_LINE,
  DECLARATION_BLOCK_LINES,
  DEFAULT_CALL_PATTERNS,
  DEFAULT_EXTENSIONS,
  DEFAULT_WINDOW,
  FILE_LEVEL_MARKER,
  FILE_LEVEL_SCAN_LINES,
  IGNORE_MARKER,
  SKIP_DIRS,
  type CallPattern,
} from "./patterns.ts";

export type RuleId =
  | "no-boundary"
  | "empty-boundary"
  | "missing-model-version"
  | "ignore-without-reason";

export type Severity = "error" | "warning";

export const RULE_SEVERITY: Readonly<Record<RuleId, Severity>> = {
  "no-boundary": "error",
  "empty-boundary": "error",
  "ignore-without-reason": "error",
  "missing-model-version": "warning",
};

export interface Finding {
  file: string;
  /** 1-based line of the call site (or of the ignore comment). */
  line: number;
  /** 1-based column of the matched call. */
  column: number;
  rule: RuleId;
  severity: Severity;
  message: string;
  /** The matched pattern id, e.g. `anthropic.messages`. */
  pattern: string;
  /** The source line, trimmed. */
  callSite: string;
}

export interface LintOptions {
  /** Lines above a call site in which a declaration counts as in scope. */
  window: number;
  patterns: readonly CallPattern[];
  extensions: readonly string[];
}

export const DEFAULT_OPTIONS: LintOptions = {
  window: DEFAULT_WINDOW,
  patterns: DEFAULT_CALL_PATTERNS,
  extensions: DEFAULT_EXTENSIONS,
};

interface CallSite {
  index: number; // 0-based line index
  column: number; // 1-based
  pattern: CallPattern;
}

interface Declaration {
  index: number; // 0-based line index of the marker
  block: string[]; // the declaration text following the marker
}

const PLACEHOLDER = /^<.*>$/;
const MODEL_VERSION_RE = /MODEL_VERSION\s*:\s*(.*)$/;
const MITIGATION_RE = /MITIGATION\s*:\s*(.*)$/;
const CHECKLIST_RE = /\[( |x|X)\]\s*ERR_[A-Z_]+/;

function withDefaults(options?: Partial<LintOptions>): LintOptions {
  return { ...DEFAULT_OPTIONS, ...(options ?? {}) };
}

function findCallSites(lines: readonly string[], patterns: readonly CallPattern[]): CallSite[] {
  const sites: CallSite[] = [];
  lines.forEach((line, index) => {
    if (COMMENT_LINE.test(line)) return;
    for (const pattern of patterns) {
      const m = pattern.regex.exec(line);
      if (m) {
        sites.push({ index, column: m.index + 1, pattern });
        return; // one finding per line
      }
    }
  });
  return sites;
}

function isMarker(line: string): boolean {
  return BOUNDARY_MARKERS.some((re) => re.test(line));
}

function declarationAt(lines: readonly string[], markerIndex: number, endExclusive: number): Declaration {
  const stop = Math.min(lines.length, markerIndex + DECLARATION_BLOCK_LINES, endExclusive);
  return { index: markerIndex, block: lines.slice(markerIndex, Math.max(stop, markerIndex + 1)) };
}

function findFileLevelDeclaration(lines: readonly string[]): Declaration | undefined {
  const limit = Math.min(lines.length, FILE_LEVEL_SCAN_LINES);
  for (let i = 0; i < limit; i++) {
    const line = lines[i] ?? "";
    if (isMarker(line) || FILE_LEVEL_MARKER.test(line)) {
      // Require the file-level intent somewhere in the surrounding block.
      const block = lines.slice(i, Math.min(lines.length, i + DECLARATION_BLOCK_LINES));
      if (block.some((l) => FILE_LEVEL_MARKER.test(l)) && block.some(isMarker)) {
        const markerLine = block.findIndex(isMarker);
        return declarationAt(lines, i + markerLine, lines.length);
      }
    }
  }
  return undefined;
}

function findScopedDeclaration(lines: readonly string[], site: CallSite, window: number): Declaration | undefined {
  const start = Math.max(0, site.index - window);
  for (let i = site.index; i >= start; i--) {
    if (isMarker(lines[i] ?? "")) {
      return declarationAt(lines, i, site.index);
    }
  }
  return undefined;
}

function ignoreReason(lines: readonly string[], site: CallSite): { ignored: boolean; reason: string } {
  for (const idx of [site.index, site.index - 1]) {
    const line = lines[idx];
    if (line === undefined) continue;
    const m = IGNORE_MARKER.exec(line);
    if (m) {
      const reason = (m[1] ?? "").replace(/\*\/\s*$/, "").trim();
      return { ignored: true, reason };
    }
  }
  return { ignored: false, reason: "" };
}

function inspectDeclaration(decl: Declaration): { emptyChecklist: boolean; missingModelVersion: boolean } {
  let checklistLines = 0;
  let checked = 0;
  let modelVersion: string | undefined;
  let mitigation: string | undefined;
  for (const raw of decl.block) {
    const line = raw.replace(/\*\/\s*$/, "");
    const cl = CHECKLIST_RE.exec(line);
    if (cl) {
      checklistLines++;
      if (cl[1] !== " ") checked++;
    }
    const mv = MODEL_VERSION_RE.exec(line);
    if (mv && modelVersion === undefined) modelVersion = (mv[1] ?? "").trim();
    const mi = MITIGATION_RE.exec(line);
    if (mi && mitigation === undefined) mitigation = (mi[1] ?? "").trim();
  }
  const usable = (v: string | undefined): boolean =>
    v !== undefined && v.length > 0 && !PLACEHOLDER.test(v);
  const emptyChecklist = checklistLines > 0 && checked === 0 && !usable(mitigation);
  const missingModelVersion = !usable(modelVersion);
  return { emptyChecklist, missingModelVersion };
}

function finding(
  file: string,
  site: CallSite,
  rule: RuleId,
  message: string,
  lines: readonly string[],
): Finding {
  return {
    file,
    line: site.index + 1,
    column: site.column,
    rule,
    severity: RULE_SEVERITY[rule],
    message,
    pattern: site.pattern.id,
    callSite: (lines[site.index] ?? "").trim(),
  };
}

/** Lint one source text. `file` is used for reporting only. */
export function lintSource(file: string, source: string, options?: Partial<LintOptions>): Finding[] {
  const opts = withDefaults(options);
  const lines = source.split(/\r?\n/);
  const findings: Finding[] = [];
  const fileLevel = findFileLevelDeclaration(lines);
  const sites = findCallSites(lines, opts.patterns);

  for (const site of sites) {
    const ignore = ignoreReason(lines, site);
    if (ignore.ignored) {
      if (ignore.reason.length === 0) {
        findings.push(finding(
          file, site, "ignore-without-reason",
          "silent-acceptance-ignore must state a reason (`silent-acceptance-ignore: <why>`).",
          lines,
        ));
      }
      continue;
    }

    const decl = findScopedDeclaration(lines, site, opts.window) ?? fileLevel;
    if (!decl) {
      findings.push(finding(
        file, site, "no-boundary",
        `LLM call (${site.pattern.provider}) with no verification boundary declared within ` +
          `${opts.window} lines or at file level. Add the §10.1 contract block or a ` +
          "`SILENT_ACCEPTANCE_VERSION:` / `@verification-boundary` comment.",
        lines,
      ));
      continue;
    }

    const inspection = inspectDeclaration(decl);
    if (inspection.emptyChecklist) {
      findings.push(finding(
        file, site, "empty-boundary",
        `Boundary declared at line ${decl.index + 1} leaves every error class unchecked and ` +
          "gives no MITIGATION note (spec §10.1: blocking defect).",
        lines,
      ));
    }
    if (inspection.missingModelVersion) {
      findings.push(finding(
        file, site, "missing-model-version",
        `Boundary declared at line ${decl.index + 1} has no MODEL_VERSION pin (spec §9.6: ` +
          "a model swap without boundary review is a regression).",
        lines,
      ));
    }
  }
  return findings;
}

/** Recursively collect lintable files under the given paths. */
export function collectFiles(paths: readonly string[], extensions: readonly string[] = DEFAULT_EXTENSIONS): string[] {
  const out: string[] = [];
  const visit = (p: string): void => {
    const st = statSync(p);
    if (st.isDirectory()) {
      for (const entry of readdirSync(p).sort()) {
        if (SKIP_DIRS.has(entry)) continue;
        visit(join(p, entry));
      }
      return;
    }
    if (extensions.includes(extname(p))) out.push(p);
  };
  for (const p of paths) visit(resolve(p));
  return out;
}

/** Lint every file under the given paths. */
export function lintPaths(paths: readonly string[], options?: Partial<LintOptions>): Finding[] {
  const opts = withDefaults(options);
  const findings: Finding[] = [];
  for (const file of collectFiles(paths, opts.extensions)) {
    const source = readFileSync(file, "utf8");
    findings.push(...lintSource(file, source, opts));
  }
  return findings;
}

export interface Summary {
  files: number;
  errors: number;
  warnings: number;
}

export function summarize(findings: readonly Finding[], files: number): Summary {
  return {
    files,
    errors: findings.filter((f) => f.severity === "error").length,
    warnings: findings.filter((f) => f.severity === "warning").length,
  };
}
