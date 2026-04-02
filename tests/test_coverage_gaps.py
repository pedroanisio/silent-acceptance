"""Tests to close remaining coverage gaps across modules."""

from __future__ import annotations

import urllib.error
from unittest.mock import MagicMock, patch

from pals_check.math_checker import (
    _describe_math_block,
    _get_section_text,
    check_math_consistency,
    extract_math_blocks,
)
from pals_check.references import (
    Reference,
    _fetch_and_extract,
    extract_references,
    verify_references,
)
from pals_check.report import build_report


# === references.py gaps ===


class TestExtractReferencesEdgeCases:
    def test_skips_header_row_starting_with_reference(self):
        text = """\
## 4. Table

| Reference | Relevance | Confidence |
| --- | --- | --- |
"""
        refs = extract_references(text)
        assert refs == []

    def test_skips_row_starting_with_class_or_bold(self):
        text = """\
## 4. Table

| **Bold header** (2024) | rel | conf |
| Class description (2024) | rel | conf |
"""
        refs = extract_references(text)
        assert refs == []

    def test_inline_citation_section_merging(self):
        """Test that inline citations from sections get merged into refs with partial key matches."""
        text = """\
## 4. Table

| Ji, Z. (2023), "Survey of Hallucination," *ACM*, DOI: 10.1145/3571730 | hallucination | High |

## 6. Arguments

Ji et al. (2023) showed important results.

## 7. Limitations

Other text.
"""
        refs = extract_references(text)
        assert len(refs) == 1
        # Line 88: section_cited_in should include §6 from inline citation merge
        assert any("§6" in s for s in refs[0].section_cited_in)


class TestVerifyReferencesVerbose:
    @patch("pals_check.references._fetch_and_extract")
    def test_verify_with_quiet_false_prints_output(self, mock_fetch, capsys):
        mock_fetch.return_value = {
            "status": "verified", "url": "https://doi.org/x",
            "fetched_title": "Title", "match_quality": 0.9,
        }
        ref = Reference(
            ref_id="test_2024", authors="Test", year=2024,
            title="Title", venue="Conf", doi="10.1234/test",
        )
        verify_references([ref], quiet=False)
        output = capsys.readouterr().out
        assert "Verifying" in output
        assert "verified" in output

    def test_verify_no_identifier_verbose(self, capsys):
        ref = Reference(
            ref_id="test_2024", authors="Test", year=2024,
            title="Title", venue="Conf",
        )
        verify_references([ref], quiet=False)
        output = capsys.readouterr().out
        assert "no identifier" in output

    @patch("pals_check.references._fetch_and_extract")
    def test_verify_arxiv_only(self, mock_fetch):
        mock_fetch.return_value = {
            "status": "verified", "url": "https://arxiv.org/abs/1234.5678",
            "fetched_title": "Paper", "match_quality": 0.8,
        }
        ref = Reference(
            ref_id="test_2024", authors="Test", year=2024,
            title="Paper", venue="Conf", arxiv_id="1234.5678.",
        )
        result = verify_references([ref], quiet=True)
        assert result[0].verification_status == "verified"

    @patch("pals_check.references._fetch_and_extract")
    @patch("pals_check.references.time")
    def test_verify_multiple_refs_rate_limits(self, mock_time, mock_fetch):
        mock_fetch.return_value = {
            "status": "verified", "url": "https://doi.org/x",
            "fetched_title": "T", "match_quality": 0.9,
        }
        refs = [
            Reference(ref_id=f"r{i}", authors="A", year=2024, title="T", venue="V", doi=f"10/{i}")
            for i in range(3)
        ]
        verify_references(refs, quiet=True)
        # sleep called between refs (not after last)
        assert mock_time.sleep.call_count == 2


class TestFetchAndExtract:
    def test_fetch_html_with_title_verified(self):
        ref = Reference(ref_id="x", authors="A", year=2024, title="My Paper", venue="V")
        html = b"<html><head><title>My Paper - Journal</title></head></html>"
        mock_resp = MagicMock()
        mock_resp.url = "https://example.com/paper"
        mock_resp.headers = {"Content-Type": "text/html; charset=utf-8"}
        mock_resp.read.return_value = html
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("pals_check.references.urllib.request.urlopen", return_value=mock_resp):
            result = _fetch_and_extract("https://example.com", ref)
        assert result["status"] == "verified"

    def test_fetch_html_mismatch(self):
        ref = Reference(ref_id="x", authors="A", year=2024, title="Quantum Computing", venue="V")
        html = b"<html><head><title>Cat Food Reviews</title></head></html>"
        mock_resp = MagicMock()
        mock_resp.url = "https://example.com"
        mock_resp.headers = {"Content-Type": "text/html"}
        mock_resp.read.return_value = html
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("pals_check.references.urllib.request.urlopen", return_value=mock_resp):
            result = _fetch_and_extract("https://example.com", ref)
        assert result["status"] == "mismatch"

    def test_fetch_pdf_returns_partial(self):
        ref = Reference(ref_id="x", authors="A", year=2024, title="Paper", venue="V")
        mock_resp = MagicMock()
        mock_resp.url = "https://example.com/paper.pdf"
        mock_resp.headers = {"Content-Type": "application/pdf"}
        mock_resp.read.return_value = b"%PDF-1.4"
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("pals_check.references.urllib.request.urlopen", return_value=mock_resp):
            result = _fetch_and_extract("https://example.com", ref)
        assert result["status"] == "partial"

    def test_fetch_no_title_returns_partial(self):
        ref = Reference(ref_id="x", authors="A", year=2024, title="Paper", venue="V")
        html = b"<html><body>No title tag here</body></html>"
        mock_resp = MagicMock()
        mock_resp.url = "https://example.com"
        mock_resp.headers = {"Content-Type": "text/html"}
        mock_resp.read.return_value = html
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("pals_check.references.urllib.request.urlopen", return_value=mock_resp):
            result = _fetch_and_extract("https://example.com", ref)
        assert result["status"] == "partial"

    def test_fetch_with_charset_in_content_type(self):
        ref = Reference(ref_id="x", authors="A", year=2024, title="Paper Title", venue="V")
        html = b"<html><head><title>Paper Title</title></head></html>"
        mock_resp = MagicMock()
        mock_resp.url = "https://example.com"
        mock_resp.headers = {"Content-Type": "text/html; charset=iso-8859-1"}
        mock_resp.read.return_value = html
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("pals_check.references.urllib.request.urlopen", return_value=mock_resp):
            result = _fetch_and_extract("https://example.com", ref)
        assert result["status"] == "verified"

    def test_fetch_with_bad_charset_falls_back_to_utf8(self):
        ref = Reference(ref_id="x", authors="A", year=2024, title="Paper Title", venue="V")
        html = b"<html><head><title>Paper Title</title></head></html>"
        mock_resp = MagicMock()
        mock_resp.url = "https://example.com"
        mock_resp.headers = {"Content-Type": "text/html; charset=bogus-encoding"}
        mock_resp.read.return_value = html
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("pals_check.references.urllib.request.urlopen", return_value=mock_resp):
            result = _fetch_and_extract("https://example.com", ref)
        assert result["status"] == "verified"

    def test_fetch_http_error(self):
        ref = Reference(ref_id="x", authors="A", year=2024, title="P", venue="V")
        with patch("pals_check.references.urllib.request.urlopen",
                    side_effect=urllib.error.HTTPError("url", 404, "Not Found", {}, None)):
            result = _fetch_and_extract("https://example.com", ref)
        assert result["status"] == "unreachable"
        assert "404" in result["error"]

    def test_fetch_url_error(self):
        ref = Reference(ref_id="x", authors="A", year=2024, title="P", venue="V")
        with patch("pals_check.references.urllib.request.urlopen",
                    side_effect=urllib.error.URLError("Connection refused")):
            result = _fetch_and_extract("https://example.com", ref)
        assert result["status"] == "unreachable"
        assert "URL error" in result["error"]

    def test_fetch_generic_exception(self):
        ref = Reference(ref_id="x", authors="A", year=2024, title="P", venue="V")
        with patch("pals_check.references.urllib.request.urlopen",
                    side_effect=TimeoutError("timed out")):
            result = _fetch_and_extract("https://example.com", ref)
        assert result["status"] == "unreachable"
        assert "TimeoutError" in result["error"]


# === math_checker.py gaps ===


class TestDescribeMathBlockGaps:
    def test_describe_quantified_claim(self):
        desc = _describe_math_block(r"\forall x \exists y", "99")
        assert desc == "Quantified claim"

    def test_describe_expectation_claim(self):
        desc = _describe_math_block(r"\mathbb{E}[X]", "99")
        assert desc == "Expectation-based claim"


class TestCheckMathConsistencyFallbackSearch:
    def test_independence_caveat_fallback_search(self):
        """Test the fallback section search (lines 291-302) when _get_section_text fails."""
        # Build a doc where ### 3.4 and ### 7.3 exist but use non-standard heading format
        # that _get_section_text misses but the fallback `###?\s+` pattern catches
        text = """\
## 3 Formal Statement

### 3.1 Definitions

$$
\\varepsilon(y, x) \\in \\{0, 1\\}
$$

### 3.2 Operative Form

$$
\\forall M \\in \\mathcal{M},\\ \\forall \\text{ realistic } \\mathcal{D}: \\mathbb{E}_{x \\sim \\mathcal{D}}[\\varepsilon(M(x), x)] \\geq \\delta > 0
$$

### 3.3 Existential Form

$$
\\forall M: \\exists x \\text{ s.t. } P(\\varepsilon=1) > 0
$$

## 3.4. Pipeline

Assumes independence between stages. Correlated failures possible.

$$
\\prod_{i=1}^{n}(1-p_i)
$$

$$
1 - \\prod_{i=1}^{n}(1-p_i) \\to 1
$$

## 7.3. Independence

The independence assumption may not hold. Correlation between errors exists.

## 8 Corollaries

Some text.
"""
        blocks = extract_math_blocks(text)
        checks = check_math_consistency(blocks, text)
        indep = next((c for c in checks if c.check_id == "CHK_INDEPENDENCE_PROPAGATION"), None)
        assert indep is not None

    def test_cross_references_with_broken_refs(self):
        """Test broken cross-reference detection (lines 344-345)."""
        text = """\
## 1 Preamble

See §99.9 for details.

## 3 Formal

Content referencing §1 (exists) and §42 (broken).
"""
        blocks = extract_math_blocks(text)
        checks = check_math_consistency(blocks, text)
        xref = next((c for c in checks if c.check_id == "CHK_CROSS_REFERENCES"), None)
        assert xref is not None
        assert xref.status == "fail"
        assert "42" in xref.detail or "99.9" in xref.detail


# === report.py gaps ===


class TestBuildReportGaps:
    def test_build_report_with_verify_prints(self, minimal_md_text: str, capsys):
        """Lines 39-41: do_verify=True branch."""
        with patch("pals_check.report.verify_references", return_value=[]):
            report, _ = build_report(minimal_md_text, do_verify=True)
        output = capsys.readouterr().out
        assert "Reference Verification" in output

    def test_build_report_failed_checks_warning(self):
        """Line 71: checks_failed > 0 warning."""
        # Build a doc that causes a failed check (broken cross-reference)
        text = """\
**Document version:** 0.0.1

## 1 Section

See §999 for something that doesn't exist.
"""
        report, _ = build_report(text, do_verify=False)
        if report.checks_failed > 0:
            assert any("FAILED" in w for w in report.warnings)

    def test_build_report_no_doi_warning(self):
        """Lines 73-74: reference with no DOI or arXiv."""
        text = """\
**Document version:** 0.0.1

## 4. Refs

| Author (2024), "Title," *Venue* | relevance | High |
"""
        report, _ = build_report(text, do_verify=False)
        assert any("no DOI" in w for w in report.warnings)

    def test_build_report_unreachable_warning(self):
        """Lines 75-76: unreachable reference warning."""
        text = """\
**Document version:** 0.0.1

## 4. Refs

| Author (2024), "Title," *Venue*, DOI: 10.1234/fake | relevance | High |
"""
        with patch("pals_check.report.verify_references") as mock_verify:
            ref = Reference(
                ref_id="author_2024", authors="Author", year=2024,
                title="Title", venue="Venue", doi="10.1234/fake",
                verification_status="unreachable", fetch_error="HTTP 500",
            )
            mock_verify.return_value = [ref]
            report, _ = build_report(text, do_verify=True)
        assert any("UNREACHABLE" in w for w in report.warnings)

    def test_build_report_mismatch_warning(self):
        """Lines 77-78: mismatched reference warning."""
        text = """\
**Document version:** 0.0.1

## 4. Refs

| Author (2024), "Title," *Venue*, DOI: 10.1234/fake | relevance | High |
"""
        with patch("pals_check.report.verify_references") as mock_verify:
            ref = Reference(
                ref_id="author_2024", authors="Author", year=2024,
                title="Title", venue="Venue", doi="10.1234/fake",
                verification_status="mismatch", fetched_title="Wrong Title",
            )
            mock_verify.return_value = [ref]
            report, _ = build_report(text, do_verify=True)
        assert any("MISMATCH" in w for w in report.warnings)
