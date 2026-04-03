"""Tests for pals_check.__main__ — CLI entry point called in-process for coverage."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from pals_check.__main__ import main
from pals_check.signing import generate_certificate, sign_artifact

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

    def test_main_outputs_include_signature(self, capsys):
        md_path = str(PROJECT_ROOT / "PALS_LAW-v1.5.0.md")
        with tempfile.TemporaryDirectory() as tmpdir:
            orig_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                with patch("sys.argv", ["pals_check", md_path, "--no-verify"]):
                    main()
                output = capsys.readouterr()
                assert "DIGITAL SIGNATURE" in output.out
                assert "Payload digest" in output.out
                assert "Seal" in output.out

                report = json.loads((Path(tmpdir) / "output" / "pals_law_report.json").read_text())
                assert "_signature" in report
                assert report["_signature"]["algorithm"] == "sha256"
            finally:
                os.chdir(orig_cwd)


class TestMainPackage:
    def test_package_creates_zip(self, capsys):
        md_path = str(PROJECT_ROOT / "PALS_LAW-v1.5.0.md")
        with tempfile.TemporaryDirectory() as tmpdir:
            orig_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                with patch("sys.argv", ["pals_check", md_path, "--no-verify", "--package"]):
                    main()
                output = capsys.readouterr()
                assert "Package written to" in output.out

                # Find the zip file
                import zipfile
                zips = list(Path(tmpdir).rglob("*.zip"))
                assert len(zips) == 1
                zip_path = zips[0]
                assert "pals-law-v1.5.0-" in zip_path.name

                with zipfile.ZipFile(zip_path) as zf:
                    names = zf.namelist()
                    assert "PALS_LAW-v1.5.0.md" in names
                    assert "pals_law_report.json" in names
                    assert "pals_law_schema.json" in names
                    assert "pals_law_certificate.json" in names
            finally:
                os.chdir(orig_cwd)

    def test_no_package_flag_skips_zip(self, capsys):
        md_path = str(PROJECT_ROOT / "PALS_LAW-v1.5.0.md")
        with tempfile.TemporaryDirectory() as tmpdir:
            orig_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                with patch("sys.argv", ["pals_check", md_path, "--no-verify"]):
                    main()
                output = capsys.readouterr()
                assert "Package written to" not in output.out
                zips = list(Path(tmpdir).rglob("*.zip"))
                assert len(zips) == 0
            finally:
                os.chdir(orig_cwd)


class TestMainCheckSig:
    def test_check_sig_valid_file(self, capsys):
        signed = sign_artifact({"test": "data"}, "hash")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(signed, f)
            f.flush()
            try:
                with patch("sys.argv", ["pals_check", "--check-sig", f.name]):
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code == 0
                output = capsys.readouterr()
                assert "\u2713" in output.out
                assert "Valid" in output.out
            finally:
                os.unlink(f.name)

    def test_check_sig_tampered_file(self, capsys):
        signed = sign_artifact({"test": "data"}, "hash")
        signed["test"] = "tampered"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(signed, f)
            f.flush()
            try:
                with patch("sys.argv", ["pals_check", "--check-sig", f.name]):
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code == 1
                output = capsys.readouterr()
                assert "INVALID" in output.out
            finally:
                os.unlink(f.name)

    def test_check_sig_missing_file(self):
        with patch("sys.argv", ["pals_check", "--check-sig", "/nonexistent.json"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_check_sig_no_file_arg(self):
        with patch("sys.argv", ["pals_check", "--check-sig"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1


class TestMainVerifyCert:
    def test_verify_cert_all_valid(self, capsys):
        md_text = "# Test\nContent."
        report = {"document_version": "1.0", "checks_passed": 1, "checks_warned": 0,
                  "checks_failed": 0, "math_checks": []}
        schema = {"version": "1.0", "symbols": [], "claims": []}
        cert = generate_certificate(md_text, report, schema)

        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path = Path(tmpdir) / "cert.json"
            md_path = Path(tmpdir) / "spec.md"
            report_path = Path(tmpdir) / "report.json"
            schema_path = Path(tmpdir) / "schema.json"

            cert_path.write_text(json.dumps(cert))
            md_path.write_text(md_text)
            report_path.write_text(json.dumps(report))
            schema_path.write_text(json.dumps(schema))

            with patch("sys.argv", ["pals_check", "--verify-cert",
                                     str(cert_path), str(md_path),
                                     str(report_path), str(schema_path)]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0

            output = capsys.readouterr()
            assert "spec: OK" in output.out
            assert "report: OK" in output.out
            assert "schema: OK" in output.out

    def test_verify_cert_tampered_spec(self, capsys):
        md_text = "# Test\nContent."
        report = {"document_version": "1.0", "checks_passed": 1, "checks_warned": 0,
                  "checks_failed": 0, "math_checks": []}
        schema = {"version": "1.0", "symbols": [], "claims": []}
        cert = generate_certificate(md_text, report, schema)

        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path = Path(tmpdir) / "cert.json"
            md_path = Path(tmpdir) / "spec.md"

            cert_path.write_text(json.dumps(cert))
            md_path.write_text("tampered content")

            with patch("sys.argv", ["pals_check", "--verify-cert",
                                     str(cert_path), str(md_path)]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1

    def test_verify_cert_spec_only(self, capsys):
        md_text = "# Test\nContent."
        report = {"document_version": "1.0", "checks_passed": 0, "checks_warned": 0,
                  "checks_failed": 0}
        schema = {"version": "1.0", "symbols": [], "claims": []}
        cert = generate_certificate(md_text, report, schema)

        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path = Path(tmpdir) / "cert.json"
            md_path = Path(tmpdir) / "spec.md"

            cert_path.write_text(json.dumps(cert))
            md_path.write_text(md_text)

            with patch("sys.argv", ["pals_check", "--verify-cert",
                                     str(cert_path), str(md_path)]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0
            output = capsys.readouterr()
            assert "Checks at generation" in output.out
            assert "Generated" in output.out

    def test_verify_cert_no_args(self):
        with patch("sys.argv", ["pals_check", "--verify-cert"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1


class TestMainRefDetailOutput:
    def test_main_prints_fetched_url_title_error(self, capsys):
        """Cover L147/149/151 — ref output with fetched_url, fetched_title, fetch_error."""
        md_path = str(PROJECT_ROOT / "PALS_LAW-v1.5.0.md")
        with tempfile.TemporaryDirectory() as tmpdir:
            orig_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                def fake_verify(refs, quiet=False):
                    for ref in refs:
                        ref.verification_status = "verified"
                        ref.fetched_url = "https://example.com/paper"
                        ref.fetched_title = "Fetched Paper Title"
                        ref.fetch_error = "Some transient error"
                    return refs

                # Must NOT pass --no-verify so verify_references gets called
                with patch("sys.argv", ["pals_check", md_path]):
                    with patch("pals_check.report.verify_references", side_effect=fake_verify):
                        main()
                output = capsys.readouterr()
                assert "URL: https://example.com/paper" in output.out
                assert "Fetched title: Fetched Paper Title" in output.out
                assert "Error: Some transient error" in output.out
            finally:
                os.chdir(orig_cwd)
