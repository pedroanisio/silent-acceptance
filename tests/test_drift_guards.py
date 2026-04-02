"""Contract tests that guard against spec-code drift.

These tests parse the PALS_LAW Markdown document and assert that the
hardcoded Python structures match it. If the spec changes, these tests
fail — converting silent drift into a loud test failure.
"""

from __future__ import annotations

import re

from pals_check.constants import ErrorClass
from pals_check.math_checker import EXPECTED_SECTIONS, validate_section_ids
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
