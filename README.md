# pals-check

Deterministic companion for **PALS's LAW**: a small Python CLI that audits the law's Markdown specification for reference integrity, math consistency, and formal schema structure.

It takes the source document in [`PALS_LAW-v1.5.0.md`](/home/admin/codebases/pals-check/PALS_LAW-v1.5.0.md), runs a deterministic analysis pipeline, and writes machine-readable artifacts to [`output/`](/home/admin/codebases/pals-check/output).

> [!IMPORTANT]
> This project verifies the internal consistency of the specification and can optionally fetch cited URLs for cross-checking, but it does not turn the document into ground truth. The repo's own disclaimer still applies: claims and references should be independently verified before being treated as authoritative.

## What it does

- Extracts and normalizes the references declared in the spec.
- Optionally fetches DOI and arXiv targets to compare claimed vs fetched metadata.
- Parses display-math blocks and runs consistency checks over the formal claims.
- Builds a formal schema for symbols, claims, error classes, and practitioner artifacts.
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
├── output/                 # Generated report and schema JSON
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

If you want live reference verification against DOI and arXiv URLs, omit `--no-verify`:

```bash
python3 -m pals_check PALS_LAW-v1.5.0.md
```

## CLI usage

```text
python -m pals_check <path_to_md_file> [--no-verify]

--no-verify    Skip network fetching of reference URLs
```

The project also exposes a `pals-check` console script in [`pyproject.toml`](/home/admin/codebases/pals-check/pyproject.toml) for environments where the package is installed.

The CLI prints a terminal summary with:

- document version and content hash
- normalized references and verification status
- math consistency checks
- schema totals for symbols, claims, error classes, and artifacts
- error-class coverage warnings

## Generated artifacts

### `pals_law_report.json`

Operational audit output containing:

- normalized references
- extracted math blocks
- check results
- schema summary
- warnings
- aggregate counters

### `pals_law_schema.json`

Formal schema output containing:

- symbols and type signatures
- formal claims and epistemic status
- error class definitions
- practitioner artifacts
- dependency graph
- structural vs semantic error-class partitions

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

- `140` passing tests
- strict `ruff` linting configuration
- `mypy` settings in [`pyproject.toml`](/home/admin/codebases/pals-check/pyproject.toml)

## How the pipeline is organized

The core modules under [`pals_check/`](/home/admin/codebases/pals-check/pals_check) are intentionally small and direct:

- [`pals_check/references.py`](/home/admin/codebases/pals-check/pals_check/references.py) collects references and optionally verifies them over the network.
- [`pals_check/math_checker.py`](/home/admin/codebases/pals-check/pals_check/math_checker.py) extracts `$$...$$` blocks and checks formal consistency.
- [`pals_check/schema.py`](/home/admin/codebases/pals-check/pals_check/schema.py) builds the structured schema representation.
- [`pals_check/report.py`](/home/admin/codebases/pals-check/pals_check/report.py) assembles the final audit report.
- [`pals_check/__main__.py`](/home/admin/codebases/pals-check/pals_check/__main__.py) provides the CLI entry point.

## Scope and limitations

- The tool is tailored to the current structure of the PALS's LAW spec, including section-aware parsing and hardcoded semantic mappings.
- Reference verification depends on live network access and publisher behavior; DOI hosts may block automated requests.
- The generated JSON is only as current as the last regeneration step. `make check` is the intended guard against output drift.

If you are editing the specification itself, the normal workflow is: update the Markdown source, run `make check`, review the JSON diff, and commit the regenerated artifacts together.
