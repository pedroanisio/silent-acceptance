"""Tests for pals_check.report — audit report assembly."""

from __future__ import annotations

from pals_check.report import AuditReport, _count_by, build_report


class TestBuildReport:
    def test_build_report_returns_tuple(self, minimal_md_text: str):
        report, schema = build_report(minimal_md_text, do_verify=False)
        assert isinstance(report, AuditReport)

    def test_build_report_reference_count(self, minimal_md_text: str):
        report, _ = build_report(minimal_md_text, do_verify=False)
        assert report.total_references == 2

    def test_build_report_math_blocks_found(self, minimal_md_text: str):
        report, _ = build_report(minimal_md_text, do_verify=False)
        assert report.total_math_blocks >= 4

    def test_build_report_checks_sum(self, minimal_md_text: str):
        report, _ = build_report(minimal_md_text, do_verify=False)
        total = report.checks_passed + report.checks_warned + report.checks_failed
        assert total == len(report.math_checks)

    def test_build_report_error_class_coverage_keys(self, minimal_md_text: str):
        report, _ = build_report(minimal_md_text, do_verify=False)
        assert "ERR_HALLUCINATION" in report.error_class_coverage
        assert "ERR_SCHEMA" in report.error_class_coverage
        assert len(report.error_class_coverage) == 9

    def test_build_report_warnings_for_uncovered_classes(self, minimal_md_text: str):
        report, _ = build_report(minimal_md_text, do_verify=False)
        has_uncovered_warning = any("no direct empirical reference" in w.lower() for w in report.warnings)
        assert has_uncovered_warning

    def test_build_report_schema_summary_structure(self, minimal_md_text: str):
        report, _ = build_report(minimal_md_text, do_verify=False)
        ss = report.schema_summary
        assert "total_symbols" in ss
        assert "total_claims" in ss
        assert "claims_by_status" in ss
        assert "falsifiable_claims" in ss

    def test_build_report_real_document(self, real_md_text: str):
        report, schema = build_report(real_md_text, do_verify=False)
        assert report.document_version == "1.5.0"
        assert report.total_references >= 8
        assert report.checks_passed >= 5


class TestCountBy:
    def test_count_by_simple(self):
        items = ["a", "b", "a", "c", "a"]
        counts = _count_by(items, lambda x: x)
        assert counts == {"a": 3, "b": 1, "c": 1}

    def test_count_by_empty(self):
        assert _count_by([], lambda x: x) == {}

    def test_count_by_with_key_fn(self):
        items = [{"t": "x"}, {"t": "y"}, {"t": "x"}]
        counts = _count_by(items, lambda i: i["t"])
        assert counts == {"x": 2, "y": 1}
