import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { collectFiles, lintPaths, lintSource, summarize, type Finding } from "../src/lint.ts";
import { formatText, parseArgs, run } from "../src/cli.ts";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(HERE, "fixtures");
const CLI = resolve(HERE, "../src/cli.ts");

const rules = (findings: readonly Finding[]): string[] => findings.map((f) => f.rule).sort();

test("declared boundary with checked classes produces no findings", () => {
  const findings = lintPaths([join(FIXTURES, "ok-declared.ts")]);
  assert.deepEqual(findings, []);
});

test("undeclared call site is a no-boundary error", () => {
  const findings = lintPaths([join(FIXTURES, "bad-undeclared.ts")]);
  assert.equal(findings.length, 1);
  const f = findings[0]!;
  assert.equal(f.rule, "no-boundary");
  assert.equal(f.severity, "error");
  assert.equal(f.line, 6);
  assert.equal(f.pattern, "openai.chat");
  assert.match(f.callSite, /chat\.completions\.create/);
});

test("all-unchecked checklist with placeholder mitigation is empty-boundary, and placeholder MODEL_VERSION warns", () => {
  const findings = lintPaths([join(FIXTURES, "bad-empty-checklist.ts")]);
  assert.deepEqual(rules(findings), ["empty-boundary", "missing-model-version"]);
  assert.equal(findings.find((f) => f.rule === "empty-boundary")?.severity, "error");
  assert.equal(findings.find((f) => f.rule === "missing-model-version")?.severity, "warning");
});

test("file-level declaration in a Python docstring covers every call in the file", () => {
  const findings = lintPaths([join(FIXTURES, "ok-file-level.py")]);
  assert.deepEqual(findings, []);
});

test("ignore with a reason is honored; ignore without a reason is a finding", () => {
  const findings = lintPaths([join(FIXTURES, "ignored.ts")]);
  assert.deepEqual(rules(findings), ["ignore-without-reason"]);
  assert.equal(findings[0]!.line, 11);
});

test("build output directories are skipped", () => {
  const files = collectFiles([FIXTURES]).map((f) => f.split("/").pop());
  assert.ok(!files.includes("skipped.ts"));
  assert.ok(files.includes("ok-declared.ts"));
});

test("a declaration outside the window does not cover the call", () => {
  const src = [
    "// SILENT_ACCEPTANCE_VERSION: 2.0.0",
    "// MODEL_VERSION: m1",
    ...Array.from({ length: 10 }, () => "const pad = 1;"),
    "const r = await client.messages.create({});",
  ].join("\n");
  assert.deepEqual(rules(lintSource("x.ts", src, { window: 5 })), ["no-boundary"]);
  assert.deepEqual(rules(lintSource("x.ts", src, { window: 20 })), []);
});

test("commented-out call sites are not counted", () => {
  const src = "// const r = await client.messages.create({});\n# ollama.chat(model='x')\n";
  assert.deepEqual(lintSource("x.ts", src), []);
});

test("one finding per line even if several patterns match", () => {
  const src = "const r = await client.messages.create(streamText({}));";
  assert.equal(lintSource("x.ts", src).length, 1);
});

test("legacy PALS_LAW_VERSION marker is still honored", () => {
  const src = "// PALS_LAW_VERSION: 1.5.4\n// MODEL_VERSION: m\nconst r = await client.messages.create({});";
  assert.deepEqual(lintSource("x.ts", src), []);
});

test("provider patterns: bedrock, ollama, google, vercel, mistral, cohere", () => {
  const cases: Array<[string, string]> = [
    ["const c = new ConverseCommand({});", "bedrock.converse"],
    ["const r = await ollama.chat({ model: 'llama' });", "ollama"],
    ["resp = model.generate_content(prompt)", "google.generate"],
    ["const { object } = await generateObject({});", "vercel.ai"],
    ["const r = await mistral.chat.complete({});", "mistral"],
    ["const r = await cohereClient.chat({});", "cohere"],
  ];
  for (const [line, id] of cases) {
    const f = lintSource("x.ts", line);
    assert.equal(f.length, 1, line);
    assert.equal(f[0]!.pattern, id, line);
  }
});

test("summarize counts by severity", () => {
  const findings = lintPaths([FIXTURES]);
  const s = summarize(findings, 5);
  assert.equal(s.files, 5);
  assert.equal(s.errors, 3); // no-boundary, empty-boundary, ignore-without-reason
  assert.equal(s.warnings, 1);
});

test("parseArgs handles options and defaults", () => {
  const a = parseArgs(["src", "--format", "json", "--window", "10", "--ext", "ts,.py", "--warn-only"]);
  assert.deepEqual(a.paths, ["src"]);
  assert.equal(a.format, "json");
  assert.equal(a.window, 10);
  assert.deepEqual(a.extensions, [".ts", ".py"]);
  assert.equal(a.warnOnly, true);
  assert.deepEqual(parseArgs([]).paths, ["."]);
  assert.throws(() => parseArgs(["--format", "xml"]));
  assert.throws(() => parseArgs(["--bogus"]));
});

test("run returns exit 1 on errors, 0 with --warn-only, and valid JSON", () => {
  const r = run([FIXTURES, "--format", "json"], HERE);
  assert.equal(r.exitCode, 1);
  const parsed = JSON.parse(r.output) as { summary: { errors: number }; findings: Finding[] };
  assert.equal(parsed.summary.errors, 3);
  assert.equal(parsed.findings.length, 4);

  const warnOnly = run([FIXTURES, "--warn-only"], HERE);
  assert.equal(warnOnly.exitCode, 0);

  const clean = run([join(FIXTURES, "ok-declared.ts")], HERE);
  assert.equal(clean.exitCode, 0);
  assert.match(clean.output, /no silent acceptance found/);
});

test("formatText renders file:line:col with the rule and call site", () => {
  const findings = lintPaths([join(FIXTURES, "bad-undeclared.ts")]);
  const text = formatText(findings, FIXTURES);
  assert.match(text, /^bad-undeclared\.ts:6:\d+\s+error\s+no-boundary/);
  assert.match(text, /chat\.completions\.create/);
});

test("CLI process exits 1 on findings and prints usage on --help", () => {
  const bad = spawnSync(process.execPath, [CLI, join(FIXTURES, "bad-undeclared.ts")], { encoding: "utf8" });
  assert.equal(bad.status, 1, bad.stderr);
  assert.match(bad.stdout, /no-boundary/);

  const help = spawnSync(process.execPath, [CLI, "--help"], { encoding: "utf8" });
  assert.equal(help.status, 0, help.stderr);
  assert.match(help.stdout, /Usage: silent-acceptance-lint/);
});
