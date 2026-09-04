"""Regression tests for bugs identified in the drift-risk review.

Each test is named after the specific bug it guards against, with a
docstring explaining what was broken and how.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from pals_check.constants import ErrorClass, SpecLayout
from pals_check.math_checker import (
    _get_section_text,
    asymmetry_blocks,
    check_math_consistency,
    extract_math_blocks,
)
from pals_check.references import (
    _fetch_and_extract,
    _parse_formal_reference,
    extract_references,
)
from pals_check.schema import (
    _build_artifacts,
    _build_error_classes,
    build_schema,
)

# =====================================================================
# Regression: _get_section_text f-string quantifier bug
# Root cause: rf'^#{2,4}\s+...' in f-string evaluates {2,4} as tuple
# Fix: Use escaped braces rf'^#{{2,4}}\s+...'
# =====================================================================


class TestGetSectionTextFStringRegression:
    """Guard against the f-string quantifier bug in _get_section_text.

    The original code used rf'^#{2,4}\\s+{esc}\\s' which Python f-string
    formatting evaluates as '^#(2, 4)\\s+...' — a broken regex that never
    matches any Markdown heading. This caused _get_section_text to always
    return empty strings.
    """

    def test_finds_h2_section(self):
        """_get_section_text must match ## headings (2 hashes)."""
        text = "## 3.2 Operative Form\n\nContent here.\n\n## 3.3 Next"
        result = _get_section_text(text, "3.2")
        assert "Content here" in result

    def test_finds_h3_section(self):
        """_get_section_text must match ### headings (3 hashes)."""
        text = "### 9.1 Full Contract Block\n\nERR_HALLUCINATION\n\n### 9.2 Short"
        result = _get_section_text(text, "9.1")
        assert "ERR_HALLUCINATION" in result

    def test_finds_h4_section(self):
        """_get_section_text must match #### headings (4 hashes)."""
        text = "#### 4.1 Theoretical Foundations\n\nKalai & Vempala\n\n#### 4.2 Next"
        result = _get_section_text(text, "4.1")
        assert "Kalai" in result

    def test_does_not_match_h1_or_h5(self):
        """_get_section_text should NOT match # (h1) or ##### (h5)."""
        text_h1 = "# 1.0 Title\n\nContent\n\n## 2.0 Next"
        text_h5 = "##### 1.0 Deep\n\nContent\n\n## 2.0 Next"
        assert _get_section_text(text_h1, "1.0") == ""
        assert _get_section_text(text_h5, "1.0") == ""

    def test_real_document_contract_section(self, spec_doc: tuple[str, SpecLayout]):
        """The contract-block section must return non-empty text containing ERR_HALLUCINATION."""
        text, layout = spec_doc
        section = layout.artifacts[0].section
        result = _get_section_text(text, section)
        assert len(result) > 0, f"_get_section_text returned empty for §{section}"
        assert "ERR_HALLUCINATION" in result

    def test_real_document_repository_section(self, spec_doc: tuple[str, SpecLayout]):
        """The repository-block section must return non-empty text containing pipeline language."""
        text, layout = spec_doc
        section = layout.artifacts[3].section
        result = _get_section_text(text, section)
        assert len(result) > 0, f"_get_section_text returned empty for §{section}"
        assert "pipeline" in result.lower()


# =====================================================================
# Regression: _build_artifacts all-false flags
# Root cause: _get_section_text always returned "" (f-string bug above)
# Fix: f-string fix + robust multi-strategy detection helpers
# =====================================================================


class TestArtifactFlagsRegression:
    """Guard against artifact content detection returning all-false flags.

    Previously all five boolean flags were False for every artifact because
    _get_section_text returned empty strings. After the fix, the flags must
    correctly reflect the actual content of each §9 subsection.
    """

    def test_contract_block_all_flags_true(self, spec_doc: tuple[str, SpecLayout]):
        """The contract block must detect all five content types."""
        text, layout = spec_doc
        artifacts = _build_artifacts(text, layout)
        contract = next(a for a in artifacts if a.artifact_id == "contract_block")
        assert contract.contains_operative_form
        assert contract.contains_existential_form
        assert contract.contains_pipeline_corollary
        assert contract.contains_independence_caveat
        assert contract.contains_error_checklist

    def test_short_form_operative_true(self, spec_doc: tuple[str, SpecLayout]):
        """The short form must detect the operative form (non-negligible)."""
        text, layout = spec_doc
        artifacts = _build_artifacts(text, layout)
        short = next(a for a in artifacts if a.artifact_id == "short_form")
        assert short.contains_operative_form

    def test_repository_block_flags(self, spec_doc: tuple[str, SpecLayout]):
        """The repository block (CLAUDE.md / agent file) must detect operative, pipeline, independence."""
        text, layout = spec_doc
        artifacts = _build_artifacts(text, layout)
        repo_block = next(a for a in artifacts if a.artifact_id == layout.artifacts[3].artifact_id)
        assert repo_block.contains_operative_form
        assert repo_block.contains_pipeline_corollary
        assert repo_block.contains_independence_caveat

    def test_not_all_false(self, spec_doc: tuple[str, SpecLayout]):
        """At least one artifact must have at least one True flag."""
        text, layout = spec_doc
        artifacts = _build_artifacts(text, layout)
        any_true = any(
            a.contains_operative_form
            or a.contains_existential_form
            or a.contains_pipeline_corollary
            or a.contains_independence_caveat
            or a.contains_error_checklist
            for a in artifacts
        )
        assert any_true, "All artifact flags are False — detection is broken"


# =====================================================================
# Regression: Corollary 5 partition missing ERR_OMISSION + ERR_CALIBRATION
# Root cause: Spec §8 math blocks listed only 7/9 classes; Python
# expected sets also had only 7. Schema partition had only 7.
# Fix: Added both classes to spec math, expected sets, and partition.
# =====================================================================


class TestCorollary5PartitionRegression:
    """Guard against error classes being orphaned from the Cor.5 partition."""

    def test_all_nine_classes_in_partition(self, spec_doc: tuple[str, SpecLayout]):
        """structural ∪ semantic must equal all ErrorClass members."""
        text, layout = spec_doc
        schema = build_schema(text, layout)
        structural = set(schema.structural_error_classes)
        semantic = set(schema.semantic_error_classes)
        all_classes = {ec.value for ec in ErrorClass}
        assert structural | semantic == all_classes

    def test_err_omission_in_partition(self, spec_doc: tuple[str, SpecLayout]):
        """ERR_OMISSION must be classified (was orphaned before fix)."""
        text, layout = spec_doc
        schema = build_schema(text, layout)
        all_in_partition = set(schema.structural_error_classes) | set(schema.semantic_error_classes)
        assert "ERR_OMISSION" in all_in_partition

    def test_err_calibration_in_partition(self, spec_doc: tuple[str, SpecLayout]):
        """ERR_CALIBRATION must be classified (was orphaned before fix)."""
        text, layout = spec_doc
        schema = build_schema(text, layout)
        all_in_partition = set(schema.structural_error_classes) | set(schema.semantic_error_classes)
        assert "ERR_CALIBRATION" in all_in_partition

    def test_spec_math_blocks_cover_all_classes(self, spec_doc: tuple[str, SpecLayout]):
        """The actual asymmetry LaTeX must mention all 9 error classes."""
        text, layout = spec_doc
        cor5_blocks = asymmetry_blocks(extract_math_blocks(text, layout), layout)
        assert len(cor5_blocks) >= 2, "Expected at least 2 asymmetry math blocks"

        all_found: set[str] = set()
        for b in cor5_blocks:
            for ec in ErrorClass:
                esc_name = ec.value.replace("ERR_", "ERR\\_")
                if esc_name in b.latex:
                    all_found.add(ec.value)

        expected = {ec.value for ec in ErrorClass}
        assert all_found == expected, f"Spec math blocks missing: {expected - all_found}"

    def test_chk_cor5_signs_passes(self, spec_doc: tuple[str, SpecLayout]):
        """CHK_COR5_SIGNS must pass (not warn) now that all classes are present."""
        text, layout = spec_doc
        blocks = extract_math_blocks(text, layout)
        checks = check_math_consistency(blocks, text, layout)
        cor5 = next(c for c in checks if c.check_id == "CHK_COR5_SIGNS")
        assert cor5.status == "pass", f"CHK_COR5_SIGNS status: {cor5.status}, detail: {cor5.detail}"

    def test_chk_cor5_coverage_complete(self, spec_doc: tuple[str, SpecLayout]):
        """The coverage_complete flag in CHK_COR5_SIGNS detail must be True."""
        text, layout = spec_doc
        blocks = extract_math_blocks(text, layout)
        checks = check_math_consistency(blocks, text, layout)
        cor5 = next(c for c in checks if c.check_id == "CHK_COR5_SIGNS")
        detail = json.loads(cor5.detail)
        assert detail["coverage_complete"] is True


# =====================================================================
# Regression: _extract_meta_citation_title defined but never called
# Fix: Wired as fallback when _extract_html_title returns None
# =====================================================================


class TestMetaCitationTitleFallbackRegression:
    """Guard against _extract_meta_citation_title being unused."""

    def test_fallback_to_meta_citation_title(self):
        """When <title> is absent, citation_title meta tag should be used."""
        html_no_title = (
            "<html><head>"
            '<meta name="citation_title" content="Calibrated LMs Must Hallucinate">'
            "</head><body>content</body></html>"
        )
        ref = MagicMock()
        ref.title = "Calibrated Language Models Must Hallucinate"
        ref.arxiv_id = None

        with patch("pals_check.references.urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.url = "https://example.com/paper"
            mock_resp.headers = {"Content-Type": "text/html; charset=utf-8"}
            mock_resp.read.return_value = html_no_title.encode("utf-8")
            mock_resp.__enter__ = lambda self: self
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            result = _fetch_and_extract("https://example.com/paper", ref)

        assert result["fetched_title"] is not None
        assert "Calibrated" in result["fetched_title"]


# =====================================================================
# Regression: arxiv_id trailing period not cleaned during extraction
# Root cause: regex r'arXiv:([\d.]+)' captures trailing '.' from
# "arXiv:2109.07958." — only cleaned at fetch time, not at parse time
# Fix: Added .rstrip('.') during extraction
# =====================================================================


class TestArxivIdTrailingPeriodRegression:
    """Guard against arxiv_id having a trailing period in stored data."""

    def test_arxiv_id_no_trailing_period(self):
        """Parsed arxiv_id must not end with a period."""
        raw = 'Lin, S., et al. (2022). "TruthfulQA." *ACL 2022*. arXiv:2109.07958.'
        ref = _parse_formal_reference(raw, "benchmark", "High confidence.")
        assert ref is not None
        assert ref.arxiv_id == "2109.07958"
        assert not ref.arxiv_id.endswith(".")

    def test_arxiv_id_clean_in_real_doc(self, spec_doc: tuple[str, SpecLayout]):
        """All extracted references must have clean arxiv_ids."""
        text, _ = spec_doc
        refs = extract_references(text)
        for ref in refs:
            if ref.arxiv_id:
                assert not ref.arxiv_id.endswith("."), (
                    f"Reference {ref.ref_id} has trailing period in arxiv_id: {ref.arxiv_id}"
                )


# =====================================================================
# Regression: CHK_COR5_SIGNS passed on signs alone without checking
# that all expected error classes are actually present in the spec math
# Fix: Added coverage_ok check — status is "warn" if signs are correct
# but found classes don't match expected classes
# =====================================================================


class TestCor5CoverageCheckRegression:
    """Guard against CHK_COR5_SIGNS silently passing with incomplete coverage."""

    def test_incomplete_coverage_produces_warn(self):
        """If spec only lists 7/9 classes, check should be 'warn' not 'pass'."""
        # This synthetic doc has only 3+4=7 classes (missing OMISSION, CALIBRATION)
        text = """\
## 8. Corollaries

Hypothesis about detection difficulty:

$$
\\frac{\\partial D_c}{\\partial C} \\leq 0
\\quad \\text{for } c \\in \\bigl\\{\\texttt{ERR\\_SCHEMA},\\ \\texttt{ERR\\_TRUNCATION},\\ \\texttt{ERR\\_INSTRUCTION}\\bigr\\}
$$

$$
\\frac{\\partial D_c}{\\partial C} > 0
\\quad \\text{for } c \\in \\bigl\\{\\texttt{ERR\\_HALLUCINATION},\\ \\texttt{ERR\\_SEMANTIC},\\ \\texttt{ERR\\_SYCOPHANCY},\\ \\texttt{ERR\\_REASONING}\\bigr\\}
$$
"""
        blocks = extract_math_blocks(text)
        checks = check_math_consistency(blocks, text)
        cor5 = next((c for c in checks if c.check_id == "CHK_COR5_SIGNS"), None)
        assert cor5 is not None
        assert cor5.status == "warn", f"Expected 'warn' for incomplete coverage, got '{cor5.status}'"
        detail = json.loads(cor5.detail)
        assert detail["coverage_complete"] is False

    def test_complete_coverage_produces_pass(self):
        """If spec lists all 9 classes, check should be 'pass'."""
        text = """\
## 8. Corollaries

Hypothesis about detection difficulty:

$$
\\frac{\\partial D_c}{\\partial C} \\leq 0
\\quad \\text{for } c \\in \\bigl\\{\\texttt{ERR\\_OMISSION},\\ \\texttt{ERR\\_SCHEMA},\\ \\texttt{ERR\\_TRUNCATION},\\ \\texttt{ERR\\_INSTRUCTION}\\bigr\\}
$$

$$
\\frac{\\partial D_c}{\\partial C} > 0
\\quad \\text{for } c \\in \\bigl\\{\\texttt{ERR\\_HALLUCINATION},\\ \\texttt{ERR\\_SEMANTIC},\\ \\texttt{ERR\\_SYCOPHANCY},\\ \\texttt{ERR\\_CALIBRATION},\\ \\texttt{ERR\\_REASONING}\\bigr\\}
$$
"""
        blocks = extract_math_blocks(text)
        checks = check_math_consistency(blocks, text)
        cor5 = next((c for c in checks if c.check_id == "CHK_COR5_SIGNS"), None)
        assert cor5 is not None
        assert cor5.status == "pass"
        detail = json.loads(cor5.detail)
        assert detail["coverage_complete"] is True


# =====================================================================
# Regression: ErrorClassDef.detection_strategy_type must agree with
# the schema partition (structural vs semantic)
# =====================================================================


class TestErrorClassDefPartitionAgreement:
    """Guard against ErrorClassDef type disagreeing with schema partition."""

    def test_structural_defs_have_leq_0_sign(self):
        """All structural error classes must have corollary5_sign 'leq_0'."""
        defs = _build_error_classes()
        schema = build_schema(
            "**Document version:** 0.0.1\n## 9. Artifacts\n### 9.1 A\ntest\n### 9.2 B\ntest\n### 9.3 C\ntest\n### 9.4 D\ntest"
        )
        structural_set = set(schema.structural_error_classes)
        for ec in defs:
            if ec.identifier in structural_set:
                assert ec.corollary5_sign == "leq_0", (
                    f"{ec.identifier} is structural but has sign '{ec.corollary5_sign}'"
                )

    def test_semantic_defs_have_gt_0_sign(self):
        """All semantic error classes must have corollary5_sign 'gt_0'."""
        defs = _build_error_classes()
        schema = build_schema(
            "**Document version:** 0.0.1\n## 9. Artifacts\n### 9.1 A\ntest\n### 9.2 B\ntest\n### 9.3 C\ntest\n### 9.4 D\ntest"
        )
        semantic_set = set(schema.semantic_error_classes)
        for ec in defs:
            if ec.identifier in semantic_set:
                assert ec.corollary5_sign == "gt_0", f"{ec.identifier} is semantic but has sign '{ec.corollary5_sign}'"
