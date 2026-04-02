"""Tests for pals_check.constants enumerations."""

from __future__ import annotations

from pals_check.constants import ClaimStatus, DetectionDifficulty, ErrorClass


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
            "ERR_HALLUCINATION", "ERR_OMISSION", "ERR_SCHEMA",
            "ERR_TRUNCATION", "ERR_SYCOPHANCY", "ERR_INSTRUCTION",
            "ERR_CALIBRATION", "ERR_REASONING", "ERR_SEMANTIC",
        }
        assert {ec.value for ec in ErrorClass} == expected


class TestClaimStatus:
    def test_claim_status_count(self):
        assert len(ClaimStatus) == 6

    def test_operative_value(self):
        assert ClaimStatus.OPERATIVE.value == "operative"

    def test_claim_status_is_str_enum(self):
        assert isinstance(ClaimStatus.HYPOTHESIS, str)


class TestDetectionDifficulty:
    def test_detection_difficulty_count(self):
        assert len(DetectionDifficulty) == 2

    def test_detection_difficulty_values(self):
        assert DetectionDifficulty.CONSTANT_OR_DECREASING.value == "constant_or_decreasing"
        assert DetectionDifficulty.INCREASING.value == "increasing"
