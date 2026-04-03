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
import zipfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from pals_check.report import build_report
from pals_check.signing import generate_certificate, sign_artifact, verify_artifact, verify_certificate


def main() -> None:
    if len(sys.argv) < 2 or "--help" in sys.argv:
        print("Usage: python -m pals_check <path_to_md_file> [--no-verify]", file=sys.stderr)
        print("       python -m pals_check --check-sig <json_file>", file=sys.stderr)
        print("       python -m pals_check --verify-cert <cert.json> <spec.md> [report.json] [schema.json]", file=sys.stderr)
        print("  --no-verify    Skip network fetching of reference URLs", file=sys.stderr)
        print("  --package      Bundle spec + outputs into a signed .zip archive", file=sys.stderr)
        print("  --check-sig    Verify the digital signature of an output file", file=sys.stderr)
        print("  --verify-cert  Verify a certificate against source artifacts", file=sys.stderr)
        sys.exit(1)

    # Certificate verification mode
    if sys.argv[1] == "--verify-cert":
        if len(sys.argv) < 4:
            print("Usage: python -m pals_check --verify-cert <cert.json> <spec.md> [report.json] [schema.json]", file=sys.stderr)
            sys.exit(1)
        cert_path = Path(sys.argv[2])
        cert = json.loads(cert_path.read_text(encoding="utf-8"))

        md_text = Path(sys.argv[3]).read_text(encoding="utf-8")

        report_dict = None
        schema_dict = None
        for arg in sys.argv[4:]:
            p = Path(arg)
            data = json.loads(p.read_text(encoding="utf-8"))
            if "math_checks" in data or "math_blocks" in data:
                report_dict = data
            elif "symbols" in data or "claims" in data:
                schema_dict = data

        valid, messages = verify_certificate(cert, md_text, report_dict, schema_dict)
        for msg in messages:
            icon = "\u2713" if ": OK" in msg else "\u2717"
            print(f"  {icon} {msg}")
        checks = cert.get("checks", {})
        print(f"  Checks at generation: {checks.get('passed', '?')} passed, "
              f"{checks.get('warned', '?')} warned, {checks.get('failed', '?')} failed")
        print(f"  Generated: {cert.get('generated_at', '?')}")
        sys.exit(0 if valid else 1)

    # Signature verification mode
    if sys.argv[1] == "--check-sig":
        if len(sys.argv) < 3:
            print("Usage: python -m pals_check --check-sig <json_file>", file=sys.stderr)
            sys.exit(1)
        sig_path = Path(sys.argv[2])
        if not sig_path.exists():
            print(f"File not found: {sig_path}", file=sys.stderr)
            sys.exit(1)
        signed = json.loads(sig_path.read_text(encoding="utf-8"))
        valid, message = verify_artifact(signed)
        if valid:
            print(f"\u2713 {message}")
            sys.exit(0)
        else:
            print(f"\u2717 INVALID: {message}")
            sys.exit(1)

    md_path = Path(sys.argv[1])
    if not md_path.exists():
        print(f"File not found: {md_path}", file=sys.stderr)
        sys.exit(1)

    do_verify = "--no-verify" not in sys.argv
    do_package = "--package" in sys.argv

    text = md_path.read_text(encoding="utf-8")
    report, schema = build_report(text, do_verify=do_verify)

    # Ensure output directory exists
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # Sign and write report
    source_hash = report.content_hash
    report_dict = sign_artifact(asdict(report), source_hash)
    report_path = output_dir / "pals_law_report.json"
    with open(report_path, "w") as f:
        json.dump(report_dict, f, indent=2, default=str)

    # Sign and write schema
    schema_dict = sign_artifact(asdict(schema), source_hash)
    schema_path = output_dir / "pals_law_schema.json"
    with open(schema_path, "w") as f:
        json.dump(schema_dict, f, indent=2, default=str)

    # Generate and write certificate binding all three artifacts
    cert = generate_certificate(text, report_dict, schema_dict)
    cert_path = output_dir / "pals_law_certificate.json"
    with open(cert_path, "w") as f:
        json.dump(cert, f, indent=2, default=str)

    # Package into zip if requested
    zip_path = None
    if do_package:
        version = report.document_version
        ts = datetime.now(timezone.utc).strftime("%Y%m%d")
        zip_name = f"pals-law-v{version}-{ts}.zip"
        zip_path = output_dir / zip_name

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(md_path, md_path.name)
            zf.write(report_path, report_path.name)
            zf.write(schema_path, schema_path.name)
            zf.write(cert_path, cert_path.name)

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

    # Signature info
    sig = report_dict["_signature"]
    print("  DIGITAL SIGNATURE:")
    print("  " + "-" * 68)
    print(f"  Algorithm        : {sig['algorithm']}")
    print(f"  Payload digest   : {sig['payload_digest'][:32]}...")
    print(f"  Seal             : {sig['seal'][:32]}...")
    print(f"  Signed at        : {sig['signed_at']}")
    print(f"  Tool             : {sig['tool_id']} v{sig['tool_version']}")
    print()

    # Certificate info
    print("  CERTIFICATE:")
    print("  " + "-" * 68)
    print(f"  Spec digest      : {cert['spec']['digest'][:32]}...")
    print(f"  Report digest    : {cert['report']['digest'][:32]}...")
    print(f"  Schema digest    : {cert['schema']['digest'][:32]}...")
    print(f"  Binding          : {cert['binding']['digest'][:32]}...")
    print(f"  Generated        : {cert['generated_at']}")
    print()

    print(f"  Report written to     : {report_path.resolve()}")
    print(f"  Schema written to     : {schema_path.resolve()}")
    print(f"  Certificate written to: {cert_path.resolve()}")
    if zip_path:
        print(f"  Package written to    : {zip_path.resolve()}")
    print()
    print(f"  Verify with: python -m pals_check --verify-cert {cert_path} {md_path} {report_path} {schema_path}")
    print("=" * 72)


if __name__ == "__main__":
    main()
