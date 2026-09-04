---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Pedro Anisio de Luna e Silva with Claude Fable 5.1 via Claude Code"
  date: "2026-09-03"
---

# silent-acceptance-lint

Flags LLM call sites that pass model output onward with no declared verification
boundary. It mechanizes Corollary 4 of the
[Silent Acceptance specification](../SILENT_ACCEPTANCE-v2.0.0.md) (§9.5) as the CI
check described in §10.5. Back to the repository [README](../README.md).

## Disclaimer

This work is subject to the methodological caveats and commitments described in [@DISCLAIMER.md](../DISCLAIMER.md).
> No statement or premise not backed by a real logical definition or verifiable reference should be taken for granted.

## What it checks

The tool is a *presence* check on the boundary declaration, not a dataflow analysis.
It can tell you that a boundary was declared for a call site and that the declaration
is not empty. It cannot tell you that the declared verifier is adequate; that is the
reviewer's job and the recall measurement in spec §7.3.

| Rule | Severity | Fires when |
|---|---|---|
| `no-boundary` | error | an LLM call site has no boundary declaration within the scope window (default 80 lines above) or at file level |
| `empty-boundary` | error | the declaration's `[ ] ERR_*` checklist is entirely unchecked and there is no usable `MITIGATION:` note |
| `ignore-without-reason` | error | `silent-acceptance-ignore` appears without a reason |
| `missing-model-version` | warning | the declaration has no `MODEL_VERSION:` pin, or the pin is still the `<placeholder>` |

A *declaration* is any comment carrying `SILENT_ACCEPTANCE_VERSION:`,
`@verification-boundary`, `VERIFICATION_BOUNDARY:`, or the v1.x `PALS_LAW_VERSION:`.
The full contract block from spec §10.1 is the recommended form. A declaration that
also says `@verification-boundary file` (or `SCOPE: file`) within the first 40 lines
covers every call site in that file.

A *call site* is a line matching one of the default provider patterns: Anthropic
(`.messages.create/stream/parse`), OpenAI (`.chat.completions.*`, `.responses.*`,
legacy `.completions.create`), Google GenAI (`generate_content`, `generateContent`),
Vercel AI SDK (`generateText`, `generateObject`, `streamText`, `streamObject`), AWS
Bedrock (`ConverseCommand`, `InvokeModelCommand`, `.converse`, `.invoke_model`),
Ollama, Mistral, and Cohere. Comment lines are never counted. Generic verbs such as
`invoke(` are deliberately excluded; add them per project through a config file.

## Usage

Node 24 runs the TypeScript source directly; there are no runtime dependencies.

```bash
node silent-acceptance-lint/src/cli.ts src/
node silent-acceptance-lint/src/cli.ts src/ --format json
node silent-acceptance-lint/src/cli.ts src/ --window 120 --ext .ts,.py
node silent-acceptance-lint/src/cli.ts src/ --config silent-acceptance.config.json
```

Exit code is 1 when any error-severity finding is reported, 0 otherwise, and always 0
with `--warn-only`.

Config file (all keys optional):

```json
{
  "window": 100,
  "extensions": [".ts", ".py", ".go"],
  "patterns": [
    { "id": "internal.llm", "provider": "in-house gateway", "regex": "\\bllmGateway\\.complete\\s*\\(" }
  ],
  "replace": false
}
```

Excusing a call site whose output does not flow onward:

```ts
// silent-acceptance-ignore: output is discarded; only latency is measured in this probe
await client.messages.create({ ... });
```

## CI

A ready-made GitHub Actions job is in [`ci/github-actions.yml`](./ci/github-actions.yml).
It checks this repository out beside the project and runs the linter over `src/`.

## Development

```bash
cd silent-acceptance-lint
npm test            # node --test 'tests/*.test.ts'
npm run typecheck   # tsc -p tsconfig.json (needs the devDependencies installed)
npm run build       # emits dist/ for the package bin
```

## License

MIT, as declared in `package.json`. The specification it implements is CC BY 4.0; the
practitioner artifacts it looks for are CC0 1.0.
