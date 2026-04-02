"""Tests for pals_check.references — extraction, parsing, and verification helpers."""

from __future__ import annotations

from unittest.mock import patch

from pals_check.references import (
    Reference,
    _extract_html_title,
    _extract_meta_citation_title,
    _parse_formal_reference,
    _title_match,
    extract_references,
    verify_references,
)


# --- extract_references ---


class TestExtractReferences:
    def test_extract_references_from_table_rows(self, minimal_md_text: str):
        refs = extract_references(minimal_md_text)
        assert len(refs) >= 2
        ref_ids = [r.ref_id for r in refs]
        assert "ji_2023" in ref_ids
        assert "kadavath_2022" in ref_ids

    def test_extract_references_captures_doi(self, minimal_md_text: str):
        refs = extract_references(minimal_md_text)
        ji = next(r for r in refs if r.ref_id == "ji_2023")
        assert ji.doi == "10.1145/3571730"

    def test_extract_references_captures_arxiv(self, minimal_md_text: str):
        refs = extract_references(minimal_md_text)
        kad = next(r for r in refs if r.ref_id == "kadavath_2022")
        assert kad.arxiv_id == "2207.05221"

    def test_extract_references_maps_error_classes(self, minimal_md_text: str):
        refs = extract_references(minimal_md_text)
        ji = next(r for r in refs if r.ref_id == "ji_2023")
        assert "ERR_HALLUCINATION" in ji.error_classes_supported

    def test_extract_references_skips_header_rows(self):
        text = """\
## 4. Table

| Reference | Relevance | Confidence |
| --- | --- | --- |
| Ji, Z. (2023), "Survey," *ACM*, DOI: 10.1145/3571730 | hallucination | High |
"""
        refs = extract_references(text)
        assert len(refs) == 1
        assert refs[0].ref_id == "ji_2023"

    def test_extract_references_empty_document_returns_empty(self):
        refs = extract_references("")
        assert refs == []

    def test_extract_references_inline_citations_merged(self, real_md_text: str):
        refs = extract_references(real_md_text)
        kad = next((r for r in refs if r.ref_id == "kadavath_2022"), None)
        assert kad is not None
        assert len(kad.section_cited_in) > 1


# --- _parse_formal_reference ---


class TestParseFormalReference:
    def test_parse_formal_reference_with_doi(self):
        raw = 'Ji, Z., et al. (2023), "Survey of Hallucination," *ACM Surveys*, DOI: 10.1145/3571730'
        ref = _parse_formal_reference(raw, "hallucination rates", "High")
        assert ref is not None
        assert ref.ref_id == "ji_2023"
        assert ref.doi == "10.1145/3571730"
        assert ref.year == 2023
        assert "Hallucination" in ref.title
        assert ref.venue == "ACM Surveys"

    def test_parse_formal_reference_with_arxiv(self):
        raw = 'Kadavath, S. (2022), "Models Know," arXiv:2207.05221'
        ref = _parse_formal_reference(raw, "calibration", "Medium")
        assert ref is not None
        assert ref.arxiv_id == "2207.05221"
        assert ref.doi is None

    def test_parse_formal_reference_no_year_returns_none(self):
        raw = 'Some author, "No year here," *Journal*'
        ref = _parse_formal_reference(raw, "irrelevant", "Low")
        assert ref is None

    def test_parse_formal_reference_keyword_maps_to_error_class(self):
        raw = 'Author (2024), "On Sycophancy," *Conf*'
        ref = _parse_formal_reference(raw, "sycophancy in models", "High")
        assert ref is not None
        assert "ERR_SYCOPHANCY" in ref.error_classes_supported


# --- _extract_html_title ---


class TestExtractHtmlTitle:
    def test_extract_html_title_basic(self):
        html = "<html><head><title>My Paper Title</title></head></html>"
        assert _extract_html_title(html) == "My Paper Title"

    def test_extract_html_title_with_entities(self):
        html = "<title>Title&amp;More</title>"
        title = _extract_html_title(html)
        assert title is not None
        assert "Title" in title

    def test_extract_html_title_missing_returns_none(self):
        html = "<html><body>No title here</body></html>"
        assert _extract_html_title(html) is None

    def test_extract_html_title_multiline(self):
        html = "<title>\n  Multiline\n  Title\n</title>"
        title = _extract_html_title(html)
        assert title is not None
        assert "Multiline" in title


# --- _extract_meta_citation_title ---


class TestExtractMetaCitationTitle:
    def test_extract_meta_citation_title_found(self):
        html = '<meta name="citation_title" content="Formal Paper Title">'
        assert _extract_meta_citation_title(html) == "Formal Paper Title"

    def test_extract_meta_citation_title_missing(self):
        html = "<html><head></head></html>"
        assert _extract_meta_citation_title(html) is None


# --- _title_match ---


class TestTitleMatch:
    def test_title_match_identical_returns_high(self):
        score = _title_match("Survey of Hallucination", "Survey of Hallucination")
        assert score >= 0.9

    def test_title_match_partial_overlap(self):
        score = _title_match(
            "Survey of Hallucination in Natural Language Generation",
            "A Comprehensive Survey of Hallucination in NLG",
        )
        assert score > 0.3

    def test_title_match_no_overlap_returns_zero(self):
        score = _title_match("Quantum Computing", "Cat Food Reviews")
        assert score == 0.0

    def test_title_match_empty_inputs(self):
        assert _title_match("", "something") == 0.0
        assert _title_match("something", "") == 0.0
        assert _title_match("", "") == 0.0


# --- verify_references (mocked network) ---


class TestVerifyReferences:
    def test_verify_references_no_identifier_sets_status(self):
        ref = Reference(
            ref_id="test_2024", authors="Test", year=2024,
            title="Test", venue="Test",
        )
        result = verify_references([ref], quiet=True)
        assert result[0].verification_status == "no_identifier"

    @patch("pals_check.references._fetch_and_extract")
    def test_verify_references_doi_verified(self, mock_fetch):
        mock_fetch.return_value = {
            "status": "verified",
            "url": "https://doi.org/10.1234/test",
            "fetched_title": "Test Paper",
            "match_quality": 0.9,
        }
        ref = Reference(
            ref_id="test_2024", authors="Test", year=2024,
            title="Test Paper", venue="Test", doi="10.1234/test",
        )
        result = verify_references([ref], quiet=True)
        assert result[0].verification_status == "verified"
        assert result[0].fetched_title == "Test Paper"

    @patch("pals_check.references._fetch_and_extract")
    def test_verify_references_doi_unreachable_falls_back_to_arxiv(self, mock_fetch):
        mock_fetch.side_effect = [
            {"status": "unreachable", "url": "https://doi.org/10.1234/test", "error": "HTTP 403: Forbidden"},
            {"status": "verified", "url": "https://arxiv.org/abs/2207.05221", "fetched_title": "Fallback"},
        ]
        ref = Reference(
            ref_id="test_2024", authors="Test", year=2024,
            title="Test", venue="Test", doi="10.1234/test", arxiv_id="2207.05221",
        )
        result = verify_references([ref], quiet=True)
        assert result[0].verification_status == "verified"

    @patch("pals_check.references._fetch_and_extract")
    def test_verify_references_doi_403_no_arxiv_sets_partial(self, mock_fetch):
        mock_fetch.return_value = {
            "status": "unreachable", "url": "https://doi.org/x", "error": "HTTP 403: Forbidden",
        }
        ref = Reference(
            ref_id="test_2024", authors="Test", year=2024,
            title="Test", venue="Test", doi="10.1234/test",
        )
        result = verify_references([ref], quiet=True)
        assert result[0].verification_status == "partial"
