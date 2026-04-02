"""CLI entry point for pals-check.

Usage:
    python -m pals_check <path_to_md_file> [--no-verify]

Outputs:
    - output/pals_law_report.json  -- full audit report
    - output/pals_law_schema.json  -- formal schema definition
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

from pals_check.report import build_report


def main() -> None:
    if len(sys.argv) < 2 or "--help" in sys.argv:
        print("Usage: python -m pals_check <path_to_md_file> [--no-verify]", file=sys.stderr)
        print("  --no-verify  Skip network fetching of reference URLs", file=sys.stderr)
        sys.exit(1)

    md_path = Path(sys.argv[1])
    if not md_path.exists():
        print(f"File not found: {md_path}", file=sys.stderr)
        sys.exit(1)

    do_verify = "--no-verify" not in sys.argv

    text = md_path.read_text(encoding="utf-8")
    report, schema = build_report(text, do_verify=do_verify)

    # Ensure output directory exists
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # Write report
    report_path = output_dir / "pals_law_report.json"
    with open(report_path, "w") as f:
        json.dump(asdict(report), f, indent=2, default=str)

    # Write schema
    schema_path = output_dir / "pals_law_schema.json"
    with open(schema_path, "w") as f:
        json.dump(asdict(schema), f, indent=2, default=str)

    # Print summary
    print("=" * 72)
    print("  PALS's LAW \u2014 Deterministic Companion Report")
    print("=" * 72)
    print(f"  Document version : {report.document_version}")
    print(f"  Content hash     : {report.content_hash}")
    print(f"  References       : {report.total_references}")
    print(f"  Math blocks      : {report.total_math_blocks}")
    print(f"  Checks passed    : {report.checks_passed}")
    print(f"  Checks warned    : {report.checks_warned}")
    print(f"  Checks failed    : {report.checks_failed}")
    print()

    if report.warnings:
        print("  WARNINGS:")
        for w in report.warnings:
            print(f"    \u26a0 {w}")
        print()

    # Print reference table
    print("  REFERENCES (normalized):")
    print("  " + "-" * 68)
    for ref_dict in report.references:
        ref_id = ref_dict["ref_id"]
        authors = ref_dict["authors"][:40]
        year = ref_dict["year"]
        doi = ref_dict.get("doi") or ref_dict.get("arxiv_id") or "\u2014"
        classes = ", ".join(ref_dict.get("error_classes_supported", []))
        vstatus = ref_dict.get("verification_status", "unverified")
        vicon = {"verified": "\u2713", "partial": "~", "mismatch": "\u2260",
                 "unreachable": "\u2717", "unverified": "?", "no_identifier": "\u2014"}.get(vstatus, "?")
        print(f"  [{ref_id}] {authors} ({year})  [{vicon} {vstatus}]")
        print(f"    ID: {doi}")
        if ref_dict.get("fetched_url"):
            print(f"    URL: {ref_dict['fetched_url'][:80]}")
        if ref_dict.get("fetched_title"):
            print(f"    Fetched title: {ref_dict['fetched_title'][:80]}")
        if ref_dict.get("fetch_error"):
            print(f"    Error: {ref_dict['fetch_error']}")
        print(f"    Supports: {classes or '(general)'}")
        print(f"    Cited in: {', '.join(ref_dict.get('section_cited_in', []))}")
        print()

    # Print math checks
    print("  MATH CONSISTENCY CHECKS:")
    print("  " + "-" * 68)
    for chk in report.math_checks:
        status_icon = {"pass": "\u2713", "warn": "\u26a0", "fail": "\u2717", "info": "\u2139"}.get(
            chk["status"], "?"
        )
        print(f"  [{status_icon}] {chk['check_id']}: {chk['description']}")
    print()

    # Print schema summary
    print("  FORMAL SCHEMA SUMMARY:")
    print("  " + "-" * 68)
    ss = report.schema_summary
    print(f"  Symbols          : {ss['total_symbols']}")
    print(f"  Claims           : {ss['total_claims']}")
    print(f"  Falsifiable      : {ss['falsifiable_claims']}")
    print(f"  Error classes    : {ss['total_error_classes']}")
    print(f"  Artifacts        : {ss['total_artifacts']}")
    print("  Claims by status :")
    for status, count in ss["claims_by_status"].items():
        print(f"    {status:20s}: {count}")
    print()

    # Print error class coverage
    print("  ERROR CLASS \u2192 REFERENCE COVERAGE:")
    print("  " + "-" * 68)
    for ec, ref_ids in report.error_class_coverage.items():
        marker = "\u2713" if ref_ids else "\u2205"
        print(f"  [{marker}] {ec:25s} \u2192 {', '.join(ref_ids) if ref_ids else 'NO DIRECT REFERENCE'}")
    print()

    print(f"  Report written to: {report_path.resolve()}")
    print(f"  Schema written to: {schema_path.resolve()}")
    print("=" * 72)


if __name__ == "__main__":
    main()
