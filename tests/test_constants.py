"""Tests for pals_check.constants enumerations."""

from __future__ import annotations

from pals_check.constants import (
    LAYOUT_V1,
    LAYOUT_V2,
    LAYOUTS,
    VERSION_FIELD_NAMES,
    ClaimStatus,
    DetectionDifficulty,
    ErrorClass,
    detect_layout,
    document_version,
)


class TestErrorClass:
    def test_error_class_count_is_nine(self):
        assert len(ErrorClass) == 9

    def test_error_class_values_are_prefixed(self):
        for ec in ErrorClass:
            assert ec.value.startswith("ERR_")

    def test_error_class_is_str_enum(self):
        assert isinstance(ErrorClass.ERR_HALLUCINATION, str)
        assert ErrorClass.ERR_HALLUCINATION == "ERR_HALLUCINATION"

    def test_error_class_members_complete(self):
        expected = {
            "ERR_HALLUCINATION",
            "ERR_OMISSION",
            "ERR_SCHEMA",
            "ERR_TRUNCATION",
            "ERR_SYCOPHANCY",
            "ERR_INSTRUCTION",
            "ERR_CALIBRATION",
            "ERR_REASONING",
            "ERR_SEMANTIC",
        }
        assert {ec.value for ec in ErrorClass} == expected


class TestClaimStatus:
    def test_claim_status_count(self):
        assert len(ClaimStatus) == 7

    def test_operative_value(self):
        assert ClaimStatus.OPERATIVE.value == "operative"

    def test_claim_status_is_str_enum(self):
        assert isinstance(ClaimStatus.HYPOTHESIS, str)


class TestSpecLayouts:
    def test_two_layouts_registered(self):
        assert set(LAYOUTS) == {"v1", "v2"}
        assert LAYOUTS["v1"] is LAYOUT_V1 and LAYOUTS["v2"] is LAYOUT_V2

    def test_version_field_names_cover_both_layouts(self):
        assert set(VERSION_FIELD_NAMES) == {"PALS_LAW_VERSION", "SILENT_ACCEPTANCE_VERSION"}

    def test_document_version_parses_header(self):
        assert document_version("**Document version:** 1.5.4\n") == "1.5.4"
        assert document_version("# Title\n\n**Author**  \nPreprint, v2.0.0 — September 2026\n") == "2.0.0"
        assert document_version("no header here") == "unknown"

    def test_detect_layout_by_major_version(self):
        assert detect_layout("**Document version:** 1.5.4") is LAYOUT_V1
        assert detect_layout("**Document version:** 2.0.0") is LAYOUT_V2
        assert detect_layout("Preprint, v2.0.0 — September 2026") is LAYOUT_V2
        assert detect_layout("**Document version:** 3.1.0") is LAYOUT_V2

    def test_detect_layout_defaults_to_v1_without_version(self):
        assert detect_layout("") is LAYOUT_V1
        assert detect_layout("**Document version:** draft") is LAYOUT_V1

    def test_expected_sections_are_frozen_and_distinct_between_layouts(self):
        assert isinstance(LAYOUT_V1.expected_sections, frozenset)
        assert LAYOUT_V1.expected_sections != LAYOUT_V2.expected_sections
        assert "7.3" in LAYOUT_V1.expected_sections and "8.3" in LAYOUT_V2.expected_sections

    def test_artifact_ids_are_unique_per_layout(self):
        for layout in LAYOUTS.values():
            ids = layout.artifact_ids
            assert len(ids) == len(set(ids)), layout.name


class TestDetectionDifficulty:
    def test_detection_difficulty_count(self):
        assert len(DetectionDifficulty) == 2

    def test_detection_difficulty_values(self):
        assert DetectionDifficulty.CONSTANT_OR_DECREASING.value == "constant_or_decreasing"
        assert DetectionDifficulty.INCREASING.value == "increasing"
