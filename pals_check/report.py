"""Report assembly for PALS's LAW audit."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from pals_check.constants import ErrorClass, SpecLayout, detect_layout
from pals_check.math_checker import check_math_consistency, extract_math_blocks, validate_section_ids
from pals_check.references import extract_references, verify_references
from pals_check.schema import PALSLawSchema, build_schema


@dataclass
class AuditReport:
    """Complete audit output."""

    document_version: str
    content_hash: str
    references: list[dict]
    math_blocks: list[dict]
    math_checks: list[dict]
    schema_summary: dict
    error_class_coverage: dict
    warnings: list[str]

    total_references: int = 0
    total_math_blocks: int = 0
    checks_passed: int = 0
    checks_warned: int = 0
    checks_failed: int = 0


def build_report(
    text: str, do_verify: bool = True, layout: SpecLayout | None = None
) -> tuple[AuditReport, PALSLawSchema]:
    """Run the full audit pipeline and return (report, schema)."""
    layout = layout or detect_layout(text)

    # Phase 1: References
    refs = extract_references(text)

    if do_verify:
        print("\n  \u2500\u2500 Reference Verification (fetching URLs) \u2500\u2500")
        refs = verify_references(refs)
        print()

    # Phase 2: Math
    math_blocks = extract_math_blocks(text, layout)
    math_checks = check_math_consistency(math_blocks, text, layout)

    # Phase 3: Schema
    schema = build_schema(text, layout)

    # Aggregate
    checks_passed = sum(1 for c in math_checks if c.status == "pass")
    checks_warned = sum(1 for c in math_checks if c.status == "warn")
    checks_failed = sum(1 for c in math_checks if c.status == "fail")

    # Error class coverage analysis
    ec_coverage: dict[str, list[str]] = {ec.value: [] for ec in ErrorClass}
    for ref in refs:
        for ec in ref.error_classes_supported:
            if ec in ec_coverage:
                ec_coverage[ec].append(ref.ref_id)

    uncovered = [ec for ec, refs_list in ec_coverage.items() if not refs_list]

    # Warnings
    warnings: list[str] = []

    # Validate hardcoded section IDs against document structure
    section_warnings = validate_section_ids(text, layout)
    warnings.extend(section_warnings)

    if uncovered:
        warnings.append(f"Error classes with no direct empirical reference: {', '.join(uncovered)}")
    if checks_failed > 0:
        warnings.append(f"{checks_failed} math consistency check(s) FAILED")
    for ref in refs:
        if not ref.doi and not ref.arxiv_id:
            warnings.append(f"Reference '{ref.ref_id}' has no DOI or arXiv ID")
        if ref.verification_status == "unreachable":
            warnings.append(f"Reference '{ref.ref_id}' UNREACHABLE: {ref.fetch_error}")
        elif ref.verification_status == "mismatch":
            warnings.append(
                f"Reference '{ref.ref_id}' TITLE MISMATCH \u2014 "
                f"claimed: '{ref.title[:60]}' vs fetched: '{(ref.fetched_title or '?')[:60]}'"
            )

    # Scope gap checks (from multi-model review feedback)
    # Check if spec addresses cyclic/agentic architectures
    if "cyclic" not in text.lower() and "agentic" not in text.lower() and "self-correct" not in text.lower():
        warnings.append(
            "Scope gap: \u00a73.4 models linear DAG pipelines only \u2014 "
            "cyclic/agentic architectures (ReAct, LangGraph) with self-correction loops are unaddressed"
        )
    # Check if spec addresses policy/compliance error class
    if "ERR_POLICY" not in text and "ERR_COMPLIANCE" not in text:
        warnings.append(
            "Scope gap: no ERR_POLICY/ERR_COMPLIANCE class for outputs that are "
            "correct and well-formed but violate business/safety guardrails"
        )
    # Check if contract block has the spec-version field
    for artifact in schema.artifacts:
        if artifact.artifact_id == "contract_block" and not artifact.contains_spec_version_field:
            warnings.append(
                f"Contract block (\u00a7{artifact.section}) missing {layout.version_field} field \u2014 "
                "contracts become stale as the specification evolves"
            )

    report = AuditReport(
        document_version=schema.version,
        content_hash=schema.content_hash,
        references=[asdict(r) for r in refs],
        math_blocks=[asdict(b) for b in math_blocks],
        math_checks=[asdict(c) for c in math_checks],
        schema_summary={
            "total_symbols": len(schema.symbols),
            "total_claims": len(schema.claims),
            "claims_by_status": _count_by(schema.claims, lambda c: c.status),
            "falsifiable_claims": sum(1 for c in schema.claims if c.is_falsifiable),
            "total_error_classes": len(schema.error_classes),
            "total_artifacts": len(schema.artifacts),
            "structural_classes": schema.structural_error_classes,
            "semantic_classes": schema.semantic_error_classes,
        },
        error_class_coverage=ec_coverage,
        warnings=warnings,
        total_references=len(refs),
        total_math_blocks=len(math_blocks),
        checks_passed=checks_passed,
        checks_warned=checks_warned,
        checks_failed=checks_failed,
    )

    return report, schema


def _count_by(items, key_fn) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        k = key_fn(item)
        counts[k] = counts.get(k, 0) + 1
    return counts
