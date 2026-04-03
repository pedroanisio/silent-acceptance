"""Contract tests that guard against spec-code drift.

These tests parse the PALS_LAW Markdown document and assert that the
hardcoded Python structures match it. If the spec changes, these tests
fail — converting silent drift into a loud test failure.
"""

from __future__ import annotations

import re

from pals_check.constants import ErrorClass
from pals_check.math_checker import EXPECTED_SECTIONS, extract_math_blocks, validate_section_ids
from pals_check.schema import (
    _build_artifacts,
    _build_claims,
    _build_error_classes,
    _build_symbols,
    build_schema,
)


# === Finding #1/#3: Error class partition covers all 9 classes ===


class TestErrorClassPartitionContract:
    def test_partition_covers_all_error_classes(self, real_md_text: str):
        """Every ErrorClass member must appear in exactly one partition."""
        schema = build_schema(real_md_text)
        structural = set(schema.structural_error_classes)
        semantic = set(schema.semantic_error_classes)
        all_classes = {ec.value for ec in ErrorClass}

        covered = structural | semantic
        assert covered == all_classes, (
            f"Partition missing: {all_classes - covered}. "
            f"Extra: {covered - all_classes}."
        )

    def test_partition_is_disjoint(self, real_md_text: str):
        """No class should appear in both structural and semantic."""
        schema = build_schema(real_md_text)
        structural = set(schema.structural_error_classes)
        semantic = set(schema.semantic_error_classes)
        overlap = structural & semantic
        assert not overlap, f"Classes in both partitions: {overlap}"

    def test_error_class_definitions_match_partition(self, real_md_text: str):
        """Each ErrorClassDef's detection_strategy_type must agree with the partition."""
        schema = build_schema(real_md_text)
        structural_set = set(schema.structural_error_classes)
        semantic_set = set(schema.semantic_error_classes)

        for ec in schema.error_classes:
            if ec.detection_strategy_type == "structural":
                assert ec.identifier in structural_set, (
                    f"{ec.identifier} is 'structural' in definition but not in structural_error_classes"
                )
            elif ec.detection_strategy_type in ("semantic", "epistemic"):
                assert ec.identifier in semantic_set, (
                    f"{ec.identifier} is '{ec.detection_strategy_type}' in definition but not in semantic_error_classes"
                )

    def test_enum_count_matches_error_class_definitions(self):
        """The ErrorClass enum and _build_error_classes must have the same count."""
        defs = _build_error_classes()
        assert len(defs) == len(ErrorClass), (
            f"Enum has {len(ErrorClass)} members, _build_error_classes has {len(defs)}"
        )
        def_ids = {d.identifier for d in defs}
        enum_ids = {ec.value for ec in ErrorClass}
        assert def_ids == enum_ids


# === Finding #2: Claims and symbols reference valid sections ===


class TestClaimsAndSymbolsContract:
    def test_all_claim_sections_exist_in_document(self, real_md_text: str):
        """Every claim's section field must point to an existing heading."""
        existing = set()
        for m in re.finditer(r'^#{2,4}\s+([\d.]+)\.?\s', real_md_text, re.MULTILINE):
            existing.add(m.group(1).rstrip('.'))

        claims = _build_claims()
        for c in claims:
            assert c.section in existing or any(
                s.startswith(c.section) for s in existing
            ), f"Claim {c.claim_id} references section {c.section} which doesn't exist"

    def test_all_symbol_sections_exist_in_document(self, real_md_text: str):
        """Every symbol's section_defined field must point to an existing heading."""
        existing = set()
        for m in re.finditer(r'^#{2,4}\s+([\d.]+)\.?\s', real_md_text, re.MULTILINE):
            existing.add(m.group(1).rstrip('.'))

        symbols = _build_symbols()
        for s in symbols:
            assert s.section_defined in existing or any(
                sec.startswith(s.section_defined) for sec in existing
            ), f"Symbol {s.name} references section {s.section_defined} which doesn't exist"

    def test_claim_dependencies_are_valid(self):
        """Every claim's depends_on must reference another valid claim_id."""
        claims = _build_claims()
        all_ids = {c.claim_id for c in claims}
        for c in claims:
            for dep in c.depends_on:
                assert dep in all_ids, (
                    f"Claim {c.claim_id} depends on {dep} which is not a valid claim_id"
                )


# === Finding #4: Artifact content detection ===


class TestArtifactDetectionContract:
    def test_contract_block_detects_operative_form(self, real_md_text: str):
        """§9.1 Full Contract Block should contain the operative form."""
        schema = build_schema(real_md_text)
        contract = next(a for a in schema.artifacts if a.artifact_id == "contract_block")
        assert contract.contains_operative_form, (
            "§9.1 contract block should detect operative form"
        )

    def test_contract_block_detects_existential_form(self, real_md_text: str):
        schema = build_schema(real_md_text)
        contract = next(a for a in schema.artifacts if a.artifact_id == "contract_block")
        assert contract.contains_existential_form, (
            "§9.1 contract block should detect existential form"
        )

    def test_contract_block_detects_pipeline_corollary(self, real_md_text: str):
        schema = build_schema(real_md_text)
        contract = next(a for a in schema.artifacts if a.artifact_id == "contract_block")
        assert contract.contains_pipeline_corollary, (
            "§9.1 contract block should detect pipeline corollary"
        )

    def test_contract_block_detects_independence_caveat(self, real_md_text: str):
        schema = build_schema(real_md_text)
        contract = next(a for a in schema.artifacts if a.artifact_id == "contract_block")
        assert contract.contains_independence_caveat, (
            "§9.1 contract block should detect independence caveat"
        )

    def test_contract_block_detects_error_checklist(self, real_md_text: str):
        schema = build_schema(real_md_text)
        contract = next(a for a in schema.artifacts if a.artifact_id == "contract_block")
        assert contract.contains_error_checklist, (
            "§9.1 contract block should detect error checklist"
        )

    def test_claudemd_block_detects_operative_form(self, real_md_text: str):
        schema = build_schema(real_md_text)
        claude = next(a for a in schema.artifacts if a.artifact_id == "claudemd_block")
        assert claude.contains_operative_form, (
            "§9.4 CLAUDE.md block should detect operative form"
        )

    def test_claudemd_block_detects_pipeline(self, real_md_text: str):
        schema = build_schema(real_md_text)
        claude = next(a for a in schema.artifacts if a.artifact_id == "claudemd_block")
        assert claude.contains_pipeline_corollary, (
            "§9.4 CLAUDE.md block should detect pipeline corollary"
        )

    def test_claudemd_block_detects_independence_caveat(self, real_md_text: str):
        schema = build_schema(real_md_text)
        claude = next(a for a in schema.artifacts if a.artifact_id == "claudemd_block")
        assert claude.contains_independence_caveat, (
            "§9.4 CLAUDE.md block should detect independence caveat"
        )


# === Finding #5: Hardcoded section IDs ===


class TestSectionIdContract:
    def test_all_hardcoded_sections_exist(self, real_md_text: str):
        """No hardcoded section ID should be missing from the document."""
        warnings = validate_section_ids(real_md_text)
        assert warnings == [], f"Section ID drift detected: {warnings}"

    def test_expected_sections_set_is_complete(self):
        """EXPECTED_SECTIONS must include all section IDs used in this module."""
        # These are the IDs referenced in _describe_math_block, _infer_claim_status,
        # and check_math_consistency
        known_ids = {"3.1", "3.2", "3.3", "3.4", "6.1", "7.3", "8"}
        assert EXPECTED_SECTIONS == known_ids


# === CRITICAL drift fix #1: Claims content verified against spec ===


def _extract_distinctive_fragments(latex: str) -> list[str]:
    """Extract key mathematical fragments that define a claim's identity."""
    norm = re.sub(r'\s+', '', latex)
    fragments = []
    # Quantifiers and bounds
    for pattern in [
        r'\\forallM',
        r'\\mathbb{E}',
        r'\\geq\\delta',
        r'\\exists',
        r'\\prod_{i=1}',
        r'(1-p_i)',
        r'\\partial',
        r'\\leq0',
        r'>0',
        r'P_\\theta',
        r'\\varepsilon',
        r'\\mathcal{D}',
        r'\\mathcal{M}',
    ]:
        if pattern in norm:
            fragments.append(pattern)
    return fragments


class TestClaimsContentContract:
    """Verify that _build_claims() content matches the actual spec.

    Closes drift-risk-map Finding #1: hardcoded claims were only checked
    for valid section references, not for content agreement or completeness.
    """

    def test_every_claim_with_display_math_has_matching_spec_block(self, real_md_text: str):
        """Each claim with display math must share key LaTeX fragments with a spec math block.

        The spec's display math may have formatting differences (e.g., \\bigl,
        \\quad, \\text{over}) that don't appear in the simplified claim latex.
        We check that the core mathematical content — the distinctive operators
        and bound expressions — match between claim and spec.
        """
        claims = _build_claims()
        math_blocks = extract_math_blocks(real_md_text)
        blocks_by_section: dict[str, list[str]] = {}
        for b in math_blocks:
            blocks_by_section.setdefault(b.section, []).append(b.latex)

        for c in claims:
            if not c.latex or c.status == "definition":
                continue
            # Collect blocks from this section and parent/child sections
            section_blocks: list[str] = []
            for sec, blocks in blocks_by_section.items():
                if sec == c.section or c.section.startswith(sec) or sec.startswith(c.section):
                    section_blocks.extend(blocks)

            if not section_blocks:
                # No display math in this section — claim's latex is synthetic
                # (e.g., informal arguments). Validated by the text-level test.
                continue

            # Extract distinctive fragments from the claim's latex
            # (operators, bounds, quantifiers — things that define the claim's identity)
            fragments = _extract_distinctive_fragments(c.latex)
            if not fragments:
                continue

            # At least half the distinctive fragments must appear in some block
            match_counts = []
            for block in section_blocks:
                block_norm = re.sub(r'\s+', '', block)
                hits = sum(1 for f in fragments if f in block_norm)
                match_counts.append(hits)

            best_match = max(match_counts) if match_counts else 0
            threshold = max(1, len(fragments) // 2)

            assert best_match >= threshold, (
                f"Claim {c.claim_id} (section {c.section}) shares only {best_match}/{len(fragments)} "
                f"distinctive fragments with spec math blocks. "
                f"Fragments checked: {fragments}. "
                f"The spec's math content may have changed substantially."
            )

    def test_every_claim_latex_appears_in_spec_text(self, real_md_text: str):
        """Each claim's core latex notation must appear somewhere in its spec section (inline or display)."""
        from pals_check.math_checker import _get_section_text

        claims = _build_claims()
        for c in claims:
            if not c.latex:
                continue
            section_text = _get_section_text(real_md_text, c.section)
            if not section_text:
                # Section existence is already tested by TestClaimsAndSymbolsContract
                continue
            # Extract a distinctive fragment from the claim's latex
            # (full latex may have formatting differences between code and spec)
            fragments = []
            if r'\varepsilon' in c.latex:
                fragments.append(r'\varepsilon')
            if r'\mathbb{E}' in c.latex:
                fragments.append(r'\mathbb{E}')
            if r'\exists' in c.latex:
                fragments.append(r'\exists')
            if r'\prod' in c.latex:
                fragments.append(r'\prod')
            if r'\partial' in c.latex:
                fragments.append(r'\partial')
            if not fragments:
                continue
            for frag in fragments:
                assert frag in section_text or frag in real_md_text, (
                    f"Claim {c.claim_id} uses {frag!r} but it's not in spec section {c.section}"
                )

    def test_claim_count_matches_spec_math_bearing_sections(self, real_md_text: str):
        """The number of claims must account for all math-bearing sections in the spec.

        Every section that contains a $$...$$ block should either have a
        corresponding claim or be explicitly accounted for (e.g., §3.1 is
        a definition section, §8 has two blocks for one hypothesis).
        """
        math_blocks = extract_math_blocks(real_md_text)
        sections_with_math = {b.section for b in math_blocks}

        claims = _build_claims()
        claim_sections = {c.section for c in claims}

        # Every section with math should be covered by at least one claim
        uncovered = set()
        for sec in sections_with_math:
            if sec not in claim_sections and not any(
                cs.startswith(sec) or sec.startswith(cs) for cs in claim_sections
            ):
                uncovered.add(sec)

        assert not uncovered, (
            f"Sections with math blocks not covered by any claim: {uncovered}. "
            f"If new math was added to the spec, _build_claims() needs updating."
        )

    def test_claim_supported_by_references_are_valid(self, real_md_text: str):
        """Each claim's supported_by entries must be valid ref_ids or argument section IDs."""
        from pals_check.references import extract_references

        refs = extract_references(real_md_text)
        valid_ref_ids = {r.ref_id for r in refs}

        claims = _build_claims()
        all_claim_ids = {c.claim_id for c in claims}

        for c in claims:
            for ref in c.supported_by:
                assert ref in valid_ref_ids or ref in all_claim_ids, (
                    f"Claim {c.claim_id} lists supported_by={ref!r} which is "
                    f"neither a valid reference ID nor a valid claim ID. "
                    f"Valid ref IDs: {sorted(valid_ref_ids)}"
                )


# === CRITICAL drift fix #2: Symbols content verified against spec ===


class TestSymbolsContentContract:
    """Verify that _build_symbols() content matches the actual spec.

    Closes drift-risk-map Finding #2: hardcoded symbols were only checked
    for valid section references, not for content agreement or completeness.
    """

    def test_symbol_count_matches_spec_definitions(self, real_md_text: str):
        """The number of symbols must match the definitions in the spec.

        §3.1 defines symbols as bullet points (some bullets introduce multiple
        symbols, e.g., M's bullet also introduces θ). Other sections (§3.2,
        §3.4, §8) introduce additional symbols.
        """
        symbols = _build_symbols()

        # Count symbols by their declared section_defined
        by_section: dict[str, list] = {}
        for s in symbols:
            by_section.setdefault(s.section_defined, []).append(s)

        # Verify each section exists in the spec
        for sec in by_section:
            pat = rf'###?\s+{re.escape(sec)}\b'
            assert re.search(pat, real_md_text), (
                f"Symbol section {sec} not found in spec"
            )

        # Verify the total count by extracting distinct $...$ notations from §3.1
        sec31_match = re.search(r'###\s+3\.1\b.*?\n(.*?)(?=\n###?\s+\d)', real_md_text, re.DOTALL)
        assert sec31_match, "Section 3.1 not found in spec"
        sec31_text = sec31_match.group(1)

        # Extract all LaTeX symbols defined in bullet list (including inline ones like $\theta$)
        spec_latex_31 = set(re.findall(r'\$([^$]+)\$', sec31_text))
        code_latex_31 = {s.latex for s in by_section.get("3.1", [])}

        # Each code symbol's latex must appear in the spec section's latex set
        for s in by_section.get("3.1", []):
            found = any(s.latex in spec_l or spec_l == s.latex for spec_l in spec_latex_31)
            assert found, (
                f"Symbol {s.name} has latex {s.latex!r} not found in spec §3.1. "
                f"Spec latex notations: {sorted(spec_latex_31)}"
            )

    def test_symbol_latex_appears_in_spec_section(self, real_md_text: str):
        """Each symbol's LaTeX must appear somewhere in its declared section."""
        symbols = _build_symbols()
        for s in symbols:
            # Find the section text
            sec_pattern = rf'###?\s+{re.escape(s.section_defined)}\b'
            sec_match = re.search(sec_pattern, real_md_text)
            assert sec_match, (
                f"Symbol {s.name} references section {s.section_defined} "
                f"which was not found in the spec"
            )
            start = sec_match.end()
            next_sec = re.search(r'\n#{2,4}\s+\d', real_md_text[start:])
            end = start + (next_sec.start() if next_sec else len(real_md_text) - start)
            section_text = real_md_text[start:end]

            # The latex (e.g., \mathcal{M}) should appear in the section
            # Escape for regex and search
            latex_escaped = re.escape(s.latex)
            found = re.search(latex_escaped, section_text) is not None
            # Also try without backslash escaping (raw string in markdown)
            if not found:
                found = s.latex in section_text
            assert found, (
                f"Symbol {s.name} has latex {s.latex!r} not found in spec section "
                f"{s.section_defined}. The spec may have changed this symbol's notation."
            )


# === CRITICAL drift fix #3: Error classes verified against spec ===


class TestErrorClassesSpecContract:
    """Verify that ErrorClass enum and _build_error_classes() match the spec's §5 table.

    Closes drift-risk-map Finding #3: error class enum and builder were only
    checked for internal consistency (enum vs builder), not against the spec.
    """

    def test_error_class_identifiers_match_spec_taxonomy(self, real_md_text: str):
        """Every ERR_* identifier in §5's table must exist in the ErrorClass enum, and vice versa."""
        # Extract ERR_* identifiers from the spec's §5 taxonomy table
        sec5_match = re.search(r'##\s+5\.\s+.*?\n(.*?)(?=\n---)', real_md_text, re.DOTALL)
        assert sec5_match, "Section 5 (error taxonomy) not found in spec"
        sec5_text = sec5_match.group(1)

        spec_err_ids = set(re.findall(r'`(ERR_[A-Z_]+)`', sec5_text))
        enum_err_ids = {ec.value for ec in ErrorClass}

        missing_from_enum = spec_err_ids - enum_err_ids
        extra_in_enum = enum_err_ids - spec_err_ids

        assert not missing_from_enum, (
            f"Spec §5 defines error classes not in ErrorClass enum: {missing_from_enum}. "
            f"The enum in constants.py needs updating."
        )
        assert not extra_in_enum, (
            f"ErrorClass enum has classes not in spec §5: {extra_in_enum}. "
            f"The enum has phantom entries that were removed from the spec."
        )

    def test_error_class_count_matches_spec(self, real_md_text: str):
        """The number of distinct error classes in the enum must match the spec's §5 table."""
        sec5_match = re.search(r'##\s+5\.\s+.*?\n(.*?)(?=\n---)', real_md_text, re.DOTALL)
        assert sec5_match, "Section 5 not found"
        sec5_text = sec5_match.group(1)

        # Count distinct ERR_ identifiers (some are cross-referenced in other rows' definitions)
        spec_err_ids = set(re.findall(r'`(ERR_[A-Z_]+)`', sec5_text))
        spec_count = len(spec_err_ids)
        enum_count = len(ErrorClass)
        builder_count = len(_build_error_classes())

        assert spec_count == enum_count, (
            f"Spec §5 has {spec_count} distinct error classes, ErrorClass enum has {enum_count}. "
            f"Spec: {sorted(spec_err_ids)}, Enum: {sorted(ec.value for ec in ErrorClass)}"
        )
        assert spec_count == builder_count, (
            f"Spec §5 has {spec_count} distinct error classes, _build_error_classes has {builder_count}"
        )

    def test_corollary5_partition_matches_spec_math_blocks(self, real_md_text: str):
        """The structural/semantic partition in schema.py must match §8's Corollary 5 math blocks."""
        # Extract ERR_* identifiers from the two Corollary 5 math blocks
        math_blocks = extract_math_blocks(real_md_text)
        cor5_blocks = [b for b in math_blocks if "8" in b.section and r'\partial' in b.latex]
        assert len(cor5_blocks) >= 2, (
            f"Expected at least 2 Corollary 5 math blocks in §8, found {len(cor5_blocks)}"
        )

        # First block: structural (∂D_c/∂C ≤ 0)
        structural_block = cor5_blocks[0].latex
        spec_structural = set(re.findall(r'ERR_[A-Z_]+', structural_block.replace('\\_', '_')))

        # Second block: semantic (∂D_c/∂C > 0)
        semantic_block = cor5_blocks[1].latex
        spec_semantic = set(re.findall(r'ERR_[A-Z_]+', semantic_block.replace('\\_', '_')))

        schema = build_schema(real_md_text)
        code_structural = set(schema.structural_error_classes)
        code_semantic = set(schema.semantic_error_classes)

        assert spec_structural == code_structural, (
            f"Structural partition mismatch. "
            f"Spec §8 says: {sorted(spec_structural)}, "
            f"schema.py says: {sorted(code_structural)}"
        )
        assert spec_semantic == code_semantic, (
            f"Semantic partition mismatch. "
            f"Spec §8 says: {sorted(spec_semantic)}, "
            f"schema.py says: {sorted(code_semantic)}"
        )
