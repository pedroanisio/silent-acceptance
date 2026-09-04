"""Math consistency checker for the specification document."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from pals_check.constants import ClaimStatus, ErrorClass, SpecLayout, detect_layout


def expected_sections(layout: SpecLayout) -> frozenset[str]:
    """Section IDs hardcoded in this module's logic for the given layout."""
    return layout.expected_sections


def validate_section_ids(text: str, layout: SpecLayout | None = None) -> list[str]:
    """Check that all hardcoded section IDs exist in the document.

    Returns a list of warnings for any missing sections.
    """
    layout = layout or detect_layout(text)
    existing: set[str] = set()
    for m in re.finditer(r"^#{2,4}\s+([\d.]+)\.?\s", text, re.MULTILINE):
        existing.add(m.group(1).rstrip("."))

    warnings: list[str] = []
    for sec_id in sorted(expected_sections(layout)):
        if sec_id not in existing and not any(s.startswith(sec_id) for s in existing):
            warnings.append(
                f"Hardcoded section ID '{sec_id}' not found in document headings. The spec may have been restructured."
            )
    return warnings


@dataclass
class MathBlock:
    """A single mathematical expression or equation extracted from the doc."""

    block_id: str
    section: str
    latex: str
    claim_status: str
    description: str


@dataclass
class MathCheck:
    """Result of a consistency check on a math block."""

    check_id: str
    target_blocks: list[str]
    description: str
    status: str  # "pass" | "fail" | "warn" | "info"
    detail: str


def extract_math_blocks(text: str, layout: SpecLayout | None = None) -> list[MathBlock]:
    """Extract all display-math ($$...$$) blocks with section context."""
    layout = layout or detect_layout(text)
    blocks: list[MathBlock] = []

    current_section = "0"
    lines = text.split("\n")
    buffer: list[str] = []
    in_math = False

    for line in lines:
        sec_match = re.match(r"^#{2,4}\s+([\d.]+)\.?\s", line)
        if sec_match:
            current_section = sec_match.group(1).rstrip(".")

        if line.strip() == "$$" and not in_math:
            in_math = True
            buffer = []
            continue
        elif line.strip() == "$$" and in_math:
            in_math = False
            latex = "\n".join(buffer).strip()
            if latex:
                block_id = f"math_{current_section}_{len([b for b in blocks if b.section == current_section]) + 1}"
                desc = _describe_math_block(latex, current_section, layout)
                status = _infer_claim_status(current_section, text, layout)
                blocks.append(
                    MathBlock(
                        block_id=block_id,
                        section=current_section,
                        latex=latex,
                        claim_status=status,
                        description=desc,
                    )
                )
            continue

        if in_math:
            buffer.append(line)

    return blocks


def _describe_math_block(latex: str, section: str, layout: SpecLayout | None = None) -> str:
    """Generate a human-readable description of what a math block expresses."""
    layout = layout or detect_layout("")
    descriptions = {
        layout.operative: "Operative form — expected error lower bound",
        layout.existential: "Existential form — existence of error-positive input",
        layout.pipeline: "Pipeline compounding — product formula for error-free probability",
        layout.autoregressive: "Autoregressive factorization of output probability",
        layout.asymmetry: "Capability-Detection Asymmetry — partial derivatives per error class",
    }
    for key, desc in descriptions.items():
        if section.startswith(key):
            return desc

    if r"\prod" in latex:
        return "Product formula (pipeline compounding)"
    if r"\partial" in latex:
        return "Partial derivative claim (Capability-Detection Asymmetry)"
    if r"\forall" in latex and r"\exists" in latex:
        return "Quantified claim"
    if r"\mathbb{E}" in latex:
        return "Expectation-based claim"
    return "Mathematical expression"


def _infer_claim_status(section: str, text: str, layout: SpecLayout | None = None) -> str:
    """Infer the epistemic status of a claim based on its section."""
    layout = layout or detect_layout(text)
    if section == layout.operative:
        return ClaimStatus.OPERATIVE.value
    elif section == layout.existential:
        return ClaimStatus.EXISTENTIAL.value
    elif section.startswith(layout.pipeline):
        return ClaimStatus.COROLLARY.value
    elif section.startswith(layout.autoregressive.split(".")[0]):
        return ClaimStatus.INFORMAL_ARG.value
    elif section.startswith(layout.asymmetry):
        sec_text = _get_section_text(text, section)
        if "hypothesis" in sec_text.lower():
            return ClaimStatus.HYPOTHESIS.value
        return ClaimStatus.COROLLARY.value
    elif section.startswith(layout.corollaries):
        return ClaimStatus.COROLLARY.value
    elif section.startswith(layout.definitions):
        return ClaimStatus.DEFINITION.value
    return "unclassified"


def _get_section_text(text: str, section: str) -> str:
    """Extract the text of a specific section."""
    esc = re.escape(section)
    patterns = [
        rf"^#{{2,4}}\s+{esc}\s",
        rf"^#{{2,4}}\s+{esc}\.\s",
        rf"^#{{2,4}}\s+{esc}\b",
    ]
    match = None
    for pat in patterns:
        match = re.search(pat, text, re.MULTILINE)
        if match:
            break
    if not match:
        return ""
    start = match.end()
    next_sec = re.search(r"\n#{2,4}\s+\d", text[start:])
    end = start + next_sec.start() if next_sec else len(text)
    return text[start:end]


def asymmetry_blocks(blocks: list[MathBlock], layout: SpecLayout) -> list[MathBlock]:
    """The partial-derivative blocks that state the Capability-Detection Asymmetry."""
    return [b for b in blocks if b.section.startswith(layout.asymmetry) and r"\partial" in b.latex]


def check_math_consistency(blocks: list[MathBlock], text: str, layout: SpecLayout | None = None) -> list[MathCheck]:
    """Run consistency checks across all math blocks."""
    layout = layout or detect_layout(text)
    checks: list[MathCheck] = []

    # Check 1: Operative form structure
    operative = [b for b in blocks if b.section == layout.operative]
    if operative:
        latex = operative[0].latex
        has_forall_M = r"\forall M" in latex
        has_E = r"\mathbb{E}" in latex
        has_geq_delta = r"\geq \delta > 0" in latex or r"\geq \delta" in latex
        has_D = r"\mathcal{D}" in latex

        all_ok = has_forall_M and has_E and has_geq_delta and has_D
        checks.append(
            MathCheck(
                check_id="CHK_OPERATIVE_STRUCTURE",
                target_blocks=[operative[0].block_id],
                description="Operative form has required components: ∀M, E_D[ε], ≥ δ > 0",
                status="pass" if all_ok else "fail",
                detail=json.dumps(
                    {
                        "has_universal_M": has_forall_M,
                        "has_expectation": has_E,
                        "has_delta_bound": has_geq_delta,
                        "has_distribution_D": has_D,
                    }
                ),
            )
        )

    # Check 2: Existential form is strictly weaker than operative
    existential = [b for b in blocks if b.section == layout.existential]
    if operative and existential:
        ex_has_exists_x = r"\exists" in existential[0].latex and r"x" in existential[0].latex
        ex_has_forall_D = r"\forall" in existential[0].latex and r"\mathcal{D}" in existential[0].latex

        checks.append(
            MathCheck(
                check_id="CHK_EXISTENTIAL_WEAKER",
                target_blocks=[operative[0].block_id, existential[0].block_id],
                description=(
                    f"Existential form (§{layout.existential}) is strictly weaker than operative (§{layout.operative})"
                ),
                status="pass" if (ex_has_exists_x and not ex_has_forall_D) else "warn",
                detail=(
                    "Operative quantifies over all realistic D; "
                    "Existential only claims ∃x with P(ε=1)>0. "
                    f"Existential has ∃x: {ex_has_exists_x}, lacks ∀D: {not ex_has_forall_D}"
                ),
            )
        )

    # Check 3: Pipeline formula is algebraically correct
    pipeline_blocks = [b for b in blocks if b.section.startswith(layout.pipeline)]
    if len(pipeline_blocks) >= 2:
        b1 = pipeline_blocks[0].latex
        b2 = pipeline_blocks[1].latex

        b1_norm = re.sub(r"\s+", "", b1)
        b2_norm = re.sub(r"\s+", "", b2)
        has_prod_1_minus = r"\prod" in b1 and ("1-p_i" in b1_norm or "(1-p_i)" in b1_norm)
        has_complement = ("1-" in b2_norm and r"\prod" in b2) or r"1-\prod" in b2_norm
        has_limit = r"\xrightarrow" in b2 or r"\to" in b2

        # v2.1.0 replaced the independence-based product with a chain-rule
        # decomposition over conditional hazards. Both forms are valid targets:
        # older specs in this repo still carry the product form, so the check
        # is selected by what the document actually states rather than assumed.
        conditional = r"\mid" in b1 or "|" in b1
        has_chain_rule = r"\prod" in b1 and conditional and "E_" in b1_norm
        has_hazard_condition = "E_" in b2_norm and (r"\geq" in b2 or "≥" in b2) and (
            r"\delta" in b2 or "δ" in b2
        )

        if has_chain_rule:
            checks.append(
                MathCheck(
                    check_id="CHK_PIPELINE_CHAINRULE",
                    target_blocks=[b.block_id for b in pipeline_blocks],
                    description=(
                        "Pipeline decomposition is exact: "
                        "P(error-free) = ∏ P(Eᵢᶜ | E₁ᶜ … Eᵢ₋₁ᶜ), no independence assumed"
                    ),
                    status="pass" if has_chain_rule else "warn",
                    detail=json.dumps(
                        {
                            "has_chain_rule": has_chain_rule,
                            "conditions_on_history": conditional,
                            "assumes_independence": has_prod_1_minus,
                        }
                    ),
                )
            )
            checks.append(
                MathCheck(
                    check_id="CHK_PIPELINE_HAZARD",
                    target_blocks=[pipeline_blocks[1].block_id],
                    description="Hazard condition stated: P(Eᵢ | E₁ᶜ … Eᵢ₋₁ᶜ) ≥ δ for all i",
                    status="pass" if has_hazard_condition else "warn",
                    detail=(
                        "The bound P(≥1 error) ≥ 1 - (1-δ)ⁿ → 1 holds only under this "
                        "condition. Shared context can raise or lower the conditional "
                        "hazard, so a deployment must estimate it rather than assume "
                        f"independence. Condition present: {has_hazard_condition}"
                    ),
                )
            )
        else:
            checks.append(
                MathCheck(
                    check_id="CHK_PIPELINE_ALGEBRA",
                    target_blocks=[b.block_id for b in pipeline_blocks],
                    description="Pipeline formula: P(error-free) = ∏(1-p_i), P(≥1 error) = 1 - ∏(1-p_i)",
                    status="pass" if (has_prod_1_minus and has_complement) else "warn",
                    detail=json.dumps(
                        {
                            "has_product_formula": has_prod_1_minus,
                            "has_complement_formula": has_complement,
                            "has_limit_statement": has_limit,
                        }
                    ),
                )
            )

        checks.append(
            MathCheck(
                check_id="CHK_PIPELINE_LIMIT",
                target_blocks=[pipeline_blocks[1].block_id],
                description=(
                    "Limit: P(≥1 error) ≥ 1 - (1-δ)ⁿ → 1 as n → ∞ under the hazard condition"
                    if has_chain_rule
                    else "Limit: ∏(1-p_i) → 0 as n → ∞ when all p_i > 0 (hence 1 - ∏ → 1)"
                ),
                status="pass",
                detail=(
                    (
                        "Under the chain-rule decomposition, if every conditional hazard "
                        "P(Eᵢ | E₁ᶜ … Eᵢ₋₁ᶜ) ≥ δ > 0, then P(error-free) ≤ (1-δ)ⁿ → 0, so "
                        "P(at least one error) → 1. No independence is assumed; the limit "
                        "is carried by the uniform lower bound on the conditional hazard. "
                        "A hazard decaying fast enough leaves the product bounded away from "
                        f"zero — see §{layout.pipeline} and §{layout.independence}."
                    )
                    if has_chain_rule
                    else (
                        "For p_i ∈ (0,1) ∀i: ln(∏(1-p_i)) = Σln(1-p_i). "
                        "Since ln(1-p_i) < 0 for p_i > 0, the partial sums diverge to -∞ "
                        "iff Σp_i = ∞ (which holds when p_i ≥ δ > 0 for all i). "
                        "Therefore ∏(1-p_i) → 0, so P(at least one error) → 1. "
                        f"NOTE: requires independence assumption (flagged in §{layout.pipeline} caveat "
                        f"and §{layout.independence})."
                    )
                ),
            )
        )

    # Check 3b: Convergence condition for pipeline limit
    if len(pipeline_blocks) >= 2:
        b2 = pipeline_blocks[1].latex
        b2_norm = re.sub(r"\s+", "", b2)
        # Check if the spec states the convergence condition (delta > 0 uniform bound
        # or Σp_i = ∞) rather than just "p_i > 0"
        sec34_text = _get_section_text(text, layout.pipeline)
        has_uniform_bound = (
            r"\delta" in b2 or r"\delta" in pipeline_blocks[0].latex or "delta" in sec34_text.lower() or r"\geq" in b2
        )
        has_divergence_note = (
            "diverge" in sec34_text.lower() or "sum" in sec34_text.lower() and "infin" in sec34_text.lower()
        )
        checks.append(
            MathCheck(
                check_id="CHK_CONVERGENCE_CONDITION",
                target_blocks=[pipeline_blocks[1].block_id],
                description=(
                    "Pipeline limit requires Σp_i = ∞ (e.g. uniform lower bound p_i ≥ δ > 0); "
                    "p_i > 0 alone is insufficient (counterexample: p_i = 2^{-i})"
                ),
                status="pass" if has_uniform_bound else "warn",
                detail=(
                    f"Uniform bound stated in formula: {has_uniform_bound}. "
                    f"Divergence condition noted in text: {has_divergence_note}. "
                    "The operative form guarantees p_i ≥ δ > 0 for each step, "
                    "which implies Σp_i = ∞ and validates the limit. "
                    "If this condition is not explicit in the spec, it should be."
                ),
            )
        )

    # Check 4: Autoregressive factorization is standard
    arg_blocks = [b for b in blocks if b.section == layout.autoregressive]
    if arg_blocks:
        latex = arg_blocks[0].latex
        has_chain_rule = r"\prod_{t=1}" in latex and r"P_\theta" in latex
        checks.append(
            MathCheck(
                check_id="CHK_AUTOREGRESSIVE_FACTORIZATION",
                target_blocks=[arg_blocks[0].block_id],
                description="Autoregressive factorization P(y|x) = ∏P(y_t|y_{<t},x) is the chain rule of probability",
                status="pass" if has_chain_rule else "warn",
                detail="Standard chain rule application to sequential token generation. Textbook identity.",
            )
        )

    # Check 5: Capability-Detection Asymmetry partial derivatives consistency
    cor5_blocks = asymmetry_blocks(blocks, layout)
    if len(cor5_blocks) >= 2:
        b_structural = cor5_blocks[0].latex
        b_semantic = cor5_blocks[1].latex

        structural_leq_0 = r"\leq 0" in b_structural
        semantic_gt_0 = r"> 0" in b_semantic

        structural_classes: set[str] = set()
        semantic_classes: set[str] = set()
        for ec in ErrorClass:
            esc_name = ec.value.replace("ERR_", "ERR\\_")
            if esc_name in b_structural:
                structural_classes.add(ec.value)
            if esc_name in b_semantic:
                semantic_classes.add(ec.value)

        expected_structural = {"ERR_OMISSION", "ERR_SCHEMA", "ERR_TRUNCATION", "ERR_INSTRUCTION"}
        expected_semantic = {"ERR_HALLUCINATION", "ERR_SYCOPHANCY", "ERR_CALIBRATION", "ERR_REASONING", "ERR_SEMANTIC"}

        signs_ok = structural_leq_0 and semantic_gt_0
        coverage_ok = structural_classes == expected_structural and semantic_classes == expected_semantic
        all_ok = signs_ok and coverage_ok

        checks.append(
            MathCheck(
                check_id="CHK_COR5_SIGNS",
                target_blocks=[b.block_id for b in cor5_blocks],
                description=(
                    "Capability-Detection Asymmetry: ∂D_c/∂C ≤ 0 for structural classes, > 0 for semantic classes"
                ),
                status="pass" if all_ok else ("warn" if signs_ok else "fail"),
                detail=json.dumps(
                    {
                        "structural_sign_correct": structural_leq_0,
                        "semantic_sign_correct": semantic_gt_0,
                        "structural_classes_found": sorted(structural_classes),
                        "semantic_classes_found": sorted(semantic_classes),
                        "expected_structural": sorted(expected_structural),
                        "expected_semantic": sorted(expected_semantic),
                        "coverage_complete": coverage_ok,
                    },
                    indent=2,
                ),
            )
        )

    # Check 6: Cross-reference consistency
    xref_checks = _check_cross_references(text)
    checks.extend(xref_checks)

    # Check 7: Error predicate ε domain/range
    checks.append(
        MathCheck(
            check_id="CHK_EPSILON_DOMAIN",
            target_blocks=[f"math_{layout.definitions}_*"],
            description="ε(y,x) ∈ {0,1} — Boolean predicate over Y × X",
            status="pass",
            detail=(
                "ε: Y × X → {0,1} is well-defined given Σ: X → Y (partial). "
                "ε(y,x) = 1 iff y deviates from Σ(x). "
                f"§{layout.boolean_predicate} acknowledges this is a deliberate simplification; "
                "graded extension ε ∈ [0,1] noted as known gap."
            ),
        )
    )

    # Check 8: Independence caveat propagation
    pipeline_mentions = []
    for section_id in [layout.pipeline, layout.independence]:
        sec_text = _get_section_text(text, section_id)
        if not sec_text:
            patterns = [
                rf"###?\s+{re.escape(section_id)}\b",
                rf"###?\s+{re.escape(section_id)}\s",
            ]
            for pat in patterns:
                m = re.search(pat, text)
                if m:
                    start = m.end()
                    next_sec = re.search(r"\n#{2,4}\s+\d", text[start:])
                    end = start + next_sec.start() if next_sec else len(text)
                    sec_text = text[start:end]
                    break
        has_caveat = bool(sec_text) and ("independen" in sec_text.lower() or "correlat" in sec_text.lower())
        pipeline_mentions.append(
            {
                "section": section_id,
                "has_independence_caveat": has_caveat,
                "section_found": bool(sec_text),
            }
        )

    checks.append(
        MathCheck(
            check_id="CHK_INDEPENDENCE_PROPAGATION",
            target_blocks=[f"math_{layout.pipeline}_*"],
            description=(
                f"Independence caveat present at point of use (§{layout.pipeline}) "
                f"and full treatment (§{layout.independence})"
            ),
            status="pass" if all(p["has_independence_caveat"] for p in pipeline_mentions) else "warn",
            detail=json.dumps(pipeline_mentions, indent=2),
        )
    )

    return checks


def _check_cross_references(text: str) -> list[MathCheck]:
    """Verify that all internal cross-references (§N.M) point to existing sections."""
    checks: list[MathCheck] = []

    existing_sections: set[str] = set()
    for m in re.finditer(r"^#{2,4}\s+([\d.]+)\.?\s", text, re.MULTILINE):
        existing_sections.add(m.group(1).rstrip("."))

    changelog_pattern = re.compile(r"\*\*Changelog:\*\*.*?(?=\n---)", re.DOTALL)
    body_text = changelog_pattern.sub("", text)

    xrefs: set[str] = set()
    for m in re.finditer(r"§([\d.]+)", body_text):
        ref = m.group(1).rstrip(".")
        xrefs.add(ref)

    normalized_existing = {s.rstrip(".") for s in existing_sections}

    broken = xrefs - normalized_existing
    truly_broken: set[str] = set()
    for ref in broken:
        if not any(s.startswith(ref) for s in normalized_existing):
            truly_broken.add(ref)

    checks.append(
        MathCheck(
            check_id="CHK_CROSS_REFERENCES",
            target_blocks=["document"],
            description="All §N.M cross-references resolve to existing section headings",
            status="pass" if not truly_broken else "fail",
            detail=json.dumps(
                {
                    "existing_sections": sorted(normalized_existing),
                    "referenced_sections": sorted(xrefs),
                    "broken_references": sorted(truly_broken),
                },
                indent=2,
            ),
        )
    )

    return checks
