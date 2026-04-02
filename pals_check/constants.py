"""Enumerations and constants for PALS's LAW companion."""

from __future__ import annotations

from enum import Enum


class ErrorClass(str, Enum):
    """The nine intrinsic error classes defined in \u00a75."""

    ERR_HALLUCINATION = "ERR_HALLUCINATION"
    ERR_OMISSION = "ERR_OMISSION"
    ERR_SCHEMA = "ERR_SCHEMA"
    ERR_TRUNCATION = "ERR_TRUNCATION"
    ERR_SYCOPHANCY = "ERR_SYCOPHANCY"
    ERR_INSTRUCTION = "ERR_INSTRUCTION"
    ERR_CALIBRATION = "ERR_CALIBRATION"
    ERR_REASONING = "ERR_REASONING"
    ERR_SEMANTIC = "ERR_SEMANTIC"


class ClaimStatus(str, Enum):
    """Epistemic status of a claim within the document."""

    OPERATIVE = "operative"  # \u00a73.2 \u2014 empirically grounded
    EXISTENTIAL = "existential"  # \u00a73.3 \u2014 formally establishable
    INFORMAL_ARG = "informal_arg"  # \u00a76   \u2014 motivational, not proof
    HYPOTHESIS = "hypothesis"  # \u00a78.5 \u2014 labeled conjecture
    COROLLARY = "corollary"  # \u00a78   \u2014 derived consequence
    DEFINITION = "definition"  # \u00a73.1 \u2014 definitional


class DetectionDifficulty(str, Enum):
    """Corollary 5 classification."""

    CONSTANT_OR_DECREASING = "constant_or_decreasing"
    INCREASING = "increasing"
