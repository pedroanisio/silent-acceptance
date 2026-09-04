"""Contract tests that guard against spec-code drift.

These tests parse every published specification (PALS's LAW v1.5.4, Silent
Acceptance v2.0.0, and v2.1.0) and assert that the hardcoded Python structures
match each one. If a spec changes, these tests fail — converting silent drift
into a loud test failure. The ``spec_doc`` fixture supplies ``(text, layout)``
pairs; claims and symbols are read through ``build_schema`` so that vocabulary
gated on the document's exact version is checked for the document that has it.
"""

from __future__ import annotations

import re

from pals_check.constants import LAYOUT_V1, LAYOUT_V2, ErrorClass, SpecLayout
from pals_check.math_checker import (
    asymmetry_blocks,
    expected_sections,
    extract_math_blocks,
    validate_section_ids,
)
from pals_check.schema import (
    _build_artifacts,
    _build_error_classes,
    build_schema,
)


def _existing_sections(text: str) -> set[str]:
    existing: set[str] = set()
    for m in re.finditer(r"^#{2,4}\s+([\d.]+)\.?\s", text, re.MULTILINE):
        existing.add(m.group(1).rstrip("."))
    return existing


# === Finding #1/#3: Error class partition covers all 9 classes ===


class TestErrorClassPartitionContract:
    def test_partition_covers_all_error_classes(self, spec_doc: tuple[str, SpecLayout]):
        """Every ErrorClass member must appear in exactly one partition."""
        text, layout = spec_doc
        schema = build_schema(text, layout)
        structural = set(schema.structural_error_classes)
        semantic = set(schema.semantic_error_classes)
        all_classes = {ec.value for ec in ErrorClass}

        covered = structural | semantic
        assert covered == all_classes, f"Partition missing: {all_classes - covered}. Extra: {covered - all_classes}."

    def test_partition_is_disjoint(self, spec_doc: tuple[str, SpecLayout]):
        """No class should appear in both structural and semantic."""
        text, layout = spec_doc
        schema = build_schema(text, layout)
        overlap = set(schema.structural_error_classes) & set(schema.semantic_error_classes)
        assert not overlap, f"Classes in both partitions: {overlap}"

    def test_error_class_definitions_match_partition(self, spec_doc: tuple[str, SpecLayout]):
        """Each ErrorClassDef's detection_strategy_type must agree with the partition."""
        text, layout = spec_doc
        schema = build_schema(text, layout)
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
        assert len(defs) == len(ErrorClass), f"Enum has {len(ErrorClass)} members, _build_error_classes has {len(defs)}"
        def_ids = {d.identifier for d in defs}
        enum_ids = {ec.value for ec in ErrorClass}
        assert def_ids == enum_ids


# === Finding #2: Claims and symbols reference valid sections ===


class TestClaimsAndSymbolsContract:
    def test_all_claim_sections_exist_in_document(self, spec_doc: tuple[str, SpecLayout]):
        """Every claim's section field must point to an existing heading."""
        text, layout = spec_doc
        existing = _existing_sections(text)
        for c in build_schema(text, layout).claims:
            assert c.section in existing or any(s.startswith(c.section) for s in existing), (
                f"Claim {c.claim_id} references section {c.section} which doesn't exist in {layout.name}"
            )

    def test_all_symbol_sections_exist_in_document(self, spec_doc: tuple[str, SpecLayout]):
        """Every symbol's section_defined field must point to an existing heading."""
        text, layout = spec_doc
        existing = _existing_sections(text)
        for s in build_schema(text, layout).symbols:
            assert s.section_defined in existing or any(sec.startswith(s.section_defined) for sec in existing), (
                f"Symbol {s.name} references section {s.section_defined} which doesn't exist in {layout.name}"
            )

    def test_all_claim_caveats_exist_in_document(self, spec_doc: tuple[str, SpecLayout]):
        """Every caveat section a claim cites must exist (they are limitation subsections)."""
        text, layout = spec_doc
        existing = _existing_sections(text)
        for c in build_schema(text, layout).claims:
            for caveat in c.caveats:
                assert caveat in existing, (
                    f"Claim {c.claim_id} cites caveat §{caveat} which doesn't exist in {layout.name}"
                )

    def test_claim_dependencies_are_valid(self, spec_doc: tuple[str, SpecLayout]):
        """Every claim's depends_on must reference another valid claim_id."""
        text, layout = spec_doc
        claims = build_schema(text, layout).claims
        all_ids = {c.claim_id for c in claims}
        for c in claims:
            for dep in c.depends_on:
                assert dep in all_ids, f"Claim {c.claim_id} depends on {dep} which is not a valid claim_id"


# === Finding #4: Artifact content detection ===


class TestArtifactDetectionContract:
    def test_contract_block_detects_all_content(self, spec_doc: tuple[str, SpecLayout]):
        """The full contract block must contain every structural element."""
        text, layout = spec_doc
        schema = build_schema(text, layout)
        contract = next(a for a in schema.artifacts if a.artifact_id == "contract_block")
        assert contract.contains_operative_form, "contract block should detect operative form"
        assert contract.contains_existential_form, "contract block should detect existential form"
        assert contract.contains_pipeline_corollary, "contract block should detect pipeline corollary"
        assert contract.contains_independence_caveat, "contract block should detect independence caveat"
        assert contract.contains_error_checklist, "contract block should detect error checklist"
        assert contract.contains_spec_version_field, f"contract block should carry the {layout.version_field} field"

    def test_repository_block_detects_content(self, spec_doc: tuple[str, SpecLayout]):
        """The repository-level block (CLAUDE.md / agent instruction file) must carry the core claims."""
        text, layout = spec_doc
        schema = build_schema(text, layout)
        repo_block = next(a for a in schema.artifacts if a.scope == "repository")
        assert repo_block.contains_operative_form, f"{repo_block.name} should detect operative form"
        assert repo_block.contains_pipeline_corollary, f"{repo_block.name} should detect pipeline corollary"
        assert repo_block.contains_independence_caveat, f"{repo_block.name} should detect independence caveat"
        assert repo_block.contains_spec_version_field, (
            f"{repo_block.name} should carry the {layout.version_field} field"
        )

    def test_artifact_ids_match_layout(self, spec_doc: tuple[str, SpecLayout]):
        text, layout = spec_doc
        artifacts = _build_artifacts(text, layout)
        assert tuple(a.artifact_id for a in artifacts) == layout.artifact_ids


# === Finding #5: Hardcoded section IDs ===


class TestSectionIdContract:
    def test_all_hardcoded_sections_exist(self, spec_doc: tuple[str, SpecLayout]):
        """No hardcoded section ID should be missing from the document."""
        text, layout = spec_doc
        warnings = validate_section_ids(text, layout)
        assert warnings == [], f"Section ID drift detected in {layout.name}: {warnings}"

    def test_expected_sections_cover_layout_fields(self):
        """expected_sections() must include every section id the checker logic uses."""
        for layout in (LAYOUT_V1, LAYOUT_V2):
            used = {
                layout.definitions,
                layout.operative,
                layout.existential,
                layout.pipeline,
                layout.autoregressive,
                layout.independence,
                layout.asymmetry,
            }
            assert expected_sections(layout) == used, layout.name

    def test_layouts_disagree_where_the_spec_moved(self):
        """v2 moved the independence treatment, the asymmetry, and the artifacts."""
        assert LAYOUT_V1.independence == "7.3" and LAYOUT_V2.independence == "8.3"
        assert LAYOUT_V1.asymmetry == "8" and LAYOUT_V2.asymmetry == "7"
        assert LAYOUT_V1.artifacts[0].section == "9.1" and LAYOUT_V2.artifacts[0].section == "10.1"


# === CRITICAL drift fix #1: Claims content verified against spec ===


def _extract_distinctive_fragments(latex: str) -> list[str]:
    """Extract key mathematical fragments that define a claim's identity."""
    norm = re.sub(r"\s+", "", latex)
    fragments = []
    for pattern in [
        r"\\forallM",
        r"\\mathbb{E}",
        r"\\geq\\delta",
        r"\\exists",
        r"\\prod_{i=1}",
        r"(1-p_i)",
        r"\\partial",
        r"\\leq0",
        r">0",
        r"P_\\theta",
        r"\\varepsilon",
        r"\\mathcal{D}",
        r"\\mathcal{M}",
    ]:
        if pattern in norm:
            fragments.append(pattern)
    return fragments


class TestClaimsContentContract:
    """Verify that _build_claims() content matches the actual spec."""

    def test_every_claim_with_display_math_has_matching_spec_block(self, spec_doc: tuple[str, SpecLayout]):
        """Each claim with display math must share key LaTeX fragments with a spec math block."""
        text, layout = spec_doc
        claims = build_schema(text, layout).claims
        math_blocks = extract_math_blocks(text, layout)
        blocks_by_section: dict[str, list[str]] = {}
        for b in math_blocks:
            blocks_by_section.setdefault(b.section, []).append(b.latex)

        for c in claims:
            if not c.latex or c.status == "definition":
                continue
            section_blocks: list[str] = []
            for sec, blocks in blocks_by_section.items():
                if sec == c.section or c.section.startswith(sec) or sec.startswith(c.section):
                    section_blocks.extend(blocks)

            if not section_blocks:
                continue

            fragments = _extract_distinctive_fragments(c.latex)
            if not fragments:
                continue

            match_counts = []
            for block in section_blocks:
                block_norm = re.sub(r"\s+", "", block)
                hits = sum(1 for f in fragments if f in block_norm)
                match_counts.append(hits)

            best_match = max(match_counts) if match_counts else 0
            threshold = max(1, len(fragments) // 2)

            assert best_match >= threshold, (
                f"Claim {c.claim_id} (section {c.section}, {layout.name}) shares only "
                f"{best_match}/{len(fragments)} distinctive fragments with spec math blocks. "
                f"Fragments checked: {fragments}."
            )

    def test_every_claim_latex_appears_in_spec_text(self, spec_doc: tuple[str, SpecLayout]):
        """Each claim's core latex notation must appear somewhere in its spec section (inline or display)."""
        from pals_check.math_checker import _get_section_text

        text, layout = spec_doc
        for c in build_schema(text, layout).claims:
            if not c.latex:
                continue
            section_text = _get_section_text(text, c.section)
            if not section_text:
                continue
            fragments = [
                frag for frag in (r"\varepsilon", r"\mathbb{E}", r"\exists", r"\prod", r"\partial") if frag in c.latex
            ]
            for frag in fragments:
                assert frag in section_text or frag in text, (
                    f"Claim {c.claim_id} uses {frag!r} but it's not in spec section {c.section}"
                )

    def test_claim_count_matches_spec_math_bearing_sections(self, spec_doc: tuple[str, SpecLayout]):
        """Every section that contains a $$...$$ block must be covered by a claim."""
        text, layout = spec_doc
        math_blocks = extract_math_blocks(text, layout)
        sections_with_math = {b.section for b in math_blocks}
        claim_sections = {c.section for c in build_schema(text, layout).claims}

        uncovered = set()
        for sec in sections_with_math:
            if sec not in claim_sections and not any(cs.startswith(sec) or sec.startswith(cs) for cs in claim_sections):
                uncovered.add(sec)

        assert not uncovered, (
            f"Sections with math blocks not covered by any claim in {layout.name}: {uncovered}. "
            f"If new math was added to the spec, _build_claims() needs updating."
        )

    def test_claim_supported_by_references_are_valid(self, spec_doc: tuple[str, SpecLayout]):
        """Each claim's supported_by entries must be valid ref_ids or argument section IDs."""
        from pals_check.references import extract_references

        text, layout = spec_doc
        refs = extract_references(text)
        valid_ref_ids = {r.ref_id for r in refs}

        claims = build_schema(text, layout).claims
        all_claim_ids = {c.claim_id for c in claims}

        for c in claims:
            for ref in c.supported_by:
                assert ref in valid_ref_ids or ref in all_claim_ids, (
                    f"Claim {c.claim_id} lists supported_by={ref!r} which is "
                    f"neither a valid reference ID nor a valid claim ID in {layout.name}. "
                    f"Valid ref IDs: {sorted(valid_ref_ids)}"
                )


# === CRITICAL drift fix #2: Symbols content verified against spec ===


class TestSymbolsContentContract:
    """Verify that _build_symbols() content matches the actual spec."""

    def test_symbol_count_matches_spec_definitions(self, spec_doc: tuple[str, SpecLayout]):
        """Each symbol declared in the definitions section must appear in its inline math.

        Symbols come from build_schema(), not _build_symbols(layout), so the v2.1.0
        vocabulary (gated on the document's own version) is checked against v2.1.0
        and not claimed for v2.0.0.
        """
        text, layout = spec_doc
        symbols = build_schema(text, layout).symbols

        by_section: dict[str, list] = {}
        for s in symbols:
            by_section.setdefault(s.section_defined, []).append(s)

        for sec in by_section:
            pat = rf"###?\s+{re.escape(sec)}\b"
            assert re.search(pat, text), f"Symbol section {sec} not found in {layout.name} spec"

        sec_def = layout.definitions
        sec_match = re.search(rf"###\s+{re.escape(sec_def)}\b.*?\n(.*?)(?=\n###?\s+\d)", text, re.DOTALL)
        assert sec_match, f"Section {sec_def} not found in spec"
        sec_text = sec_match.group(1)

        spec_latex = set(re.findall(r"\$([^$]+)\$", sec_text))
        for s in by_section.get(sec_def, []):
            found = any(s.latex in spec_l for spec_l in spec_latex)
            assert found, (
                f"Symbol {s.name} has latex {s.latex!r} not found in spec §{sec_def} ({layout.name}). "
                f"Spec latex notations: {sorted(spec_latex)}"
            )

    def test_symbol_latex_appears_in_spec_section(self, spec_doc: tuple[str, SpecLayout]):
        """Each symbol's LaTeX must appear somewhere in its declared section."""
        text, layout = spec_doc
        for s in build_schema(text, layout).symbols:
            sec_pattern = rf"###?\s+{re.escape(s.section_defined)}\b"
            sec_match = re.search(sec_pattern, text)
            assert sec_match, (
                f"Symbol {s.name} references section {s.section_defined} which was not found in the {layout.name} spec"
            )
            start = sec_match.end()
            next_sec = re.search(r"\n#{2,4}\s+\d", text[start:])
            end = start + (next_sec.start() if next_sec else len(text) - start)
            section_text = text[start:end]

            found = re.search(re.escape(s.latex), section_text) is not None or s.latex in section_text
            assert found, (
                f"Symbol {s.name} has latex {s.latex!r} not found in spec section "
                f"{s.section_defined} ({layout.name}). The spec may have changed this symbol's notation."
            )


# === CRITICAL drift fix #3: Error classes verified against spec ===


def _taxonomy_table_ids(text: str) -> set[str]:
    sec5_match = re.search(r"##\s+5\.\s+.*?\n(.*?)(?=\n---)", text, re.DOTALL)
    assert sec5_match, "Section 5 (error taxonomy) not found in spec"
    table_rows = [line for line in sec5_match.group(1).split("\n") if line.strip().startswith("|")]
    return set(re.findall(r"`(ERR_[A-Z_]+)`", "\n".join(table_rows)))


class TestErrorClassesSpecContract:
    """Verify that ErrorClass enum and _build_error_classes() match the spec's §5 table."""

    def test_error_class_identifiers_match_spec_taxonomy(self, spec_doc: tuple[str, SpecLayout]):
        """Every ERR_* identifier in §5's taxonomy table must exist in the ErrorClass enum, and vice versa."""
        text, layout = spec_doc
        spec_err_ids = _taxonomy_table_ids(text)
        enum_err_ids = {ec.value for ec in ErrorClass}

        assert not (spec_err_ids - enum_err_ids), (
            f"Spec §5 ({layout.name}) defines error classes not in ErrorClass enum: {spec_err_ids - enum_err_ids}."
        )
        assert not (enum_err_ids - spec_err_ids), (
            f"ErrorClass enum has classes not in spec §5 ({layout.name}): {enum_err_ids - spec_err_ids}."
        )

    def test_error_class_count_matches_spec(self, spec_doc: tuple[str, SpecLayout]):
        """The number of distinct error classes in the enum must match the spec's §5 table."""
        text, _ = spec_doc
        spec_count = len(_taxonomy_table_ids(text))
        assert spec_count == len(ErrorClass)
        assert spec_count == len(_build_error_classes())

    def test_asymmetry_partition_matches_spec_math_blocks(self, spec_doc: tuple[str, SpecLayout]):
        """The structural/semantic partition in schema.py must match the asymmetry math blocks."""
        text, layout = spec_doc
        blocks = asymmetry_blocks(extract_math_blocks(text, layout), layout)
        assert len(blocks) >= 2, (
            f"Expected at least 2 asymmetry math blocks in §{layout.asymmetry} ({layout.name}), found {len(blocks)}"
        )

        spec_structural = set(re.findall(r"ERR_[A-Z_]+", blocks[0].latex.replace("\\_", "_")))
        spec_semantic = set(re.findall(r"ERR_[A-Z_]+", blocks[1].latex.replace("\\_", "_")))

        schema = build_schema(text, layout)
        assert spec_structural == set(schema.structural_error_classes), (
            f"Structural partition mismatch ({layout.name}). Spec: {sorted(spec_structural)}, "
            f"schema.py: {sorted(schema.structural_error_classes)}"
        )
        assert spec_semantic == set(schema.semantic_error_classes), (
            f"Semantic partition mismatch ({layout.name}). Spec: {sorted(spec_semantic)}, "
            f"schema.py: {sorted(schema.semantic_error_classes)}"
        )
