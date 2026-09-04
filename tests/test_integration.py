"""Integration tests — full pipeline end-to-end."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

import pytest

from pals_check.report import build_report

PROJECT_ROOT = Path(__file__).parent.parent


@pytest.mark.integration
class TestFullPipeline:
    def test_cli_runs_successfully(self):
        """Run the CLI against the real document and verify exit code.

        Runs in a temporary directory, never in the repository root: the CLI writes
        ``output/`` relative to its cwd, and running it from the repo would replace
        the committed audit artifacts with a v1.5.0 run. That happened in commits
        2b2ec89 and 4a49025; the digest guard below keeps it from happening again.
        """
        import hashlib
        import os

        tracked = sorted((PROJECT_ROOT / "output").glob("pals_law_*.json"))
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in tracked}

        with tempfile.TemporaryDirectory() as tmpdir:
            env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
            result = subprocess.run(
                [sys.executable, "-m", "pals_check", str(PROJECT_ROOT / "PALS_LAW-v1.5.0.md"), "--no-verify"],
                capture_output=True,
                text=True,
                cwd=tmpdir,
                timeout=30,
                env=env,
            )
        assert result.returncode == 0
        assert "PALS's LAW" in result.stdout
        assert "Checks passed" in result.stdout

        after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in tracked}
        assert after == before, "the test suite must never rewrite the repository's output/ artifacts"

    def test_cli_writes_output_files(self):
        """Verify CLI creates report and schema JSON files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = {**__import__("os").environ, "PYTHONPATH": str(PROJECT_ROOT)}
            result = subprocess.run(
                [sys.executable, "-m", "pals_check", str(PROJECT_ROOT / "PALS_LAW-v1.5.0.md"), "--no-verify"],
                capture_output=True,
                text=True,
                cwd=tmpdir,
                timeout=30,
                env=env,
            )
            assert result.returncode == 0
            report_path = Path(tmpdir) / "output" / "pals_law_report.json"
            schema_path = Path(tmpdir) / "output" / "pals_law_schema.json"
            assert report_path.exists()
            assert schema_path.exists()

            report_data = json.loads(report_path.read_text())
            assert report_data["document_version"] == "1.5.0"
            assert report_data["total_references"] >= 8

            schema_data = json.loads(schema_path.read_text())
            assert len(schema_data["symbols"]) == 15
            assert len(schema_data["claims"]) == 12

    def test_cli_missing_file_exits_with_error(self):
        result = subprocess.run(
            [sys.executable, "-m", "pals_check", "nonexistent.md"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode != 0
        assert "not found" in result.stderr.lower() or "File not found" in result.stderr

    def test_cli_no_args_exits_with_usage(self):
        result = subprocess.run(
            [sys.executable, "-m", "pals_check"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode != 0
        assert "Usage" in result.stderr


@pytest.mark.integration
class TestReportSchemaConsistency:
    def test_report_references_serializable(self, real_md_text: str):
        """All report data must be JSON-serializable."""
        report, schema = build_report(real_md_text, do_verify=False)
        report_json = json.dumps(asdict(report), default=str)
        schema_json = json.dumps(asdict(schema), default=str)
        assert len(report_json) > 0
        assert len(schema_json) > 0

    def test_report_and_schema_version_match(self, real_md_text: str):
        report, schema = build_report(real_md_text, do_verify=False)
        assert report.document_version == schema.version

    def test_report_and_schema_hash_match(self, real_md_text: str):
        report, schema = build_report(real_md_text, do_verify=False)
        assert report.content_hash == schema.content_hash

    def test_no_checks_failed_on_real_document(self, real_md_text: str):
        report, _ = build_report(real_md_text, do_verify=False)
        assert report.checks_failed == 0, (
            f"Failed checks found: {[c for c in report.math_checks if c['status'] == 'fail']}"
        )
