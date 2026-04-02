---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "OpenAI Codex via Codex CLI"
  date: "2026-04-02"
---

# pals-check

Deterministic companion for **PALS's LAW**: a small Python CLI that audits the law's Markdown specification for reference integrity, math consistency, and formal schema structure.

It takes the source document in [`PALS_LAW-v1.5.0.md`](/home/admin/codebases/pals-check/PALS_LAW-v1.5.0.md), runs a deterministic analysis pipeline, and writes machine-readable artifacts to [`output/`](/home/admin/codebases/pals-check/output).

## Disclaimer

This work is subject to the methodological caveats and commitments described in [@DISCLAIMER.md](./DISCLAIMER.md).
> No statement or premise not backed by a real logical definition or verifiable reference should be taken for granted.

> [!IMPORTANT]
> This project verifies the internal consistency of the specification and can optionally fetch cited URLs for cross-checking, but it does not turn the document into ground truth. The repo's own disclaimer still applies: claims and references should be independently verified before being treated as authoritative.

## What it does

- Extracts and normalizes the references declared in the spec.
- Optionally fetches DOI and arXiv targets to compare claimed vs fetched metadata.
- Parses display-math blocks and runs consistency checks over the formal claims.
- Builds a formal schema for symbols, claims, error classes, and practitioner artifacts.
- Signs generated JSON artifacts and emits a binding certificate for tamper-evident verification.
- Emits JSON artifacts that can be reviewed, diffed, or consumed by downstream tooling.

For the current checked-in spec, the generated report summarizes:

- `10` references
- `7` math blocks
- `9` passed checks
- `0` failed checks

## Repository layout

```text
.
├── PALS_LAW-v1.5.0.md      # Source specification
├── pals_check/             # CLI and audit pipeline
├── tests/                  # Unit, property, and integration tests
├── output/                 # Generated report, schema, and certificate JSON
├── DISCLAIMER.md           # Project disclaimer
└── Makefile                # Common commands
```

## Quickstart

### Requirements

- Python `3.10+`

### Run from source

```bash
python3 -m pals_check PALS_LAW-v1.5.0.md --no-verify
```

This writes:

- [`output/pals_law_report.json`](/home/admin/codebases/pals-check/output/pals_law_report.json)
- [`output/pals_law_schema.json`](/home/admin/codebases/pals-check/output/pals_law_schema.json)
- [`output/pals_law_certificate.json`](/home/admin/codebases/pals-check/output/pals_law_certificate.json)

If you want live reference verification against DOI and arXiv URLs, omit `--no-verify`:

```bash
python3 -m pals_check PALS_LAW-v1.5.0.md
```

## CLI usage

```text
python -m pals_check <path_to_md_file> [--no-verify]
python -m pals_check --check-sig <json_file>
python -m pals_check --verify-cert <cert.json> <spec.md> [report.json] [schema.json]

--no-verify    Skip network fetching of reference URLs
--check-sig    Verify the digital signature of an output file
--verify-cert  Verify a certificate against source artifacts
```

The project also exposes a `pals-check` console script in [`pyproject.toml`](/home/admin/codebases/pals-check/pyproject.toml) for environments where the package is installed.

The CLI prints a terminal summary with:

- document version and content hash
- normalized references and verification status
- math consistency checks
- schema totals for symbols, claims, error classes, and artifacts
- error-class coverage warnings
- per-artifact signature metadata
- certificate digests binding spec, report, and schema together

## Generated artifacts

### `pals_law_report.json`

Operational audit output containing:

- normalized references
- extracted math blocks
- check results
- schema summary
- warnings
- aggregate counters
- `_signature` metadata proving the payload digest and signing tool version

### `pals_law_schema.json`

Formal schema output containing:

- symbols and type signatures
- formal claims and epistemic status
- error class definitions
- practitioner artifacts
- dependency graph
- structural vs semantic error-class partitions
- `_signature` metadata proving the payload digest and signing tool version

### `pals_law_certificate.json`

Standalone binding certificate containing:

- SHA-256 digests for the source spec, report payload, and schema payload
- generation timestamp and tool version
- aggregate check counts at generation time
- a certificate binding digest used to verify the certificate itself

You can verify outputs after generation with:

```bash
python3 -m pals_check --check-sig output/pals_law_report.json
python3 -m pals_check --check-sig output/pals_law_schema.json
python3 -m pals_check --verify-cert \
  output/pals_law_certificate.json \
  PALS_LAW-v1.5.0.md \
  output/pals_law_report.json \
  output/pals_law_schema.json
```

## Development

Common commands are exposed through [`Makefile`](/home/admin/codebases/pals-check/Makefile):

```bash
make regen         # regenerate output JSON without network fetches
make regen-verify  # regenerate output JSON with DOI/arXiv verification
make lint          # run ruff checks
make test          # run pytest with coverage
make check         # lint, test, regenerate, and detect output drift
```

The repository currently includes:

- `198` passing tests
- strict `ruff` linting configuration
- `mypy` settings in [`pyproject.toml`](/home/admin/codebases/pals-check/pyproject.toml)
- targeted regression coverage for drift bugs and signing/certificate verification

## How the pipeline is organized

The core modules under [`pals_check/`](/home/admin/codebases/pals-check/pals_check) are intentionally small and direct:

- [`pals_check/references.py`](/home/admin/codebases/pals-check/pals_check/references.py) collects references and optionally verifies them over the network.
- [`pals_check/math_checker.py`](/home/admin/codebases/pals-check/pals_check/math_checker.py) extracts `$$...$$` blocks and checks formal consistency.
- [`pals_check/schema.py`](/home/admin/codebases/pals-check/pals_check/schema.py) builds the structured schema representation.
- [`pals_check/report.py`](/home/admin/codebases/pals-check/pals_check/report.py) assembles the final audit report.
- [`pals_check/signing.py`](/home/admin/codebases/pals-check/pals_check/signing.py) signs artifacts and verifies report/schema certificates.
- [`pals_check/__main__.py`](/home/admin/codebases/pals-check/pals_check/__main__.py) provides the CLI entry point.

## Scope and limitations

- The tool is tailored to the current structure of the PALS's LAW spec, including section-aware parsing and hardcoded semantic mappings.
- Reference verification depends on live network access and publisher behavior; DOI hosts may block automated requests.
- Signatures and certificates make output tampering evident, but they do not replace independent validation of the spec's claims or references.
- The generated JSON is only as current as the last regeneration step. `make check` is the intended guard against output drift.

If you are editing the specification itself, the normal workflow is: update the Markdown source, run `make check`, review the JSON diff, and commit the regenerated artifacts together.
