"""Enumerations, constants, and section layouts for the specification companion.

The specification has been published under two structures:

* ``v1`` — *PALS's LAW* (versions 1.x): corollaries in §8, artifacts in §9.
* ``v2`` — *Silent Acceptance* (versions 2.x): asymmetry in §7, corollaries in §9,
  artifacts in §10.

Every section identifier the checker relies on is recorded in a :class:`SpecLayout`
so that a restructure of the document is a one-place change here, and so that
older published versions remain auditable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class ErrorClass(str, Enum):
    """The nine intrinsic error classes defined in §5."""

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

    OPERATIVE = "operative"  # §3.2 — empirically grounded
    EXISTENTIAL = "existential"  # §3.3 — formally establishable
    INFORMAL_ARG = "informal_arg"  # §6   — motivational, not proof
    HYPOTHESIS = "hypothesis"  # labeled conjecture (v1 §8.5, v2 §7)
    COROLLARY = "corollary"  # derived consequence
    PRESCRIPTION = "prescription"  # v2 §9.1 — the Verification Boundary Principle
    DEFINITION = "definition"  # §3.1 — definitional


class DetectionDifficulty(str, Enum):
    """Capability-Detection Asymmetry classification."""

    CONSTANT_OR_DECREASING = "constant_or_decreasing"
    INCREASING = "increasing"


@dataclass(frozen=True)
class ArtifactSpec:
    """One practitioner artifact: its stable id, display name, section, and scope."""

    artifact_id: str
    name: str
    section: str
    scope: str


@dataclass(frozen=True)
class SpecLayout:
    """Section identifiers and naming for one published structure of the spec."""

    name: str
    display_name: str
    package_prefix: str
    version_field: str
    definitions: str
    operative: str
    existential: str
    pipeline: str
    autoregressive: str
    independence: str
    boolean_predicate: str
    asymmetry: str
    corollaries: str
    artifacts: tuple[ArtifactSpec, ...]
    # Sections for the individual corollary claims (COR1..COR4 map to these in order).
    corollary_sections: tuple[str, ...]

    @property
    def expected_sections(self) -> frozenset[str]:
        """Every section id the checker hardcodes for this layout."""
        return frozenset(
            {
                self.definitions,
                self.operative,
                self.existential,
                self.pipeline,
                self.autoregressive,
                self.independence,
                self.asymmetry,
            }
        )

    @property
    def artifact_ids(self) -> tuple[str, ...]:
        return tuple(a.artifact_id for a in self.artifacts)


LAYOUT_V1 = SpecLayout(
    name="v1",
    display_name="PALS's LAW",
    package_prefix="pals-law",
    version_field="PALS_LAW_VERSION",
    definitions="3.1",
    operative="3.2",
    existential="3.3",
    pipeline="3.4",
    autoregressive="6.1",
    independence="7.3",
    boolean_predicate="7.5",
    asymmetry="8",
    corollaries="8",
    artifacts=(
        ArtifactSpec("contract_block", "Full Contract Block", "9.1", "function"),
        ArtifactSpec("short_form", "Short-Form", "9.2", "project"),
        ArtifactSpec("inline_banner", "Inline Banner", "9.3", "inline"),
        ArtifactSpec("claudemd_block", "CLAUDE.md Integration Block", "9.4", "repository"),
    ),
    corollary_sections=("8", "8", "8", "8"),
)

LAYOUT_V2 = SpecLayout(
    name="v2",
    display_name="Silent Acceptance",
    package_prefix="silent-acceptance",
    version_field="SILENT_ACCEPTANCE_VERSION",
    definitions="3.1",
    operative="3.2",
    existential="3.3",
    pipeline="3.4",
    autoregressive="6.1",
    independence="8.3",
    boolean_predicate="8.5",
    asymmetry="7",
    corollaries="9",
    artifacts=(
        ArtifactSpec("contract_block", "Full Contract Block", "10.1", "function"),
        ArtifactSpec("short_form", "Short-Form", "10.2", "project"),
        ArtifactSpec("inline_banner", "Inline Banner", "10.3", "inline"),
        ArtifactSpec("agent_instruction_block", "Agent Instruction File Block", "10.4", "repository"),
        ArtifactSpec("ci_check", "CI Check", "10.5", "ci"),
    ),
    corollary_sections=("9.2", "9.3", "9.4", "9.5"),
)

LAYOUTS: dict[str, SpecLayout] = {LAYOUT_V1.name: LAYOUT_V1, LAYOUT_V2.name: LAYOUT_V2}

# Accepted spellings of the contract-staleness field across layouts.
VERSION_FIELD_NAMES: tuple[str, ...] = tuple(layout.version_field for layout in LAYOUTS.values())

# v1.x: "**Document version:** 1.5.4"; v2.x title page: "Preprint, v2.0.0 — ..."
_VERSION_RE = re.compile(r"(?:Document version:\*\*\s*|^Preprint,\s*v)([\d.]+)", re.MULTILINE)


def document_version(text: str) -> str:
    """Return the document version from either title-page convention, or ``"unknown"``."""
    m = _VERSION_RE.search(text)
    return m.group(1) if m else "unknown"


def detect_layout(text: str) -> SpecLayout:
    """Choose the layout from the document's major version.

    Documents without a parseable version (synthetic fixtures, fragments) are
    treated as v1, the structure the checker was originally written against.
    """
    version = document_version(text)
    try:
        major = int(version.split(".")[0])
    except ValueError:
        major = 0
    return LAYOUT_V2 if major >= 2 else LAYOUT_V1
