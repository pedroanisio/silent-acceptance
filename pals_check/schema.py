"""Formal schema definition for PALS's LAW."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Optional

from pals_check.constants import ClaimStatus
from pals_check.math_checker import _get_section_text


@dataclass
class Symbol:
    """A symbol in the formal vocabulary."""

    name: str
    latex: str
    type_signature: str
    definition: str
    section_defined: str


@dataclass
class FormalClaim:
    """A single formal claim with its epistemic metadata."""

    claim_id: str
    name: str
    section: str
    status: str
    latex: str
    natural_language: str
    depends_on: list[str]
    supported_by: list[str]
    caveats: list[str]
    is_falsifiable: bool
    falsification_method: Optional[str] = None


@dataclass
class ErrorClassDef:
    """Formal definition of an error class in the taxonomy."""

    identifier: str
    name: str
    definition: str
    detection_strategy_type: str
    corollary5_sign: str
    example: Optional[str] = None


@dataclass
class PractitionerArtifact:
    """A copy-paste artifact defined in \u00a79."""

    artifact_id: str
    name: str
    section: str
    scope: str
    contains_operative_form: bool
    contains_existential_form: bool
    contains_pipeline_corollary: bool
    contains_independence_caveat: bool
    contains_error_checklist: bool
    contains_spec_version_field: bool


@dataclass
class PALSLawSchema:
    """Complete formal schema of PALS's LAW."""

    version: str
    content_hash: str
    symbols: list[Symbol]
    claims: list[FormalClaim]
    error_classes: list[ErrorClassDef]
    artifacts: list[PractitionerArtifact]
    dependency_graph: dict[str, list[str]]
    structural_error_classes: list[str]
    semantic_error_classes: list[str]


def build_schema(text: str) -> PALSLawSchema:
    """Build the complete formal schema from the document text."""
    version_match = re.search(r'Document version:\*\*\s*([\d.]+)', text)
    version = version_match.group(1) if version_match else "unknown"

    content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]

    symbols = _build_symbols()
    claims = _build_claims()
    error_classes = _build_error_classes()
    artifacts = _build_artifacts(text)
    dep_graph = _build_dependency_graph(claims)

    return PALSLawSchema(
        version=version,
        content_hash=content_hash,
        symbols=symbols,
        claims=claims,
        error_classes=error_classes,
        artifacts=artifacts,
        dependency_graph=dep_graph,
        structural_error_classes=[
            "ERR_OMISSION", "ERR_SCHEMA", "ERR_TRUNCATION", "ERR_INSTRUCTION",
        ],
        semantic_error_classes=[
            "ERR_HALLUCINATION", "ERR_SYCOPHANCY", "ERR_CALIBRATION",
            "ERR_REASONING", "ERR_SEMANTIC",
        ],
    )


def _build_symbols() -> list[Symbol]:
    return [
        Symbol("M_class", r"\mathcal{M}", "Set",
               "Class of autoregressive transformer language models", "3.1"),
        Symbol("M", r"M", "M \u2208 M_class",
               "Any concrete model with parameter set \u03b8", "3.1"),
        Symbol("theta", r"\theta", "\u211d^d",
               "Parameter set of model M", "3.1"),
        Symbol("X", r"\mathcal{X}", "Set",
               "Space of all valid input prompts", "3.1"),
        Symbol("Y", r"\mathcal{Y}", "Set",
               "Space of all possible output sequences", "3.1"),
        Symbol("x", r"x", "x \u2208 X",
               "Any specific prompt", "3.1"),
        Symbol("y", r"y", "y \u2208 Y",
               "One sampled output: y ~ P_\u03b8(\u00b7|x)", "3.1"),
        Symbol("Sigma", r"\Sigma", "X \u21c0 Y (partial function)",
               "Ground-truth semantic specification", "3.1"),
        Symbol("epsilon", r"\varepsilon", "Y \u00d7 X \u2192 {0, 1}",
               "Boolean error predicate: \u03b5(y,x) = 1 iff y deviates from \u03a3(x)", "3.1"),
        Symbol("D", r"\mathcal{D}", "Distribution over X",
               "Realistic task distribution (see working definition \u00a73.2)", "3.2"),
        Symbol("delta", r"\delta", "\u211d, \u03b4 > 0",
               "Non-negligible lower bound on expected error rate", "3.2"),
        Symbol("P_pipeline", r"\mathcal{P}", "(M_1, ..., M_n)",
               "Pipeline of n sequential LLM calls", "3.4"),
        Symbol("p_i", r"p_i", "p_i \u2208 (0, 1)",
               "Per-step error probability: P(\u03b5(M_i(x_i), x_i) = 1)", "3.4"),
        Symbol("D_c", r"D_c(M)", "\u211d\u207a",
               "Detection difficulty of error class c for model M", "8"),
        Symbol("C_M", r"C(M)", "\u211d\u207a",
               "Model capability (requires operational definition)", "8"),
    ]


def _build_claims() -> list[FormalClaim]:
    return [
        FormalClaim(
            claim_id="DEF_EPSILON",
            name="Error predicate definition",
            section="3.1",
            status=ClaimStatus.DEFINITION.value,
            latex=r"\varepsilon(y, x) \in \{0, 1\},\ \varepsilon = 1 \iff y \text{ deviates from } \Sigma(x)",
            natural_language=(
                "\u03b5 is 1 when model output deviates from ground truth in any dimension of \u00a75. "
                "NOTE: \u03a3 is a partial function \u2014 \u03b5(y,x) is undefined when \u03a3(x) is undefined "
                "(creative/subjective prompts). The operative form's expectation is implicitly "
                "restricted to dom(\u03a3)."
            ),
            depends_on=[],
            supported_by=[],
            caveats=["7.1", "7.5"],
            is_falsifiable=False,
        ),
        FormalClaim(
            claim_id="OPERATIVE",
            name="Operative form (The Law)",
            section="3.2",
            status=ClaimStatus.OPERATIVE.value,
            latex=r"\forall M \in \mathcal{M},\ \forall \text{ realistic } \mathcal{D}: \mathbb{E}_{x \sim \mathcal{D}}[\varepsilon(M(x), x)] \geq \delta > 0",
            natural_language="For any model and any realistic distribution, expected error rate is non-negligibly above zero",
            depends_on=["DEF_EPSILON"],
            supported_by=["ji_2023", "maynez_2020", "lin_2022", "kadavath_2022", "perez_2022", "sharma_2023", "kalai_2024"],
            caveats=["7.1", "7.2", "7.5", "7.6"],
            is_falsifiable=True,
            falsification_method=(
                "Produce a model M and a realistic distribution D (per \u00a73.2 working definition) "
                "where E[\u03b5(M(x),x)] is zero or negligible (below measurement threshold). "
                "Requires operationalizing 'realistic' and 'negligible' for the test domain."
            ),
        ),
        FormalClaim(
            claim_id="EXISTENTIAL",
            name="Existential form",
            section="3.3",
            status=ClaimStatus.EXISTENTIAL.value,
            latex=r"\forall M \in \mathcal{M}: \exists x \in \mathcal{X} \text{ s.t. } P_\theta(\varepsilon(M(x),x)=1) > 0",
            natural_language="For every model, there exists at least one input on which incorrect output has positive probability",
            depends_on=["DEF_EPSILON"],
            supported_by=["ARG_6.2"],
            caveats=["7.1"],
            is_falsifiable=True,
            falsification_method=(
                "Prove that a specific model M has P(\u03b5=1) = 0 for ALL x \u2208 X. "
                "This would require proving the model solves arbitrary NLU \u2014 "
                "equivalent to proving a finite-parameter system represents all computable functions."
            ),
        ),
        FormalClaim(
            claim_id="PIPELINE",
            name="Pipeline corollary",
            section="3.4",
            status=ClaimStatus.COROLLARY.value,
            latex=r"P(\text{error-free pipeline}) = \prod_{i=1}^{n}(1-p_i) \to 0 \text{ as } n \to \infty",
            natural_language=(
                "Unverified pipeline failure probability approaches 1 as pipeline length grows. "
                "Requires \u03a3p_i = \u221e (e.g. p_i \u2265 \u03b4 > 0 uniform lower bound); "
                "if p_i decreases fast enough (e.g. p_i = 2^{-i}), the product converges "
                "and pipeline error stays bounded below 1."
            ),
            depends_on=["OPERATIVE"],
            supported_by=[],
            caveats=["7.3"],
            is_falsifiable=True,
            falsification_method=(
                "Show that pipeline errors are so correlated (non-independent) that "
                "the product formula fundamentally mischaracterizes the risk direction, "
                "or that per-step error probabilities decrease fast enough (p_i = o(1/i)) "
                "for \u03a3p_i < \u221e, making the product converge to a positive value. "
                "\u00a77.3 already acknowledges the independence assumption is approximate."
            ),
        ),
        FormalClaim(
            claim_id="ARG_6.1",
            name="Probabilistic generation \u2260 deterministic truth",
            section="6.1",
            status=ClaimStatus.INFORMAL_ARG.value,
            latex=r"P_\theta(y \mid x) = \prod_{t=1}^{|y|} P_\theta(y_t \mid y_{<t}, x)",
            natural_language="No learned distribution over a discrete vocabulary exactly matches \u03a3 on all inputs",
            depends_on=["DEF_EPSILON"],
            supported_by=["ji_2023", "maynez_2020", "lin_2022"],
            caveats=[],
            is_falsifiable=False,
            falsification_method=None,
        ),
        FormalClaim(
            claim_id="ARG_6.2",
            name="Finite parameters cannot encode unbounded world knowledge",
            section="6.2",
            status=ClaimStatus.INFORMAL_ARG.value,
            latex="",
            natural_language="Pigeonhole: |\u03b8| finite, true propositions unbounded \u2192 some must be unrepresented",
            depends_on=[],
            supported_by=[],
            caveats=[],
            is_falsifiable=False,
            falsification_method=None,
        ),
        FormalClaim(
            claim_id="ARG_6.3",
            name="Evaluation is not generation",
            section="6.3",
            status=ClaimStatus.INFORMAL_ARG.value,
            latex="",
            natural_language="Correct internal belief may not surface faithfully in sampled output",
            depends_on=[],
            supported_by=["kadavath_2022"],
            caveats=[],
            is_falsifiable=True,
            falsification_method="Show that sampling always faithfully surfaces encoded beliefs.",
        ),
        FormalClaim(
            claim_id="COR1",
            name="Appearance of correctness \u2260 correctness",
            section="8",
            status=ClaimStatus.COROLLARY.value,
            latex="",
            natural_language="Finite test-set validation does not demonstrate error-freedom on unverified inputs",
            depends_on=["OPERATIVE"],
            supported_by=[],
            caveats=[],
            is_falsifiable=False,
        ),
        FormalClaim(
            claim_id="COR2",
            name="Trust accumulation prohibited",
            section="8",
            status=ClaimStatus.COROLLARY.value,
            latex="",
            natural_language="Prior correct outputs do not reduce E[\u03b5] on the next call for different inputs",
            depends_on=["OPERATIVE"],
            supported_by=[],
            caveats=[],
            is_falsifiable=True,
            falsification_method="Show that a sequence of correct outputs Bayesian-updates E[\u03b5] toward zero.",
        ),
        FormalClaim(
            claim_id="COR3",
            name="Verification scope must match error taxonomy",
            section="8",
            status=ClaimStatus.COROLLARY.value,
            latex="",
            natural_language="Partial verification (e.g. schema-only) does not cover other error classes",
            depends_on=["OPERATIVE", "DEF_EPSILON"],
            supported_by=[],
            caveats=["7.4"],
            is_falsifiable=False,
        ),
        FormalClaim(
            claim_id="COR4",
            name="Silent acceptance is an architectural defect",
            section="8",
            status=ClaimStatus.COROLLARY.value,
            latex="",
            natural_language="Passing LLM output without a declared verification boundary is an architectural omission",
            depends_on=["OPERATIVE"],
            supported_by=[],
            caveats=[],
            is_falsifiable=False,
        ),
        FormalClaim(
            claim_id="COR5",
            name="Capability-Detection Asymmetry (Hypothesis)",
            section="8",
            status=ClaimStatus.HYPOTHESIS.value,
            latex=r"\frac{\partial D_c}{\partial C} \leq 0 \text{ (structural)}, > 0 \text{ (semantic/epistemic)}",
            natural_language="As model capability grows, structural errors get easier to detect while semantic errors get harder",
            depends_on=["OPERATIVE"],
            supported_by=["lin_2022"],
            caveats=[],
            is_falsifiable=True,
            falsification_method=(
                "Operationalize C(M) and D_c(M), then show \u2202D_c/\u2202C \u2264 0 for a semantic class "
                "(e.g. hallucination detection gets easier with more capable models)."
            ),
        ),
    ]


def _build_error_classes() -> list[ErrorClassDef]:
    return [
        ErrorClassDef("ERR_HALLUCINATION", "Hallucination",
                       "Asserting a false factual claim with apparent confidence",
                       "semantic", "gt_0",
                       "Fabricated citation with real author name, plausible DOI"),
        ErrorClassDef("ERR_OMISSION", "Omission",
                       "Silently dropping required content",
                       "structural", "leq_0",
                       "Instructions followed partially, constraints missed"),
        ErrorClassDef("ERR_SCHEMA", "Schema violation",
                       "Output structurally non-conformant with declared format",
                       "structural", "leq_0",
                       "JSON parse failure, missing keys"),
        ErrorClassDef("ERR_TRUNCATION", "Partial completion",
                       "Output cut short due to token budget or stopping heuristics",
                       "structural", "leq_0",
                       "Response ends mid-sentence"),
        ErrorClassDef("ERR_SYCOPHANCY", "Sycophantic drift",
                       "Output shaped by perceived user preference rather than truth",
                       "semantic", "gt_0",
                       "Model agrees with user's incorrect premise"),
        ErrorClassDef("ERR_INSTRUCTION", "Instruction failure",
                       "Violation of explicit constraints stated in the prompt",
                       "structural", "leq_0",
                       "Wrong language, exceeded length limit"),
        ErrorClassDef("ERR_CALIBRATION", "Calibration failure",
                       "Expressed confidence misaligned with actual reliability",
                       "semantic", "gt_0",
                       "High confidence on incorrect claim"),
        ErrorClassDef("ERR_REASONING", "Reasoning failure",
                       "Correct facts, invalid composition \u2014 multi-step inference breakdowns",
                       "semantic", "gt_0",
                       "A\u2192B known, B\u2192A fails; logical contradiction across steps"),
        ErrorClassDef("ERR_SEMANTIC", "Semantic drift",
                       "Correct surface form, wrong meaning",
                       "semantic", "gt_0",
                       "Paraphrase that inverts the intended claim"),
    ]


def _has_operative_form(sec: str) -> bool:
    """Detect operative form via Unicode, LaTeX, or keyword."""
    low = sec.lower()
    return (
        "\ud835\udd3c[\u03b5(M(x), x)]" in sec  # Unicode 𝔼[ε(M(x), x)]
        or r"\mathbb{E}" in sec  # LaTeX
        or "operative" in low
        or "non-negligible" in low
    )


def _has_existential_form(sec: str) -> bool:
    """Detect existential form via Unicode, LaTeX, or keyword."""
    return (
        "\u2203 x" in sec  # Unicode ∃ x
        or "\u2203x" in sec
        or r"\exists" in sec  # LaTeX
        or "existential" in sec.lower()
    )


def _has_pipeline_corollary(sec: str) -> bool:
    """Detect pipeline corollary via Unicode, LaTeX, or keyword."""
    return (
        "\u220f" in sec  # Unicode ∏
        or r"\prod" in sec  # LaTeX
        or "pipeline" in sec.lower()
    )


def _has_independence_caveat(sec: str) -> bool:
    """Detect independence caveat via keywords."""
    low = sec.lower()
    return "independen" in low or "correlat" in low


def _has_error_checklist(sec: str) -> bool:
    """Detect error checklist by presence of any ERR_ identifier."""
    return "ERR_HALLUCINATION" in sec or "ERR_" in sec


def _has_spec_version_field(sec: str) -> bool:
    """Detect PALS_LAW_VERSION field for contract staleness tracking."""
    return "PALS_LAW_VERSION" in sec or "pals_law_version" in sec.lower()


def _build_artifacts(text: str) -> list[PractitionerArtifact]:
    artifacts = []

    sec91 = _get_section_text(text, "9.1")
    artifacts.append(PractitionerArtifact(
        artifact_id="contract_block",
        name="Full Contract Block",
        section="9.1",
        scope="function",
        contains_operative_form=_has_operative_form(sec91),
        contains_existential_form=_has_existential_form(sec91),
        contains_pipeline_corollary=_has_pipeline_corollary(sec91),
        contains_independence_caveat=_has_independence_caveat(sec91),
        contains_error_checklist=_has_error_checklist(sec91),
        contains_spec_version_field=_has_spec_version_field(sec91),
    ))

    sec92 = _get_section_text(text, "9.2")
    artifacts.append(PractitionerArtifact(
        artifact_id="short_form",
        name="Short-Form",
        section="9.2",
        scope="project",
        contains_operative_form=_has_operative_form(sec92),
        contains_existential_form=_has_existential_form(sec92),
        contains_pipeline_corollary=_has_pipeline_corollary(sec92),
        contains_independence_caveat=_has_independence_caveat(sec92),
        contains_error_checklist=_has_error_checklist(sec92),
        contains_spec_version_field=_has_spec_version_field(sec92),
    ))

    sec93 = _get_section_text(text, "9.3")
    artifacts.append(PractitionerArtifact(
        artifact_id="inline_banner",
        name="Inline Banner",
        section="9.3",
        scope="inline",
        contains_operative_form=_has_operative_form(sec93),
        contains_existential_form=_has_existential_form(sec93),
        contains_pipeline_corollary=_has_pipeline_corollary(sec93),
        contains_independence_caveat=_has_independence_caveat(sec93),
        contains_error_checklist=_has_error_checklist(sec93),
        contains_spec_version_field=_has_spec_version_field(sec93),
    ))

    sec94 = _get_section_text(text, "9.4")
    artifacts.append(PractitionerArtifact(
        artifact_id="claudemd_block",
        name="CLAUDE.md Integration Block",
        section="9.4",
        scope="repository",
        contains_operative_form=_has_operative_form(sec94),
        contains_existential_form=_has_existential_form(sec94),
        contains_pipeline_corollary=_has_pipeline_corollary(sec94),
        contains_independence_caveat=_has_independence_caveat(sec94),
        contains_error_checklist=_has_error_checklist(sec94),
        contains_spec_version_field=_has_spec_version_field(sec94),
    ))

    return artifacts


def _build_dependency_graph(claims: list[FormalClaim]) -> dict[str, list[str]]:
    """Build the directed dependency graph from claims."""
    return {c.claim_id: c.depends_on for c in claims}
