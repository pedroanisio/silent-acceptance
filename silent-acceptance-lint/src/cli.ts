#!/usr/bin/env node
/**
 * silent-acceptance-lint CLI.
 *
 *   node src/cli.ts [paths...] [--format text|json] [--window N] [--ext .ts,.py]
 *                   [--config file.json] [--warn-only] [--help] [--version]
 *
 * Exit code 1 when any error-severity finding is reported (0 with --warn-only).
 */

import { readFileSync } from "node:fs";
import { relative } from "node:path";
import { collectFiles, lintPaths, summarize, type Finding, type LintOptions } from "./lint.ts";
import { DEFAULT_CALL_PATTERNS, type CallPattern } from "./patterns.ts";

const VERSION = "0.1.0";

interface CliArgs {
  paths: string[];
  format: "text" | "json";
  window?: number;
  extensions?: string[];
  config?: string;
  warnOnly: boolean;
  help: boolean;
  version: boolean;
}

interface ConfigFile {
  window?: number;
  extensions?: string[];
  /** Extra or replacement patterns; `replace: true` drops the defaults. */
  patterns?: Array<{ id: string; provider: string; regex: string; flags?: string }>;
  replace?: boolean;
}

export function parseArgs(argv: readonly string[]): CliArgs {
  const args: CliArgs = { paths: [], format: "text", warnOnly: false, help: false, version: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i] ?? "";
    const next = (): string => {
      const v = argv[++i];
      if (v === undefined) throw new Error(`missing value for ${a}`);
      return v;
    };
    if (a === "--format") {
      const v = next();
      if (v !== "text" && v !== "json") throw new Error(`--format must be text or json, got ${v}`);
      args.format = v;
    } else if (a === "--window") {
      const n = Number(next());
      if (!Number.isInteger(n) || n < 0) throw new Error("--window must be a non-negative integer");
      args.window = n;
    } else if (a === "--ext") {
      args.extensions = next().split(",").map((e) => (e.startsWith(".") ? e : `.${e}`));
    } else if (a === "--config") {
      args.config = next();
    } else if (a === "--warn-only") {
      args.warnOnly = true;
    } else if (a === "--help" || a === "-h") {
      args.help = true;
    } else if (a === "--version" || a === "-v") {
      args.version = true;
    } else if (a.startsWith("-")) {
      throw new Error(`unknown option ${a}`);
    } else {
      args.paths.push(a);
    }
  }
  if (args.paths.length === 0) args.paths.push(".");
  return args;
}

export function loadConfig(path: string): Partial<LintOptions> {
  const cfg = JSON.parse(readFileSync(path, "utf8")) as ConfigFile;
  const options: Partial<LintOptions> = {};
  if (cfg.window !== undefined) options.window = cfg.window;
  if (cfg.extensions) options.extensions = cfg.extensions;
  if (cfg.patterns) {
    const extra: CallPattern[] = cfg.patterns.map((p) => ({
      id: p.id,
      provider: p.provider,
      regex: new RegExp(p.regex, p.flags ?? ""),
    }));
    options.patterns = cfg.replace ? extra : [...DEFAULT_CALL_PATTERNS, ...extra];
  }
  return options;
}

const USAGE = `silent-acceptance-lint ${VERSION}
Flags LLM call sites with no declared verification boundary (Silent Acceptance spec §10.5).

Usage: silent-acceptance-lint [paths...] [options]

Options:
  --format text|json   Output format (default: text)
  --window N           Lines above a call site in which a declaration counts (default: 80)
  --ext .ts,.py        File extensions to scan (default: ts/tsx/js/jsx/mjs/cjs/py)
  --config file.json   Extra call-site patterns, window, extensions
  --warn-only          Report findings but always exit 0
  --help, -h           Show this help
  --version, -v        Show version

Rules:
  no-boundary            error    call site with no boundary declaration in scope
  empty-boundary         error    declaration leaves all ERR_ classes unchecked, no MITIGATION
  ignore-without-reason  error    silent-acceptance-ignore without a reason
  missing-solver-configuration   warning  declaration has no SOLVER_CONFIGURATION_ID
  deprecated-model-version       warning  declaration still pins MODEL_VERSION (v2.0.0 field)
  missing-acceptance-authority   warning  declaration names no ACCEPTANCE_AUTHORITY
`;

export function formatText(findings: readonly Finding[], cwd: string): string {
  const lines: string[] = [];
  for (const f of findings) {
    const rel = relative(cwd, f.file) || f.file;
    lines.push(`${rel}:${f.line}:${f.column}  ${f.severity.padEnd(7)} ${f.rule}  ${f.message}`);
    lines.push(`    ${f.callSite}`);
  }
  return lines.join("\n");
}

export function run(argv: readonly string[], cwd: string = process.cwd()): { exitCode: number; output: string } {
  let args: CliArgs;
  try {
    args = parseArgs(argv);
  } catch (err) {
    return { exitCode: 2, output: `error: ${(err as Error).message}\n\n${USAGE}` };
  }
  if (args.help) return { exitCode: 0, output: USAGE };
  if (args.version) return { exitCode: 0, output: VERSION };

  let options: Partial<LintOptions> = {};
  if (args.config) options = loadConfig(args.config);
  if (args.window !== undefined) options.window = args.window;
  if (args.extensions) options.extensions = args.extensions;

  const files = collectFiles(args.paths, options.extensions);
  const findings = lintPaths(args.paths, options);
  const summary = summarize(findings, files.length);

  let output: string;
  if (args.format === "json") {
    output = JSON.stringify({ version: VERSION, summary, findings }, null, 2);
  } else {
    const body = formatText(findings, cwd);
    const tail =
      `${summary.files} file(s) scanned: ${summary.errors} error(s), ${summary.warnings} warning(s)` +
      (summary.errors === 0 && summary.warnings === 0 ? " — no silent acceptance found." : "");
    output = body ? `${body}\n\n${tail}` : tail;
  }
  const exitCode = summary.errors > 0 && !args.warnOnly ? 1 : 0;
  return { exitCode, output };
}

const invokedDirectly = process.argv[1] !== undefined && import.meta.url === new URL(`file://${process.argv[1]}`).href;
if (invokedDirectly) {
  const result = run(process.argv.slice(2));
  process.stdout.write(`${result.output}\n`);
  process.exit(result.exitCode);
}
