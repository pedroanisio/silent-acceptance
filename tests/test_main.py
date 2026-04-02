"""Tests for pals_check.__main__ — CLI entry point called in-process for coverage."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from pals_check.__main__ import main

PROJECT_ROOT = Path(__file__).parent.parent


class TestMainInProcess:
    def test_main_no_args_exits(self):
        with patch("sys.argv", ["pals_check"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_main_help_exits(self):
        with patch("sys.argv", ["pals_check", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_main_missing_file_exits(self):
        with patch("sys.argv", ["pals_check", "/nonexistent/file.md"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_main_runs_full_report(self, capsys):
        md_path = str(PROJECT_ROOT / "PALS_LAW-v1.5.0.md")
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("sys.argv", ["pals_check", md_path, "--no-verify"]):
                # Patch output dir to tmpdir
                with patch("pals_check.__main__.Path") as MockPath:
                    # Make md_path work normally
                    real_path = Path(md_path)
                    mock_md = MockPath.return_value
                    mock_md.exists.return_value = real_path.exists()
                    mock_md.read_text.return_value = real_path.read_text(encoding="utf-8")

                    # Make output dir point to tmpdir
                    output_dir = Path(tmpdir) / "output"
                    output_dir.mkdir()

                    # We need a simpler approach - just run in tmpdir
                    pass

        # Simpler: just call main with cwd patched
        with tempfile.TemporaryDirectory() as tmpdir:
            import os
            orig_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                with patch("sys.argv", ["pals_check", md_path, "--no-verify"]):
                    main()
                output = capsys.readouterr()
                assert "PALS's LAW" in output.out
                assert "Checks passed" in output.out
                assert "REFERENCES" in output.out
                assert "MATH CONSISTENCY" in output.out
                assert "FORMAL SCHEMA" in output.out
                assert "ERROR CLASS" in output.out

                # Verify output files
                report_path = Path(tmpdir) / "output" / "pals_law_report.json"
                schema_path = Path(tmpdir) / "output" / "pals_law_schema.json"
                assert report_path.exists()
                assert schema_path.exists()

                report = json.loads(report_path.read_text())
                assert report["document_version"] == "1.5.0"
            finally:
                os.chdir(orig_cwd)

    def test_main_prints_warnings(self, capsys):
        """The real document has uncovered error classes, so warnings should print."""
        md_path = str(PROJECT_ROOT / "PALS_LAW-v1.5.0.md")
        with tempfile.TemporaryDirectory() as tmpdir:
            import os
            orig_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                with patch("sys.argv", ["pals_check", md_path, "--no-verify"]):
                    main()
                output = capsys.readouterr()
                assert "WARNINGS" in output.out
            finally:
                os.chdir(orig_cwd)

    def test_main_prints_reference_details(self, capsys):
        """Verify reference output includes IDs, supports, and cited-in fields."""
        md_path = str(PROJECT_ROOT / "PALS_LAW-v1.5.0.md")
        with tempfile.TemporaryDirectory() as tmpdir:
            import os
            orig_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                with patch("sys.argv", ["pals_check", md_path, "--no-verify"]):
                    main()
                output = capsys.readouterr()
                assert "[ji_2023]" in output.out
                assert "Supports:" in output.out
                assert "Cited in:" in output.out
            finally:
                os.chdir(orig_cwd)
