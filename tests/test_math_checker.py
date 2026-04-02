"""Tests for pals_check.math_checker — math block extraction and consistency checks."""

from __future__ import annotations

from pals_check.math_checker import (
    MathBlock,
    _describe_math_block,
    _get_section_text,
    _infer_claim_status,
    check_math_consistency,
    extract_math_blocks,
)


# --- extract_math_blocks ---


class TestExtractMathBlocks:
    def test_extract_math_blocks_from_minimal_doc(self, minimal_md_text: str):
        blocks = extract_math_blocks(minimal_md_text)
        assert len(blocks) >= 4  # 3.1, 3.2, 3.3, and two 3.4 blocks, 6.1, two 8 blocks

    def test_extract_math_blocks_section_tracking(self, minimal_md_text: str):
        blocks = extract_math_blocks(minimal_md_text)
        sections = {b.section for b in blocks}
        assert "3.2" in sections
        assert "3.3" in sections

    def test_extract_math_blocks_assigns_block_id(self, minimal_md_text: str):
        blocks = extract_math_blocks(minimal_md_text)
        for b in blocks:
            assert b.block_id.startswith("math_")

    def test_extract_math_blocks_empty_document(self):
        blocks = extract_math_blocks("")
        assert blocks == []

    def test_extract_math_blocks_no_math(self):
        text = "## 1. Section\n\nJust plain text.\n"
        blocks = extract_math_blocks(text)
        assert blocks == []

    def test_extract_math_blocks_preserves_latex(self, minimal_md_text: str):
        blocks = extract_math_blocks(minimal_md_text)
        operative = [b for b in blocks if b.section == "3.2"]
        assert len(operative) == 1
        assert r"\forall M" in operative[0].latex
        assert r"\mathbb{E}" in operative[0].latex


# --- _describe_math_block ---


class TestDescribeMathBlock:
    def test_describe_operative_section(self):
        desc = _describe_math_block(r"\forall M", "3.2")
        assert "Operative" in desc

    def test_describe_existential_section(self):
        desc = _describe_math_block(r"\exists x", "3.3")
        assert "Existential" in desc

    def test_describe_product_formula(self):
        desc = _describe_math_block(r"\prod_{i=1}^{n}", "99")
        assert "Product" in desc

    def test_describe_partial_derivative(self):
        desc = _describe_math_block(r"\partial D", "99")
        assert "Partial derivative" in desc or "derivative" in desc.lower()

    def test_describe_generic_fallback(self):
        desc = _describe_math_block(r"x + y = z", "99")
        assert desc == "Mathematical expression"


# --- _infer_claim_status ---


class TestInferClaimStatus:
    def test_infer_operative(self):
        assert _infer_claim_status("3.2", "") == "operative"

    def test_infer_existential(self):
        assert _infer_claim_status("3.3", "") == "existential"

    def test_infer_pipeline_corollary(self):
        assert _infer_claim_status("3.4", "") == "corollary"

    def test_infer_informal_arg(self):
        assert _infer_claim_status("6.1", "") == "informal_arg"

    def test_infer_hypothesis_from_section_8(self):
        # _get_section_text must find the section for hypothesis keyword detection
        text = "## 8 Corollaries\n\nThis is a hypothesis about detection.\n## 9 Next\n"
        assert _infer_claim_status("8", text) == "hypothesis"

    def test_infer_definition(self):
        assert _infer_claim_status("3.1", "") == "definition"

    def test_infer_unclassified(self):
        assert _infer_claim_status("99", "") == "unclassified"


# --- _get_section_text ---


class TestGetSectionText:
    def test_get_section_text_found(self, real_md_text: str):
        sec = _get_section_text(real_md_text, "3.2")
        assert len(sec) > 0

    def test_get_section_text_not_found(self, minimal_md_text: str):
        sec = _get_section_text(minimal_md_text, "99.99")
        assert sec == ""


# --- check_math_consistency ---


class TestCheckMathConsistency:
    def test_check_math_consistency_returns_checks(self, minimal_md_text: str):
        blocks = extract_math_blocks(minimal_md_text)
        checks = check_math_consistency(blocks, minimal_md_text)
        assert len(checks) > 0

    def test_check_operative_structure_passes(self, minimal_md_text: str):
        blocks = extract_math_blocks(minimal_md_text)
        checks = check_math_consistency(blocks, minimal_md_text)
        op_check = next((c for c in checks if c.check_id == "CHK_OPERATIVE_STRUCTURE"), None)
        assert op_check is not None
        assert op_check.status == "pass"

    def test_check_existential_weaker_passes(self, minimal_md_text: str):
        blocks = extract_math_blocks(minimal_md_text)
        checks = check_math_consistency(blocks, minimal_md_text)
        ex_check = next((c for c in checks if c.check_id == "CHK_EXISTENTIAL_WEAKER"), None)
        assert ex_check is not None
        assert ex_check.status == "pass"

    def test_check_pipeline_algebra(self, minimal_md_text: str):
        blocks = extract_math_blocks(minimal_md_text)
        checks = check_math_consistency(blocks, minimal_md_text)
        pipe_check = next((c for c in checks if c.check_id == "CHK_PIPELINE_ALGEBRA"), None)
        assert pipe_check is not None

    def test_check_cross_references_present(self, minimal_md_text: str):
        blocks = extract_math_blocks(minimal_md_text)
        checks = check_math_consistency(blocks, minimal_md_text)
        xref_check = next((c for c in checks if c.check_id == "CHK_CROSS_REFERENCES"), None)
        assert xref_check is not None

    def test_check_epsilon_domain_always_passes(self, minimal_md_text: str):
        blocks = extract_math_blocks(minimal_md_text)
        checks = check_math_consistency(blocks, minimal_md_text)
        eps_check = next((c for c in checks if c.check_id == "CHK_EPSILON_DOMAIN"), None)
        assert eps_check is not None
        assert eps_check.status == "pass"

    def test_check_all_check_ids_unique(self, minimal_md_text: str):
        blocks = extract_math_blocks(minimal_md_text)
        checks = check_math_consistency(blocks, minimal_md_text)
        ids = [c.check_id for c in checks]
        assert len(ids) == len(set(ids))

    def test_check_all_statuses_valid(self, minimal_md_text: str):
        blocks = extract_math_blocks(minimal_md_text)
        checks = check_math_consistency(blocks, minimal_md_text)
        valid_statuses = {"pass", "fail", "warn", "info"}
        for c in checks:
            assert c.status in valid_statuses, f"{c.check_id} has invalid status: {c.status}"
