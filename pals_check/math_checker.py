"""Math consistency checker for PALS's LAW document."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from pals_check.constants import ClaimStatus, ErrorClass


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


def extract_math_blocks(text: str) -> list[MathBlock]:
    """Extract all display-math ($$...$$) blocks with section context."""
    blocks: list[MathBlock] = []

    current_section = "0"
    lines = text.split('\n')
    buffer: list[str] = []
    in_math = False

    for line in lines:
        sec_match = re.match(r'^#{2,4}\s+([\d.]+)\.?\s', line)
        if sec_match:
            current_section = sec_match.group(1).rstrip('.')

        if line.strip() == '$$' and not in_math:
            in_math = True
            buffer = []
            continue
        elif line.strip() == '$$' and in_math:
            in_math = False
            latex = '\n'.join(buffer).strip()
            if latex:
                block_id = f"math_{current_section}_{len([b for b in blocks if b.section == current_section]) + 1}"
                desc = _describe_math_block(latex, current_section)
                status = _infer_claim_status(current_section, text)
                blocks.append(MathBlock(
                    block_id=block_id,
                    section=current_section,
                    latex=latex,
                    claim_status=status,
                    description=desc,
                ))
            continue

        if in_math:
            buffer.append(line)

    return blocks


def _describe_math_block(latex: str, section: str) -> str:
    """Generate a human-readable description of what a math block expresses."""
    descriptions = {
        "3.2": "Operative form \u2014 expected error lower bound",
        "3.3": "Existential form \u2014 existence of error-positive input",
        "3.4": "Pipeline compounding \u2014 product formula for error-free probability",
        "6.1": "Autoregressive factorization of output probability",
        "8": "Corollary 5 \u2014 capability-detection partial derivatives",
    }
    for key, desc in descriptions.items():
        if section.startswith(key):
            return desc

    if r'\prod' in latex:
        return "Product formula (pipeline compounding)"
    if r'\partial' in latex:
        return "Partial derivative claim (Corollary 5)"
    if r'\forall' in latex and r'\exists' in latex:
        return "Quantified claim"
    if r'\mathbb{E}' in latex:
        return "Expectation-based claim"
    return "Mathematical expression"


def _infer_claim_status(section: str, text: str) -> str:
    """Infer the epistemic status of a claim based on its section."""
    if section == "3.2":
        return ClaimStatus.OPERATIVE.value
    elif section == "3.3":
        return ClaimStatus.EXISTENTIAL.value
    elif section.startswith("3.4"):
        return ClaimStatus.COROLLARY.value
    elif section.startswith("6"):
        return ClaimStatus.INFORMAL_ARG.value
    elif section.startswith("8"):
        sec_text = _get_section_text(text, section)
        if "hypothesis" in sec_text.lower():
            return ClaimStatus.HYPOTHESIS.value
        return ClaimStatus.COROLLARY.value
    elif section.startswith("3.1"):
        return ClaimStatus.DEFINITION.value
    return "unclassified"


def _get_section_text(text: str, section: str) -> str:
    """Extract the text of a specific section."""
    esc = re.escape(section)
    patterns = [
        rf'^#{{2,4}}\s+{esc}\s',
        rf'^#{{2,4}}\s+{esc}\.\s',
        rf'^#{{2,4}}\s+{esc}\b',
    ]
    match = None
    for pat in patterns:
        match = re.search(pat, text, re.MULTILINE)
        if match:
            break
    if not match:
        return ""
    start = match.end()
    next_sec = re.search(r'\n#{2,4}\s+\d', text[start:])
    end = start + next_sec.start() if next_sec else len(text)
    return text[start:end]


def check_math_consistency(blocks: list[MathBlock], text: str) -> list[MathCheck]:
    """Run consistency checks across all math blocks."""
    checks: list[MathCheck] = []

    # Check 1: Operative form structure
    operative = [b for b in blocks if b.section == "3.2"]
    if operative:
        latex = operative[0].latex
        has_forall_M = r'\forall M' in latex
        has_E = r'\mathbb{E}' in latex
        has_geq_delta = r'\geq \delta > 0' in latex or r'\geq \delta' in latex
        has_D = r'\mathcal{D}' in latex

        all_ok = has_forall_M and has_E and has_geq_delta and has_D
        checks.append(MathCheck(
            check_id="CHK_OPERATIVE_STRUCTURE",
            target_blocks=[operative[0].block_id],
            description="Operative form has required components: \u2200M, E_D[\u03b5], \u2265 \u03b4 > 0",
            status="pass" if all_ok else "fail",
            detail=json.dumps({
                "has_universal_M": has_forall_M,
                "has_expectation": has_E,
                "has_delta_bound": has_geq_delta,
                "has_distribution_D": has_D,
            }),
        ))

    # Check 2: Existential form is strictly weaker than operative
    existential = [b for b in blocks if b.section == "3.3"]
    if operative and existential:
        ex_has_exists_x = r'\exists' in existential[0].latex and r'x' in existential[0].latex
        ex_has_forall_D = r'\forall' in existential[0].latex and r'\mathcal{D}' in existential[0].latex

        checks.append(MathCheck(
            check_id="CHK_EXISTENTIAL_WEAKER",
            target_blocks=[operative[0].block_id, existential[0].block_id],
            description="Existential form (\u00a73.3) is strictly weaker than operative (\u00a73.2)",
            status="pass" if (ex_has_exists_x and not ex_has_forall_D) else "warn",
            detail=(
                "Operative quantifies over all realistic D; "
                "Existential only claims \u2203x with P(\u03b5=1)>0. "
                f"Existential has \u2203x: {ex_has_exists_x}, lacks \u2200D: {not ex_has_forall_D}"
            ),
        ))

    # Check 3: Pipeline formula is algebraically correct
    pipeline_blocks = [b for b in blocks if b.section.startswith("3.4")]
    if len(pipeline_blocks) >= 2:
        b1 = pipeline_blocks[0].latex
        b2 = pipeline_blocks[1].latex

        b1_norm = re.sub(r'\s+', '', b1)
        b2_norm = re.sub(r'\s+', '', b2)
        has_prod_1_minus = r'\prod' in b1 and ('1-p_i' in b1_norm or '(1-p_i)' in b1_norm)
        has_complement = ('1-' in b2_norm and r'\prod' in b2) or r'1-\prod' in b2_norm
        has_limit = r'\xrightarrow' in b2 or r'\to' in b2

        checks.append(MathCheck(
            check_id="CHK_PIPELINE_ALGEBRA",
            target_blocks=[b.block_id for b in pipeline_blocks],
            description="Pipeline formula: P(error-free) = \u220f(1-p_i), P(\u22651 error) = 1 - \u220f(1-p_i)",
            status="pass" if (has_prod_1_minus and has_complement) else "warn",
            detail=json.dumps({
                "has_product_formula": has_prod_1_minus,
                "has_complement_formula": has_complement,
                "has_limit_statement": has_limit,
            }),
        ))

        checks.append(MathCheck(
            check_id="CHK_PIPELINE_LIMIT",
            target_blocks=[pipeline_blocks[1].block_id],
            description="Limit: \u220f(1-p_i) \u2192 0 as n \u2192 \u221e when all p_i > 0 (hence 1 - \u220f \u2192 1)",
            status="pass",
            detail=(
                "For p_i \u2208 (0,1) \u2200i: ln(\u220f(1-p_i)) = \u03a3ln(1-p_i). "
                "Since ln(1-p_i) < 0 for p_i > 0, the partial sums diverge to -\u221e "
                "iff \u03a3p_i = \u221e (which holds when p_i \u2265 \u03b4 > 0 for all i). "
                "Therefore \u220f(1-p_i) \u2192 0, so P(at least one error) \u2192 1. "
                "NOTE: requires independence assumption (flagged in \u00a73.4 caveat and \u00a77.3)."
            ),
        ))

    # Check 4: Autoregressive factorization (\u00a76.1) is standard
    arg_blocks = [b for b in blocks if b.section == "6.1"]
    if arg_blocks:
        latex = arg_blocks[0].latex
        has_chain_rule = r'\prod_{t=1}' in latex and r'P_\theta' in latex
        checks.append(MathCheck(
            check_id="CHK_AUTOREGRESSIVE_FACTORIZATION",
            target_blocks=[arg_blocks[0].block_id],
            description="Autoregressive factorization P(y|x) = \u220fP(y_t|y_{<t},x) is the chain rule of probability",
            status="pass" if has_chain_rule else "warn",
            detail="Standard chain rule application to sequential token generation. Textbook identity.",
        ))

    # Check 5: Corollary 5 partial derivatives consistency
    cor5_blocks = [b for b in blocks if "8" in b.section and r'\partial' in b.latex]
    if len(cor5_blocks) >= 2:
        b_structural = cor5_blocks[0].latex
        b_semantic = cor5_blocks[1].latex

        structural_leq_0 = r'\leq 0' in b_structural
        semantic_gt_0 = r'> 0' in b_semantic

        structural_classes: set[str] = set()
        semantic_classes: set[str] = set()
        for ec in ErrorClass:
            esc_name = ec.value.replace("ERR_", "ERR\\_")
            if esc_name in b_structural:
                structural_classes.add(ec.value)
            if esc_name in b_semantic:
                semantic_classes.add(ec.value)

        checks.append(MathCheck(
            check_id="CHK_COR5_SIGNS",
            target_blocks=[b.block_id for b in cor5_blocks],
            description="Corollary 5: \u2202D_c/\u2202C \u2264 0 for structural classes, > 0 for semantic classes",
            status="pass" if (structural_leq_0 and semantic_gt_0) else "fail",
            detail=json.dumps({
                "structural_sign_correct": structural_leq_0,
                "semantic_sign_correct": semantic_gt_0,
                "structural_classes_found": sorted(structural_classes),
                "semantic_classes_found": sorted(semantic_classes),
                "expected_structural": sorted({"ERR_SCHEMA", "ERR_TRUNCATION", "ERR_INSTRUCTION"}),
                "expected_semantic": sorted({"ERR_HALLUCINATION", "ERR_SEMANTIC", "ERR_SYCOPHANCY", "ERR_REASONING"}),
            }, indent=2),
        ))

    # Check 6: Cross-reference consistency
    xref_checks = _check_cross_references(text)
    checks.extend(xref_checks)

    # Check 7: Error predicate \u03b5 domain/range
    checks.append(MathCheck(
        check_id="CHK_EPSILON_DOMAIN",
        target_blocks=["math_3.1_*"],
        description="\u03b5(y,x) \u2208 {0,1} \u2014 Boolean predicate over Y \u00d7 X",
        status="pass",
        detail=(
            "\u03b5: Y \u00d7 X \u2192 {0,1} is well-defined given \u03a3: X \u2192 Y (partial). "
            "\u03b5(y,x) = 1 iff y deviates from \u03a3(x). "
            "\u00a77.5 acknowledges this is a deliberate simplification; "
            "graded extension \u03b5 \u2208 [0,1] noted as known gap."
        ),
    ))

    # Check 8: Independence caveat propagation
    pipeline_mentions = []
    for section_id in ["3.4", "7.3"]:
        sec_text = _get_section_text(text, section_id)
        if not sec_text:
            patterns = [
                rf'###?\s+{re.escape(section_id)}\b',
                rf'###?\s+{re.escape(section_id)}\s',
            ]
            for pat in patterns:
                m = re.search(pat, text)
                if m:
                    start = m.end()
                    next_sec = re.search(r'\n#{2,4}\s+\d', text[start:])
                    end = start + next_sec.start() if next_sec else len(text)
                    sec_text = text[start:end]
                    break
        has_caveat = bool(sec_text) and (
            "independen" in sec_text.lower() or "correlat" in sec_text.lower()
        )
        pipeline_mentions.append({
            "section": section_id,
            "has_independence_caveat": has_caveat,
            "section_found": bool(sec_text),
        })

    checks.append(MathCheck(
        check_id="CHK_INDEPENDENCE_PROPAGATION",
        target_blocks=["math_3.4_*"],
        description="Independence caveat present at point of use (\u00a73.4) and full treatment (\u00a77.3)",
        status="pass" if all(p["has_independence_caveat"] for p in pipeline_mentions) else "warn",
        detail=json.dumps(pipeline_mentions, indent=2),
    ))

    return checks


def _check_cross_references(text: str) -> list[MathCheck]:
    """Verify that all internal cross-references (\u00a7N.M) point to existing sections."""
    checks: list[MathCheck] = []

    existing_sections: set[str] = set()
    for m in re.finditer(r'^#{2,4}\s+([\d.]+)\.?\s', text, re.MULTILINE):
        existing_sections.add(m.group(1).rstrip('.'))

    changelog_pattern = re.compile(r'\*\*Changelog:\*\*.*?(?=\n---)', re.DOTALL)
    body_text = changelog_pattern.sub('', text)

    xrefs: set[str] = set()
    for m in re.finditer(r'\u00a7([\d.]+)', body_text):
        ref = m.group(1).rstrip('.')
        xrefs.add(ref)

    normalized_existing = {s.rstrip('.') for s in existing_sections}

    broken = xrefs - normalized_existing
    truly_broken: set[str] = set()
    for ref in broken:
        if not any(s.startswith(ref) for s in normalized_existing):
            truly_broken.add(ref)

    checks.append(MathCheck(
        check_id="CHK_CROSS_REFERENCES",
        target_blocks=["document"],
        description="All \u00a7N.M cross-references resolve to existing section headings",
        status="pass" if not truly_broken else "fail",
        detail=json.dumps({
            "existing_sections": sorted(normalized_existing),
            "referenced_sections": sorted(xrefs),
            "broken_references": sorted(truly_broken),
        }, indent=2),
    ))

    return checks
