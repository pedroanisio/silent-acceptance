"""Formal schema definition for the specification (PALS's LAW v1.x / Silent Acceptance v2.x)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from pals_check.constants import (
    LAYOUT_V1,
    VERSION_FIELD_NAMES,
    ClaimStatus,
    SpecLayout,
    detect_layout,
    document_version,
)
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
    falsification_method: str | None = None


@dataclass
class ErrorClassDef:
    """Formal definition of an error class in the taxonomy."""

    identifier: str
    name: str
    definition: str
    detection_strategy_type: str
    corollary5_sign: str
    example: str | None = None


@dataclass
class PractitionerArtifact:
    """A copy-paste artifact defined in the practitioner section."""

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
    """Complete formal schema of the specification."""

    version: str
    content_hash: str
    symbols: list[Symbol]
    claims: list[FormalClaim]
    error_classes: list[ErrorClassDef]
    artifacts: list[PractitionerArtifact]
    dependency_graph: dict[str, list[str]]
    structural_error_classes: list[str]
    semantic_error_classes: list[str]
    layout: str = "v1"


def build_schema(text: str, layout: SpecLayout | None = None) -> PALSLawSchema:
    """Build the complete formal schema from the document text."""
    layout = layout or detect_layout(text)
    version = document_version(text)

    content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]

    # v2.1.0 introduced A/z, δ_{M,D}, τ, π_c, sev_c and ρ_c. detect_layout keys
    # on the major version only, so gate them on the document's own version.
    v21 = tuple(int(n) for n in (version.split('.') + ['0', '0'])[:2]) >= (2, 1)
    symbols = _build_symbols(layout, v21=v21)
    claims = _build_claims(layout)
    error_classes = _build_error_classes()
    artifacts = _build_artifacts(text, layout)
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
            "ERR_OMISSION",
            "ERR_SCHEMA",
            "ERR_TRUNCATION",
            "ERR_INSTRUCTION",
        ],
        semantic_error_classes=[
            "ERR_HALLUCINATION",
            "ERR_SYCOPHANCY",
            "ERR_CALIBRATION",
            "ERR_REASONING",
            "ERR_SEMANTIC",
        ],
        layout=layout.name,
    )


def _build_symbols(layout: SpecLayout = LAYOUT_V1, *, v21: bool = False) -> list[Symbol]:
    d = layout.definitions
    # In v1 the asymmetry symbols are introduced in the corollaries section (§8);
    # in v2 they are introduced in the statement subsection (§7.1).
    asym = layout.asymmetry if layout.name == "v1" else f"{layout.asymmetry}.1"
    symbols = [
        Symbol("M_class", r"\mathcal{M}", "Set", "Class of autoregressive transformer language models", d),
        Symbol(
            "M", r"M", "M ∈ M_class",
            "Solver configuration (model, harness, context policy, tool set, prompt set), "
            "identified by SOLVER_CONFIGURATION_ID"
            if v21 else "Any concrete model with parameter set θ",
            d,
        ),
        Symbol("theta", r"\theta", "ℝ^d", "Parameter set of model M", d),
        Symbol("X", r"\mathcal{X}", "Set", "Space of all valid input prompts", d),
        Symbol("Y", r"\mathcal{Y}", "Set", "Space of all possible output sequences", d),
        Symbol("x", r"x", "x ∈ X", "Any specific prompt", d),
        Symbol("y", r"y", "y ∈ Y", "One sampled output: y ~ P_θ(·|x)", d),
        *(
            [
                Symbol("Z", r"\mathcal{Z}", "Set", "Space of evaluation contexts: evidence, policy, history, declared preference, solver configuration", d),
                Symbol("z", r"z", "z ∈ Z", "One evaluation context, what acceptability is judged against", d),
                Symbol("A", r"A", "Y × X × Z → {0, 1}", "Acceptability predicate: A(y,x,z) = 1 when y is acceptable for x in context z", d),
            ]
            if v21
            else [Symbol("Sigma", r"\Sigma", "X ⇀ Y (partial function)", "Ground-truth semantic specification", d)]
        ),
        Symbol(
            "epsilon",
            r"\varepsilon",
            "Y × X × Z → {0, 1}" if v21 else "Y × X → {0, 1}",
            "Boolean error predicate: ε(y,x,z) = 1 − A(y,x,z)"
            if v21 else "Boolean error predicate: ε(y,x) = 1 iff y deviates from Σ(x)",
            d,
        ),
        Symbol(
            "D",
            r"\mathcal{D}",
            "Distribution over X",
            f"Realistic task distribution (see working definition §{layout.operative})",
            layout.operative,
        ),
        *(
            [
                Symbol("delta_MD", r"\delta_{M,\mathcal{D}}", "ℝ, δ > 0",
                       "Measured error rate of solver configuration M on distribution D; not a universal constant",
                       layout.operative),
                Symbol("tau", r"\tau", "[0, 1]",
                       "Tolerated failure rate for the declared consumer; a deployment parameter",
                       layout.operative),
            ]
            if v21
            else [Symbol("delta", r"\delta", "ℝ, δ > 0",
                         "Non-negligible lower bound on expected error rate", layout.operative)]
        ),
        Symbol("P_pipeline", r"\mathcal{P}", "(M_1, ..., M_n)", "Pipeline of n sequential LLM calls", layout.pipeline),
        Symbol(
            "p_i",
            r"p_i",
            "p_i ∈ [δ, 1)",
            f"Per-step error probability: P(ε(M_i(x_i), x_i) = 1) ≥ δ > 0 "
            f"(uniform lower bound from §{layout.operative})",
            layout.pipeline,
        ),
        Symbol("D_c", r"D_c(M)", "ℝ⁺", "Detection difficulty of error class c for model M", asym),
        Symbol("C_M", r"C(M)", "ℝ⁺", "Model capability (requires operational definition)", asym),
    ]
    if layout.name == "v2":
        symbols.extend(
            [
                Symbol("C_classes", r"\mathcal{C}", "Set", "The set of error classes enumerated in the taxonomy", d),
                Symbol(
                    "V_c",
                    r"V_c",
                    "Y × X → {0, 1}",
                    "Verifier for error class c: an executable predicate distinct from M "
                    "that returns 1 when it detects ε_c(y,x) = 1",
                    d,
                ),
                Symbol(
                    "B",
                    r"B",
                    "(S, {V_c}_{c ∈ S}), S ⊆ C_classes",
                    "Verification boundary: a declared subset of error classes with one "
                    "verifier per class, applied before output reaches a consumer",
                    d,
                ),
                *([] if not v21 else [Symbol(
                    "pi_c",
                    r"\pi_c",
                    "[0, 1]",
                    "Prevalence: rate at which class-c errors occur in M's output on D",
                    layout.asymmetry,
                ),
                Symbol(
                    "sev_c",
                    r"\mathrm{sev}_c",
                    "ℝ⁺",
                    "Severity weight of an escaped class-c error for the declared consumer",
                    layout.asymmetry,
                ),
                Symbol(
                    "rho_c",
                    r"\rho_c",
                    "ℝ⁺",
                    "Escaped risk: ρ_c(M) = π_c(M)(1 − R_c)·sev_c — the weighted rate at which class-c errors reach a consumer",
                    layout.asymmetry,
                )]),
                Symbol(
                    "R_c",
                    r"R_c",
                    "[0, 1]",
                    ("Recall of verifier V_c against configuration M on D: P(V_c(y,x) = 1 | ε_c(y,x,z) = 1)"
                     if v21 else
                     "Recall of verifier V_c against model M on distribution D: P(V_c(y,x) = 1 | ε_c(y,x) = 1)"),
                    d,
                ),
            ]
        )
    return symbols


def _build_claims(layout: SpecLayout = LAYOUT_V1) -> list[FormalClaim]:
    v1 = layout.name == "v1"
    cor = layout.corollary_sections
    claims = [
        FormalClaim(
            claim_id="DEF_EPSILON",
            name="Error predicate definition",
            section=layout.definitions,
            status=ClaimStatus.DEFINITION.value,
            latex=r"\varepsilon(y, x) \in \{0, 1\},\ \varepsilon = 1 \iff y \text{ deviates from } \Sigma(x)",
            natural_language=(
                "ε is 1 when model output deviates from ground truth in any dimension of §5. "
                "NOTE: Σ is a partial function — ε(y,x) is undefined when Σ(x) is undefined "
                "(creative/subjective prompts). The operative form's expectation is implicitly "
                "restricted to dom(Σ)."
            ),
            depends_on=[],
            supported_by=[],
            caveats=[f"{layout.independence.split('.')[0]}.1", layout.boolean_predicate],
            is_falsifiable=False,
        ),
        FormalClaim(
            claim_id="OPERATIVE",
            name="Operative form (The Law)",
            section=layout.operative,
            status=ClaimStatus.OPERATIVE.value,
            latex=r"\forall M \in \mathcal{M},\ \forall \text{ realistic } \mathcal{D}: \mathbb{E}_{x \sim \mathcal{D}}[\varepsilon(M(x), x)] \geq \delta > 0",
            natural_language="For any model and any realistic distribution, expected error rate is non-negligibly above zero",
            depends_on=["DEF_EPSILON"],
            supported_by=[
                "ji_2023",
                "maynez_2020",
                "lin_2022",
                "kadavath_2022",
                "perez_2022",
                "sharma_2023",
                "kalai_2024",
            ],
            caveats=[
                f"{layout.independence.split('.')[0]}.1",
                f"{layout.independence.split('.')[0]}.2",
                layout.boolean_predicate,
                f"{layout.independence.split('.')[0]}.6",
            ],
            is_falsifiable=True,
            falsification_method=(
                f"Produce a model M and a realistic distribution D (per §{layout.operative} working definition) "
                "where E[ε(M(x),x)] is zero or negligible (below measurement threshold). "
                "Requires operationalizing 'realistic' and 'negligible' for the test domain."
            ),
        ),
        FormalClaim(
            claim_id="EXISTENTIAL",
            name="Existential form",
            section=layout.existential,
            status=ClaimStatus.EXISTENTIAL.value,
            latex=r"\forall M \in \mathcal{M}: \exists x \in \mathcal{X} \text{ s.t. } P_\theta(\varepsilon(M(x),x)=1) > 0",
            natural_language="For every model, there exists at least one input on which incorrect output has positive probability",
            depends_on=["DEF_EPSILON"],
            supported_by=["ARG_6.2"],
            caveats=[f"{layout.independence.split('.')[0]}.1"],
            is_falsifiable=True,
            falsification_method=(
                "Prove that a specific model M has P(ε=1) = 0 for ALL x ∈ X. "
                "This would require proving the model solves arbitrary NLU — "
                "equivalent to proving a finite-parameter system represents all computable functions."
            ),
        ),
        FormalClaim(
            claim_id="PIPELINE",
            name="Pipeline corollary",
            section=layout.pipeline,
            status=ClaimStatus.COROLLARY.value,
            latex=r"P(\text{error-free pipeline}) = \prod_{i=1}^{n}(1-p_i) \to 0 \text{ as } n \to \infty",
            natural_language=(
                "Unverified pipeline failure probability approaches 1 as pipeline length grows. "
                "Requires Σp_i = ∞ (e.g. p_i ≥ δ > 0 uniform lower bound); "
                "if p_i decreases fast enough (e.g. p_i = 2^{-i}), the product converges "
                "and pipeline error stays bounded below 1."
            ),
            depends_on=["OPERATIVE"],
            supported_by=[],
            caveats=[layout.independence],
            is_falsifiable=True,
            falsification_method=(
                "Show that pipeline errors are so correlated (non-independent) that "
                "the product formula fundamentally mischaracterizes the risk direction, "
                "or that per-step error probabilities decrease fast enough (p_i = o(1/i)) "
                "for Σp_i < ∞, making the product converge to a positive value. "
                f"§{layout.independence} already acknowledges the independence assumption is approximate."
            ),
        ),
        FormalClaim(
            claim_id="ARG_6.1",
            name="Probabilistic generation ≠ deterministic truth",
            section="6.1",
            status=ClaimStatus.INFORMAL_ARG.value,
            latex=r"P_\theta(y \mid x) = \prod_{t=1}^{|y|} P_\theta(y_t \mid y_{<t}, x)",
            natural_language="No learned distribution over a discrete vocabulary exactly matches Σ on all inputs",
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
            natural_language="Pigeonhole: |θ| finite, true propositions unbounded → some must be unrepresented",
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
    ]

    asymmetry = FormalClaim(
        claim_id="COR5" if v1 else "ASYMMETRY",
        name="Capability-Detection Asymmetry (Hypothesis)",
        section=layout.asymmetry,
        status=ClaimStatus.HYPOTHESIS.value,
        latex=r"\frac{\partial D_c}{\partial C} \leq 0 \text{ (structural)}, > 0 \text{ (semantic/epistemic)}",
        natural_language="As model capability grows, structural errors get easier to detect while semantic errors get harder",
        depends_on=["OPERATIVE"],
        supported_by=["lin_2022"],
        caveats=[] if v1 else [f"{layout.independence.split('.')[0]}.7"],
        is_falsifiable=True,
        falsification_method=(
            "Operationalize C(M) and D_c(M), then show ∂D_c/∂C ≤ 0 for a semantic class "
            "(e.g. hallucination detection gets easier with more capable models)."
            if v1
            else f"Run the protocol in §{layout.asymmetry}.3: fix a benchmark suite for C(M) and a "
            "reference verifier per class for D_c(M) = 1 − recall; a semantic class whose "
            "miss rate falls as C rises under the fixed verifier refutes the inequality."
        ),
    )

    if not v1:
        claims.append(
            FormalClaim(
                claim_id="VBP",
                name="Verification Boundary Principle",
                section=f"{layout.corollaries}.1",
                status=ClaimStatus.PRESCRIPTION.value,
                latex="",
                natural_language=(
                    "Every system consuming LLM output must declare a verification boundary "
                    "B = (S, {V_c}) stating scope, mechanism, calibration model, and location "
                    "before the output reaches a consumer."
                ),
                depends_on=["OPERATIVE", "DEF_EPSILON"],
                supported_by=[],
                caveats=[f"{layout.independence.split('.')[0]}.4"],
                is_falsifiable=False,
            )
        )

    claims.extend(
        [
            FormalClaim(
                claim_id="COR1",
                name="Appearance of correctness ≠ correctness",
                section=cor[0],
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
                section=cor[1],
                status=ClaimStatus.COROLLARY.value,
                latex="",
                natural_language=(
                    "Observing correct outputs on x_1..x_k provides no guarantee about "
                    "P(ε=1) on a new input x_{k+1} not in {x_1..x_k}. The operative form's "
                    "bound is unconditional — no finite sample inductively lowers it."
                ),
                depends_on=["OPERATIVE"],
                supported_by=[],
                caveats=[],
                is_falsifiable=True,
                falsification_method=(
                    "Show that observing correct outputs on a finite set of inputs "
                    "provides a provable bound on P(ε=1) for unseen inputs."
                ),
            ),
            FormalClaim(
                claim_id="COR3",
                name="Verification scope must match error taxonomy",
                section=cor[2],
                status=ClaimStatus.COROLLARY.value,
                latex="",
                natural_language="Partial verification (e.g. schema-only) does not cover other error classes",
                depends_on=["OPERATIVE", "DEF_EPSILON"],
                supported_by=[],
                caveats=[f"{layout.independence.split('.')[0]}.4"],
                is_falsifiable=False,
            ),
            FormalClaim(
                claim_id="COR4",
                name="Silent acceptance is an architectural defect",
                section=cor[3],
                status=ClaimStatus.COROLLARY.value,
                latex="",
                natural_language="Passing LLM output without a declared verification boundary is an architectural omission",
                depends_on=["OPERATIVE"],
                supported_by=[],
                caveats=[],
                is_falsifiable=False,
            ),
        ]
    )

    if v1:
        claims.append(asymmetry)
    else:
        # In v2 the asymmetry precedes the corollaries in the document; keep the
        # claim list in document order.
        claims.insert(7, asymmetry)
        claims.extend(
            [
                FormalClaim(
                    claim_id="COR5",
                    name="A verifier upgrade is a precondition for a model upgrade",
                    section=f"{layout.corollaries}.6",
                    status=ClaimStatus.COROLLARY.value,
                    latex="",
                    natural_language=(
                        "If the asymmetry holds, a boundary calibrated against M_1 has lower recall "
                        "on semantic classes when applied to a more capable M_2, so the verifier "
                        "must be upgraded before the model is."
                    ),
                    depends_on=["ASYMMETRY"],
                    supported_by=[],
                    caveats=[f"{layout.independence.split('.')[0]}.7"],
                    is_falsifiable=True,
                    falsification_method=(
                        "Show, under the §7.3 protocol, that a fixed verifier's recall on semantic "
                        "classes does not fall across a capability upgrade."
                    ),
                ),
                FormalClaim(
                    claim_id="COR6",
                    name="The verifier must sit outside the boundary it verifies",
                    section=f"{layout.corollaries}.7",
                    status=ClaimStatus.COROLLARY.value,
                    latex="",
                    natural_language=(
                        "A verifier the model or its agent can modify inherits the model's error "
                        "distribution and is under optimization pressure to weaken the check; "
                        "verifiers must be immutable from the model's perspective and their "
                        "verdicts externally checkable."
                    ),
                    depends_on=["OPERATIVE"],
                    supported_by=["wang_2026", "guo_2026"],
                    caveats=[f"{layout.independence.split('.')[0]}.7"],
                    is_falsifiable=True,
                    falsification_method=(
                        "Show a self-modifying system whose agent-editable verifier retains its "
                        "recall under selection on the score it produces."
                    ),
                ),
            ]
        )

    return claims


def _build_error_classes() -> list[ErrorClassDef]:
    return [
        ErrorClassDef(
            "ERR_HALLUCINATION",
            "Hallucination",
            "Asserting a false factual claim with apparent confidence",
            "semantic",
            "gt_0",
            "Fabricated citation with real author name, plausible DOI",
        ),
        ErrorClassDef(
            "ERR_OMISSION",
            "Omission",
            "Silently dropping required content",
            "structural",
            "leq_0",
            "Instructions followed partially, constraints missed",
        ),
        ErrorClassDef(
            "ERR_SCHEMA",
            "Schema violation",
            "Output structurally non-conformant with declared format",
            "structural",
            "leq_0",
            "JSON parse failure, missing keys",
        ),
        ErrorClassDef(
            "ERR_TRUNCATION",
            "Partial completion",
            "Output cut short due to token budget or stopping heuristics",
            "structural",
            "leq_0",
            "Response ends mid-sentence",
        ),
        ErrorClassDef(
            "ERR_SYCOPHANCY",
            "Sycophantic drift",
            "Output shaped by perceived user preference rather than truth",
            "semantic",
            "gt_0",
            "Model agrees with user's incorrect premise",
        ),
        ErrorClassDef(
            "ERR_INSTRUCTION",
            "Instruction failure",
            "Violation of explicit constraints stated in the prompt",
            "structural",
            "leq_0",
            "Wrong language, exceeded length limit",
        ),
        ErrorClassDef(
            "ERR_CALIBRATION",
            "Calibration failure",
            "Expressed confidence misaligned with actual reliability",
            "semantic",
            "gt_0",
            "High confidence on incorrect claim",
        ),
        ErrorClassDef(
            "ERR_REASONING",
            "Reasoning failure",
            "Correct facts, invalid composition — multi-step inference breakdowns",
            "semantic",
            "gt_0",
            "A→B known, B→A fails; logical contradiction across steps",
        ),
        ErrorClassDef(
            "ERR_SEMANTIC",
            "Semantic drift",
            "Correct surface form, wrong meaning",
            "semantic",
            "gt_0",
            "Paraphrase that inverts the intended claim",
        ),
    ]


def _has_operative_form(sec: str) -> bool:
    """Detect operative form via Unicode, LaTeX, or keyword."""
    low = sec.lower()
    return (
        "𝔼[ε(M(x), x)]" in sec  # Unicode
        or r"\mathbb{E}" in sec  # LaTeX
        or "operative" in low
        or "non-negligible" in low
    )


def _has_existential_form(sec: str) -> bool:
    """Detect existential form via Unicode, LaTeX, or keyword."""
    return (
        "∃ x" in sec
        or "∃x" in sec
        or r"\exists" in sec  # LaTeX
        or "existential" in sec.lower()
    )


def _has_pipeline_corollary(sec: str) -> bool:
    """Detect pipeline corollary via Unicode, LaTeX, or keyword."""
    return (
        "∏" in sec
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
    """Detect the spec-version field (any layout's spelling) used for staleness tracking."""
    low = sec.lower()
    return any(name in sec or name.lower() in low for name in VERSION_FIELD_NAMES)


def _build_artifacts(text: str, layout: SpecLayout | None = None) -> list[PractitionerArtifact]:
    layout = layout or detect_layout(text)
    artifacts = []
    for spec in layout.artifacts:
        sec = _get_section_text(text, spec.section)
        artifacts.append(
            PractitionerArtifact(
                artifact_id=spec.artifact_id,
                name=spec.name,
                section=spec.section,
                scope=spec.scope,
                contains_operative_form=_has_operative_form(sec),
                contains_existential_form=_has_existential_form(sec),
                contains_pipeline_corollary=_has_pipeline_corollary(sec),
                contains_independence_caveat=_has_independence_caveat(sec),
                contains_error_checklist=_has_error_checklist(sec),
                contains_spec_version_field=_has_spec_version_field(sec),
            )
        )
    return artifacts


def _build_dependency_graph(claims: list[FormalClaim]) -> dict[str, list[str]]:
    """Build the directed dependency graph from claims."""
    return {c.claim_id: c.depends_on for c in claims}
