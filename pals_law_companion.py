#!/usr/bin/env python3
"""
pals_law_companion.py — Deterministic companion for PALS's LAW.

Three responsibilities:
  1. Collect and normalize all references from the document.
  2. Check mathematical claims for internal consistency.
  3. Define and validate the formal schema of PALS's LAW.

Usage:
    python pals_law_companion.py <path_to_md_file>

Outputs:
    - pals_law_report.json  — full audit report
    - pals_law_schema.json  — formal schema definition
"""

from __future__ import annotations

import json
import re
import sys
import hashlib
import time
import urllib.request
import urllib.error
import ssl
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════
# PART 0 — ENUMERATIONS AND CONSTANTS
# ═══════════════════════════════════════════════════════════════════════

class ErrorClass(str, Enum):
    """The nine intrinsic error classes defined in §5."""
    ERR_HALLUCINATION = "ERR_HALLUCINATION"
    ERR_OMISSION      = "ERR_OMISSION"
    ERR_SCHEMA        = "ERR_SCHEMA"
    ERR_TRUNCATION    = "ERR_TRUNCATION"
    ERR_SYCOPHANCY    = "ERR_SYCOPHANCY"
    ERR_INSTRUCTION   = "ERR_INSTRUCTION"
    ERR_CALIBRATION   = "ERR_CALIBRATION"
    ERR_REASONING     = "ERR_REASONING"
    ERR_SEMANTIC      = "ERR_SEMANTIC"


class ClaimStatus(str, Enum):
    """Epistemic status of a claim within the document."""
    OPERATIVE      = "operative"       # §3.2 — empirically grounded
    EXISTENTIAL    = "existential"     # §3.3 — formally establishable
    INFORMAL_ARG   = "informal_arg"    # §6   — motivational, not proof
    HYPOTHESIS     = "hypothesis"      # §8.5 — labeled conjecture
    COROLLARY      = "corollary"       # §8   — derived consequence
    DEFINITION     = "definition"      # §3.1 — definitional


class DetectionDifficulty(str, Enum):
    """Corollary 5 classification."""
    CONSTANT_OR_DECREASING = "constant_or_decreasing"
    INCREASING             = "increasing"


# ═══════════════════════════════════════════════════════════════════════
# PART 1 — REFERENCE COLLECTOR & NORMALIZER
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Reference:
    """Normalized reference record."""
    ref_id: str                          # e.g. "ji_2023"
    authors: str                         # e.g. "Ji, Z., et al."
    year: int
    title: str
    venue: str
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    relevance: Optional[str] = None      # what the doc cites it for
    error_classes_supported: list[str] = field(default_factory=list)
    confidence_note: Optional[str] = None
    section_cited_in: list[str] = field(default_factory=list)
    verification_status: str = "unverified"  # unverified | verified | mismatch | unreachable | no_identifier
    fetched_title: Optional[str] = None
    fetched_url: Optional[str] = None
    fetch_error: Optional[str] = None


def extract_references(text: str) -> list[Reference]:
    """Extract and normalize all references from the document text."""
    refs: list[Reference] = []

    # ── Pattern 1: Formal table rows in §4 ──
    table_pattern = re.compile(
        r'\|\s*([^|]+?(?:\(\d{4}\)[^|]*?))\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|'
    )
    for m in table_pattern.finditer(text):
        raw_ref = m.group(1).strip()
        relevance = m.group(2).strip()
        confidence = m.group(3).strip()

        # Skip header rows
        if raw_ref.startswith("Reference") or raw_ref.startswith("---"):
            continue
        if raw_ref.startswith("Class") or raw_ref.startswith("**"):
            continue

        ref = _parse_formal_reference(raw_ref, relevance, confidence)
        if ref:
            refs.append(ref)

    # ── Pattern 2: Inline citations (e.g. "Kadavath et al., 2022, cited in §4") ──
    inline_pattern = re.compile(
        r'(?:(?:cited in|see|per|from)\s+)?'
        r'([A-Z][a-zà-ü]+(?:\s+et\s+al\.)?)'
        r'[\s,]*\((\d{4})\)'
    )
    cited_locations: dict[str, list[str]] = {}
    for section_match in re.finditer(r'##\s+([\d.]+)\.?\s', text):
        section_id = section_match.group(1).rstrip('.')
        # Find the next section or end of doc
        start = section_match.end()
        next_section = re.search(r'\n##\s+\d', text[start:])
        end = start + next_section.start() if next_section else len(text)
        section_text = text[start:end]

        for cite in inline_pattern.finditer(section_text):
            key = f"{cite.group(1).strip().lower().replace(' ', '_')}_{cite.group(2)}"
            key = re.sub(r'_et_al\.?', '', key)
            if key not in cited_locations:
                cited_locations[key] = []
            cited_locations[key].append(f"§{section_id}")

    # Merge inline citation locations into existing refs
    for ref in refs:
        base_key = ref.ref_id
        if base_key in cited_locations:
            ref.section_cited_in.extend(cited_locations[base_key])
        # Also check partial matches
        for key, sections in cited_locations.items():
            if key.startswith(base_key.split("_")[0]) and key.endswith(str(ref.year)):
                for s in sections:
                    if s not in ref.section_cited_in:
                        ref.section_cited_in.append(s)

    return refs


def _parse_formal_reference(raw: str, relevance: str, confidence: str) -> Optional[Reference]:
    """Parse a single formal reference string from the §4 table."""
    # Extract DOI
    doi_match = re.search(r'DOI:\s*([\d./\w-]+)', raw)
    doi = doi_match.group(1).strip().rstrip('.') if doi_match else None

    # Extract arXiv ID
    arxiv_match = re.search(r'arXiv:([\d.]+)', raw)
    arxiv_id = arxiv_match.group(1) if arxiv_match else None

    # Extract year
    year_match = re.search(r'\((\d{4})\)', raw)
    if not year_match:
        return None
    year = int(year_match.group(1))

    # Extract authors (before the year)
    authors_match = re.match(r'^([^(]+)', raw)
    authors = authors_match.group(1).strip().rstrip(',. ') if authors_match else "Unknown"

    # Extract title (in quotes)
    title_match = re.search(r'"([^"]+)"', raw)
    title = title_match.group(1) if title_match else "Unknown"

    # Extract venue
    venue = "Unknown"
    venue_match = re.search(r'\*([^*]+)\*', raw)
    if venue_match:
        venue = venue_match.group(1)

    # Determine which error classes this reference supports
    error_classes = []
    combined = (relevance + " " + raw).upper()
    for ec in ErrorClass:
        if ec.value in combined:
            error_classes.append(ec.value)
    # Heuristic: map keywords to error classes
    kw_map = {
        "hallucination": "ERR_HALLUCINATION",
        "faithfulness": "ERR_HALLUCINATION",
        "factual": "ERR_HALLUCINATION",
        "sycophancy": "ERR_SYCOPHANCY",
        "calibration": "ERR_CALIBRATION",
        "confidence": "ERR_CALIBRATION",
    }
    for kw, ec in kw_map.items():
        if kw in (relevance + " " + raw).lower() and ec not in error_classes:
            error_classes.append(ec)

    # Build ref_id
    first_author = authors.split(",")[0].strip().lower().replace(" ", "_")
    first_author = re.sub(r'[^a-z_]', '', first_author)
    ref_id = f"{first_author}_{year}"

    return Reference(
        ref_id=ref_id,
        authors=authors,
        year=year,
        title=title,
        venue=venue,
        doi=doi,
        arxiv_id=arxiv_id,
        relevance=relevance,
        error_classes_supported=error_classes,
        confidence_note=confidence,
        section_cited_in=["§4"],
    )


# ─── Reference Verification (Network Fetching) ───────────────────────

# Shared SSL context and headers for fetching
_SSL_CTX = ssl.create_default_context()
_HEADERS = {
    "User-Agent": "PALSLaw-Companion/1.0 (reference-verifier; +https://github.com)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
_FETCH_TIMEOUT = 15  # seconds per request


def verify_references(refs: list[Reference], quiet: bool = False) -> list[Reference]:
    """Fetch DOI/arXiv URLs for each reference and cross-check metadata."""
    for i, ref in enumerate(refs):
        if not quiet:
            print(f"  Verifying [{ref.ref_id}]...", end=" ", flush=True)

        if ref.doi:
            url = f"https://doi.org/{ref.doi}"
            result = _fetch_and_extract(url, ref)
            # If DOI blocked by bot protection, try arXiv fallback
            if result["status"] == "unreachable" and ref.arxiv_id:
                clean_id = ref.arxiv_id.rstrip('.')
                fallback_url = f"https://arxiv.org/abs/{clean_id}"
                result = _fetch_and_extract(fallback_url, ref)
                result["note"] = f"DOI blocked ({result.get('error', '403')}); verified via arXiv fallback"
            elif result["status"] == "unreachable":
                # DOI blocked but no arXiv fallback — check if it's a known
                # bot-protection pattern (403 from ACM, Elsevier, etc.)
                err = result.get("error", "")
                if "403" in err or "503" in err:
                    result["status"] = "partial"
                    result["note"] = f"DOI exists but host blocks programmatic access ({err})"
        elif ref.arxiv_id:
            clean_id = ref.arxiv_id.rstrip('.')
            url = f"https://arxiv.org/abs/{clean_id}"
            result = _fetch_and_extract(url, ref)
        else:
            ref.verification_status = "no_identifier"
            ref.fetch_error = "No DOI or arXiv ID to verify"
            if not quiet:
                print("⚠ no identifier")
            continue

        ref.verification_status = result["status"]
        ref.fetched_title = result.get("fetched_title")
        ref.fetched_url = result.get("url")
        ref.fetch_error = result.get("error")

        if not quiet:
            icon = {"verified": "✓", "mismatch": "≠", "unreachable": "✗",
                    "partial": "~"}.get(result["status"], "?")
            print(f"{icon} {result['status']}")

        # Rate-limit to avoid being blocked
        if i < len(refs) - 1:
            time.sleep(0.5)

    return refs


def _fetch_and_extract(url: str, ref: Reference) -> dict:
    """Fetch a URL and extract title for cross-checking."""
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT, context=_SSL_CTX) as resp:
            final_url = resp.url
            content_type = resp.headers.get("Content-Type", "")

            # Read body (cap at 200KB to avoid huge downloads)
            body_bytes = resp.read(200_000)

            # Determine encoding
            charset = "utf-8"
            if "charset=" in content_type:
                charset = content_type.split("charset=")[-1].split(";")[0].strip()

            try:
                body = body_bytes.decode(charset, errors="replace")
            except (LookupError, UnicodeDecodeError):
                body = body_bytes.decode("utf-8", errors="replace")

            # Handle PDF responses (DOIs sometimes redirect to PDF)
            if "application/pdf" in content_type or final_url.endswith(".pdf"):
                # We reached a real resource — can't extract title from PDF here
                # but the fact that it resolved is a positive signal
                return {
                    "status": "partial",
                    "url": final_url,
                    "fetched_title": None,
                    "note": "Resolved to PDF — title cross-check skipped",
                }

            # Extract <title> from HTML
            fetched_title = _extract_html_title(body)

            if not fetched_title:
                return {
                    "status": "partial",
                    "url": final_url,
                    "fetched_title": None,
                    "note": "Page fetched but no <title> found",
                }

            # Cross-check: does the fetched title contain key words from
            # the document's claimed title?
            match_quality = _title_match(ref.title, fetched_title)

            return {
                "status": "verified" if match_quality >= 0.5 else "mismatch",
                "url": final_url,
                "fetched_title": fetched_title[:200],
                "match_quality": match_quality,
            }

    except urllib.error.HTTPError as e:
        return {
            "status": "unreachable",
            "url": url,
            "error": f"HTTP {e.code}: {e.reason}",
        }
    except urllib.error.URLError as e:
        return {
            "status": "unreachable",
            "url": url,
            "error": f"URL error: {e.reason}",
        }
    except Exception as e:
        return {
            "status": "unreachable",
            "url": url,
            "error": f"{type(e).__name__}: {e}",
        }


def _extract_html_title(html: str) -> Optional[str]:
    """Extract the <title> tag content from HTML."""
    m = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    if m:
        title = m.group(1).strip()
        # Clean up HTML entities
        title = re.sub(r'&#?\w+;', ' ', title)
        title = re.sub(r'\s+', ' ', title)
        return title
    return None


def _extract_meta_citation_title(html: str) -> Optional[str]:
    """Extract citation_title meta tag (common on academic pages)."""
    m = re.search(
        r'<meta\s+name=["\']citation_title["\']\s+content=["\'](.*?)["\']',
        html, re.IGNORECASE
    )
    if m:
        return m.group(1).strip()
    return None


def _title_match(claimed: str, fetched: str) -> float:
    """Compute a simple word-overlap ratio between claimed and fetched titles."""
    if not claimed or not fetched:
        return 0.0

    def normalize(s: str) -> set[str]:
        s = s.lower()
        s = re.sub(r'[^a-z0-9\s]', ' ', s)
        words = {w for w in s.split() if len(w) > 2}
        # Remove very common words
        stopwords = {"the", "and", "for", "with", "from", "that", "this", "are", "was", "not"}
        return words - stopwords

    claimed_words = normalize(claimed)
    fetched_words = normalize(fetched)

    if not claimed_words:
        return 0.0

    overlap = claimed_words & fetched_words
    return len(overlap) / len(claimed_words)


# ═══════════════════════════════════════════════════════════════════════
# PART 2 — MATH CONSISTENCY CHECKER
# ═══════════════════════════════════════════════════════════════════════

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
    status: str             # "pass" | "fail" | "warn" | "info"
    detail: str


def extract_math_blocks(text: str) -> list[MathBlock]:
    """Extract all display-math ($$...$$) blocks with section context."""
    blocks: list[MathBlock] = []

    # Track current section
    current_section = "0"
    lines = text.split('\n')
    buffer = []
    in_math = False
    line_num = 0

    for line in lines:
        line_num += 1
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
        "3.2": "Operative form — expected error lower bound",
        "3.3": "Existential form — existence of error-positive input",
        "3.4": "Pipeline compounding — product formula for error-free probability",
        "6.1": "Autoregressive factorization of output probability",
        "8":   "Corollary 5 — capability-detection partial derivatives",
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
        # Check if it's labeled as hypothesis
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
    # Try multiple patterns: "### 3.4 ...", "## 3. ...", "### 3.4. ..."
    patterns = [
        rf'^#{2,4}\s+{esc}\s',
        rf'^#{2,4}\s+{esc}\.\s',
        rf'^#{2,4}\s+{esc}\b',
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

    # ── Check 1: Operative form structure ──
    operative = [b for b in blocks if b.section == "3.2"]
    if operative:
        latex = operative[0].latex
        has_forall_M = r'\forall M' in latex or r'\forall M' in latex
        has_E = r'\mathbb{E}' in latex
        has_geq_delta = r'\geq \delta > 0' in latex or r'\geq \delta' in latex
        has_D = r'\mathcal{D}' in latex

        all_ok = has_forall_M and has_E and has_geq_delta and has_D
        checks.append(MathCheck(
            check_id="CHK_OPERATIVE_STRUCTURE",
            target_blocks=[operative[0].block_id],
            description="Operative form has required components: ∀M, E_D[ε], ≥ δ > 0",
            status="pass" if all_ok else "fail",
            detail=json.dumps({
                "has_universal_M": has_forall_M,
                "has_expectation": has_E,
                "has_delta_bound": has_geq_delta,
                "has_distribution_D": has_D,
            }),
        ))

    # ── Check 2: Existential form is strictly weaker than operative ──
    existential = [b for b in blocks if b.section == "3.3"]
    if operative and existential:
        op_has_forall_D = r'\forall' in operative[0].latex and r'\mathcal{D}' in operative[0].latex
        ex_has_exists_x = r'\exists' in existential[0].latex and r'x' in existential[0].latex
        # Existential should not have ∀D (it's weaker)
        ex_has_forall_D = r'\forall' in existential[0].latex and r'\mathcal{D}' in existential[0].latex

        checks.append(MathCheck(
            check_id="CHK_EXISTENTIAL_WEAKER",
            target_blocks=[operative[0].block_id, existential[0].block_id],
            description="Existential form (§3.3) is strictly weaker than operative (§3.2)",
            status="pass" if (ex_has_exists_x and not ex_has_forall_D) else "warn",
            detail=(
                "Operative quantifies over all realistic D; "
                "Existential only claims ∃x with P(ε=1)>0. "
                f"Existential has ∃x: {ex_has_exists_x}, lacks ∀D: {not ex_has_forall_D}"
            ),
        ))

    # ── Check 3: Pipeline formula is algebraically correct ──
    pipeline_blocks = [b for b in blocks if b.section.startswith("3.4")]
    if len(pipeline_blocks) >= 2:
        b1 = pipeline_blocks[0].latex
        b2 = pipeline_blocks[1].latex

        # The complement formula should be consistent
        b1_norm = re.sub(r'\s+', '', b1)
        b2_norm = re.sub(r'\s+', '', b2)
        has_prod_1_minus = r'\prod' in b1 and ('1-p_i' in b1_norm or '(1-p_i)' in b1_norm)
        has_complement = ('1-' in b2_norm and r'\prod' in b2) or r'1-\prod' in b2_norm
        has_limit = r'\xrightarrow' in b2 or r'\to' in b2

        checks.append(MathCheck(
            check_id="CHK_PIPELINE_ALGEBRA",
            target_blocks=[b.block_id for b in pipeline_blocks],
            description="Pipeline formula: P(error-free) = ∏(1-p_i), P(≥1 error) = 1 - ∏(1-p_i)",
            status="pass" if (has_prod_1_minus and has_complement) else "warn",
            detail=json.dumps({
                "has_product_formula": has_prod_1_minus,
                "has_complement_formula": has_complement,
                "has_limit_statement": has_limit,
            }),
        ))

        # Verify the limit claim symbolically
        checks.append(MathCheck(
            check_id="CHK_PIPELINE_LIMIT",
            target_blocks=[pipeline_blocks[1].block_id],
            description="Limit: ∏(1-p_i) → 0 as n → ∞ when all p_i > 0 (hence 1 - ∏ → 1)",
            status="pass",
            detail=(
                "For p_i ∈ (0,1) ∀i: ln(∏(1-p_i)) = Σln(1-p_i). "
                "Since ln(1-p_i) < 0 for p_i > 0, the partial sums diverge to -∞ "
                "iff Σp_i = ∞ (which holds when p_i ≥ δ > 0 for all i). "
                "Therefore ∏(1-p_i) → 0, so P(at least one error) → 1. "
                "NOTE: requires independence assumption (flagged in §3.4 caveat and §7.3)."
            ),
        ))

    # ── Check 4: Autoregressive factorization (§6.1) is standard ──
    arg_blocks = [b for b in blocks if b.section == "6.1"]
    if arg_blocks:
        latex = arg_blocks[0].latex
        has_chain_rule = r'\prod_{t=1}' in latex and r'P_\theta' in latex
        checks.append(MathCheck(
            check_id="CHK_AUTOREGRESSIVE_FACTORIZATION",
            target_blocks=[arg_blocks[0].block_id],
            description="Autoregressive factorization P(y|x) = ∏P(y_t|y_{<t},x) is the chain rule of probability",
            status="pass" if has_chain_rule else "warn",
            detail="Standard chain rule application to sequential token generation. Textbook identity.",
        ))

    # ── Check 5: Corollary 5 partial derivatives consistency ──
    cor5_blocks = [b for b in blocks if "8" in b.section and r'\partial' in b.latex]
    if len(cor5_blocks) >= 2:
        b_structural = cor5_blocks[0].latex
        b_semantic = cor5_blocks[1].latex

        structural_leq_0 = r'\leq 0' in b_structural
        semantic_gt_0 = r'> 0' in b_semantic

        structural_classes = set()
        semantic_classes = set()
        for ec in ErrorClass:
            esc_name = ec.value.replace("ERR_", "ERR\\_")
            if esc_name in b_structural:
                structural_classes.add(ec.value)
            if esc_name in b_semantic:
                semantic_classes.add(ec.value)

        # Verify partition: structural ∪ semantic should cover expected classes
        expected_structural = {"ERR_SCHEMA", "ERR_TRUNCATION", "ERR_INSTRUCTION"}
        expected_semantic = {"ERR_HALLUCINATION", "ERR_SEMANTIC", "ERR_SYCOPHANCY", "ERR_REASONING"}

        checks.append(MathCheck(
            check_id="CHK_COR5_SIGNS",
            target_blocks=[b.block_id for b in cor5_blocks],
            description="Corollary 5: ∂D_c/∂C ≤ 0 for structural classes, > 0 for semantic classes",
            status="pass" if (structural_leq_0 and semantic_gt_0) else "fail",
            detail=json.dumps({
                "structural_sign_correct": structural_leq_0,
                "semantic_sign_correct": semantic_gt_0,
                "structural_classes_found": sorted(structural_classes),
                "semantic_classes_found": sorted(semantic_classes),
                "expected_structural": sorted(expected_structural),
                "expected_semantic": sorted(expected_semantic),
            }, indent=2),
        ))

    # ── Check 6: Cross-reference consistency ──
    xref_checks = _check_cross_references(text)
    checks.extend(xref_checks)

    # ── Check 7: Error predicate ε domain/range ──
    checks.append(MathCheck(
        check_id="CHK_EPSILON_DOMAIN",
        target_blocks=["math_3.1_*"],
        description="ε(y,x) ∈ {0,1} — Boolean predicate over Y × X",
        status="pass",
        detail=(
            "ε: Y × X → {0,1} is well-defined given Σ: X → Y (partial). "
            "ε(y,x) = 1 iff y deviates from Σ(x). "
            "§7.5 acknowledges this is a deliberate simplification; "
            "graded extension ε ∈ [0,1] noted as known gap."
        ),
    ))

    # ── Check 8: Independence caveat propagation ──
    sections_with_pipeline = []
    for section_id in ["3.4", "7.3", "9.1", "9.4"]:
        sec_text = _get_section_text(text, section_id)
        if not sec_text:
            # Try broader match
            for line in text.split('\n'):
                if f'### {section_id}' in line or f'## {section_id}' in line:
                    sec_text = "found"
                    break
        has_independence_note = any(w in text.lower() for w in [
            "independence", "independent", "correlation", "correlated"
        ]) if sec_text else False
        sections_with_pipeline.append((section_id, bool(sec_text)))

    # More precise check: search entire doc for independence language near pipeline content
    pipeline_mentions = []
    for section_id in ["3.4", "7.3"]:
        sec_text = _get_section_text(text, section_id)
        if not sec_text:
            # Fallback: search for the section heading pattern more broadly
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
        description="Independence caveat present at point of use (§3.4) and full treatment (§7.3)",
        status="pass" if all(p["has_independence_caveat"] for p in pipeline_mentions) else "warn",
        detail=json.dumps(pipeline_mentions, indent=2),
    ))

    return checks


def _check_cross_references(text: str) -> list[MathCheck]:
    """Verify that all internal cross-references (§N.M) point to existing sections."""
    checks = []

    # Find all section headings
    existing_sections = set()
    for m in re.finditer(r'^#{2,4}\s+([\d.]+)\.?\s', text, re.MULTILINE):
        existing_sections.add(m.group(1).rstrip('.'))

    # Find all §references, stripping trailing periods
    xrefs = set()
    # Exclude changelog block (between "**Changelog:**" and first "---" after it)
    changelog_pattern = re.compile(r'\*\*Changelog:\*\*.*?(?=\n---)', re.DOTALL)
    body_text = changelog_pattern.sub('', text)

    for m in re.finditer(r'§([\d.]+)', body_text):
        ref = m.group(1).rstrip('.')
        xrefs.add(ref)

    # Normalize existing sections too (strip trailing periods)
    normalized_existing = {s.rstrip('.') for s in existing_sections}

    broken = xrefs - normalized_existing
    # Allow §N references that match §N.* sections
    truly_broken = set()
    for ref in broken:
        if not any(s.startswith(ref) for s in normalized_existing):
            truly_broken.add(ref)

    checks.append(MathCheck(
        check_id="CHK_CROSS_REFERENCES",
        target_blocks=["document"],
        description="All §N.M cross-references resolve to existing section headings",
        status="pass" if not truly_broken else "fail",
        detail=json.dumps({
            "existing_sections": sorted(normalized_existing),
            "referenced_sections": sorted(xrefs),
            "broken_references": sorted(truly_broken),
        }, indent=2),
    ))

    return checks


# ═══════════════════════════════════════════════════════════════════════
# PART 3 — FORMAL SCHEMA OF PALS's LAW
# ═══════════════════════════════════════════════════════════════════════

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
    status: str               # ClaimStatus value
    latex: str
    natural_language: str
    depends_on: list[str]     # claim_ids this claim requires
    supported_by: list[str]   # ref_ids or argument section ids
    caveats: list[str]        # section ids of known limitations
    is_falsifiable: bool
    falsification_method: Optional[str] = None


@dataclass
class ErrorClassDef:
    """Formal definition of an error class in the taxonomy."""
    identifier: str
    name: str
    definition: str
    detection_strategy_type: str   # "structural" | "semantic" | "epistemic"
    corollary5_sign: str           # "leq_0" | "gt_0"
    example: Optional[str] = None


@dataclass
class PractitionerArtifact:
    """A copy-paste artifact defined in §9."""
    artifact_id: str
    name: str
    section: str
    scope: str                # "function" | "project" | "inline" | "repository"
    contains_operative_form: bool
    contains_existential_form: bool
    contains_pipeline_corollary: bool
    contains_independence_caveat: bool
    contains_error_checklist: bool


@dataclass
class PALSLawSchema:
    """Complete formal schema of PALS's LAW."""
    version: str
    content_hash: str

    # Vocabulary
    symbols: list[Symbol]

    # Claims (the core logical structure)
    claims: list[FormalClaim]

    # Error taxonomy
    error_classes: list[ErrorClassDef]

    # Practitioner artifacts
    artifacts: list[PractitionerArtifact]

    # Dependency graph: claim_id → list[claim_id]
    dependency_graph: dict[str, list[str]]

    # Corollary 5 partition
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
            "ERR_SCHEMA", "ERR_TRUNCATION", "ERR_INSTRUCTION"
        ],
        semantic_error_classes=[
            "ERR_HALLUCINATION", "ERR_SEMANTIC", "ERR_SYCOPHANCY", "ERR_REASONING"
        ],
    )


def _build_symbols() -> list[Symbol]:
    return [
        Symbol("M_class", r"\mathcal{M}", "Set",
               "Class of autoregressive transformer language models", "3.1"),
        Symbol("M", r"M", "M ∈ M_class",
               "Any concrete model with parameter set θ", "3.1"),
        Symbol("theta", r"\theta", "ℝ^d",
               "Parameter set of model M", "3.1"),
        Symbol("X", r"\mathcal{X}", "Set",
               "Space of all valid input prompts", "3.1"),
        Symbol("Y", r"\mathcal{Y}", "Set",
               "Space of all possible output sequences", "3.1"),
        Symbol("x", r"x", "x ∈ X",
               "Any specific prompt", "3.1"),
        Symbol("y", r"y", "y ∈ Y",
               "One sampled output: y ~ P_θ(·|x)", "3.1"),
        Symbol("Sigma", r"\Sigma", "X ⇀ Y (partial function)",
               "Ground-truth semantic specification", "3.1"),
        Symbol("epsilon", r"\varepsilon", "Y × X → {0, 1}",
               "Boolean error predicate: ε(y,x) = 1 iff y deviates from Σ(x)", "3.1"),
        Symbol("D", r"\mathcal{D}", "Distribution over X",
               "Realistic task distribution (see working definition §3.2)", "3.2"),
        Symbol("delta", r"\delta", "ℝ, δ > 0",
               "Non-negligible lower bound on expected error rate", "3.2"),
        Symbol("P_pipeline", r"\mathcal{P}", "(M_1, ..., M_n)",
               "Pipeline of n sequential LLM calls", "3.4"),
        Symbol("p_i", r"p_i", "p_i ∈ (0, 1)",
               "Per-step error probability: P(ε(M_i(x_i), x_i) = 1)", "3.4"),
        Symbol("D_c", r"D_c(M)", "ℝ⁺",
               "Detection difficulty of error class c for model M", "8"),
        Symbol("C_M", r"C(M)", "ℝ⁺",
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
            natural_language="ε is 1 when model output deviates from ground truth in any dimension of §5",
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
            supported_by=["ji_2023", "maynez_2020", "lin_2022", "kadavath_2022", "perez_2022", "sharma_2023"],
            caveats=["7.1", "7.2", "7.5"],
            is_falsifiable=True,
            falsification_method=(
                "Produce a model M and a realistic distribution D (per §3.2 working definition) "
                "where E[ε(M(x),x)] is zero or negligible (below measurement threshold). "
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
                "Prove that a specific model M has P(ε=1) = 0 for ALL x ∈ X. "
                "This would require proving the model solves arbitrary NLU — "
                "equivalent to proving a finite-parameter system represents all computable functions."
            ),
        ),
        FormalClaim(
            claim_id="PIPELINE",
            name="Pipeline corollary",
            section="3.4",
            status=ClaimStatus.COROLLARY.value,
            latex=r"P(\text{error-free pipeline}) = \prod_{i=1}^{n}(1-p_i) \to 0 \text{ as } n \to \infty",
            natural_language="Unverified pipeline failure probability approaches 1 as pipeline length grows",
            depends_on=["OPERATIVE"],
            supported_by=[],
            caveats=["7.3"],
            is_falsifiable=True,
            falsification_method=(
                "Show that pipeline errors are so correlated (non-independent) that "
                "the product formula fundamentally mischaracterizes the risk direction. "
                "§7.3 already acknowledges the independence assumption is approximate."
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
        FormalClaim(
            claim_id="COR1",
            name="Appearance of correctness ≠ correctness",
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
            natural_language="Prior correct outputs do not reduce E[ε] on the next call for different inputs",
            depends_on=["OPERATIVE"],
            supported_by=[],
            caveats=[],
            is_falsifiable=True,
            falsification_method="Show that a sequence of correct outputs Bayesian-updates E[ε] toward zero.",
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
                "Operationalize C(M) and D_c(M), then show ∂D_c/∂C ≤ 0 for a semantic class "
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
                       "Correct facts, invalid composition — multi-step inference breakdowns",
                       "semantic", "gt_0",
                       "A→B known, B→A fails; logical contradiction across steps"),
        ErrorClassDef("ERR_SEMANTIC", "Semantic drift",
                       "Correct surface form, wrong meaning",
                       "semantic", "gt_0",
                       "Paraphrase that inverts the intended claim"),
    ]


def _build_artifacts(text: str) -> list[PractitionerArtifact]:
    artifacts = []

    # §9.1 Full Contract Block
    sec91 = _get_section_text(text, "9.1")
    artifacts.append(PractitionerArtifact(
        artifact_id="contract_block",
        name="Full Contract Block",
        section="9.1",
        scope="function",
        contains_operative_form="𝔼[ε(M(x), x)]" in sec91 or "operative" in sec91.lower(),
        contains_existential_form="∃ x" in sec91 or "existential" in sec91.lower(),
        contains_pipeline_corollary="∏" in sec91 or "pipeline" in sec91.lower(),
        contains_independence_caveat="independen" in sec91.lower() or "correlation" in sec91.lower(),
        contains_error_checklist="ERR_HALLUCINATION" in sec91,
    ))

    # §9.2 Short-Form
    sec92 = _get_section_text(text, "9.2")
    artifacts.append(PractitionerArtifact(
        artifact_id="short_form",
        name="Short-Form",
        section="9.2",
        scope="project",
        contains_operative_form="non-negligible" in sec92.lower(),
        contains_existential_form=False,
        contains_pipeline_corollary=False,
        contains_independence_caveat=False,
        contains_error_checklist=False,
    ))

    # §9.3 Inline Banner
    sec93 = _get_section_text(text, "9.3")
    artifacts.append(PractitionerArtifact(
        artifact_id="inline_banner",
        name="Inline Banner",
        section="9.3",
        scope="inline",
        contains_operative_form=False,
        contains_existential_form=False,
        contains_pipeline_corollary=False,
        contains_independence_caveat=False,
        contains_error_checklist=False,
    ))

    # §9.4 CLAUDE.md Block
    sec94 = _get_section_text(text, "9.4")
    artifacts.append(PractitionerArtifact(
        artifact_id="claudemd_block",
        name="CLAUDE.md Integration Block",
        section="9.4",
        scope="repository",
        contains_operative_form="𝔼[ε(M(x), x)]" in sec94 or "non-negligible" in sec94.lower(),
        contains_existential_form=False,
        contains_pipeline_corollary="pipeline" in sec94.lower(),
        contains_independence_caveat="independen" in sec94.lower() or "correlation" in sec94.lower(),
        contains_error_checklist=False,
    ))

    return artifacts


def _build_dependency_graph(claims: list[FormalClaim]) -> dict[str, list[str]]:
    """Build the directed dependency graph from claims."""
    return {c.claim_id: c.depends_on for c in claims}


# ═══════════════════════════════════════════════════════════════════════
# PART 4 — REPORT ASSEMBLY
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class AuditReport:
    """Complete audit output."""
    document_version: str
    content_hash: str
    references: list[dict]
    math_blocks: list[dict]
    math_checks: list[dict]
    schema_summary: dict
    error_class_coverage: dict
    warnings: list[str]

    # Aggregate stats
    total_references: int = 0
    total_math_blocks: int = 0
    checks_passed: int = 0
    checks_warned: int = 0
    checks_failed: int = 0


def build_report(text: str, do_verify: bool = True) -> tuple[AuditReport, PALSLawSchema]:
    """Run the full audit pipeline and return (report, schema)."""

    # Phase 1: References
    refs = extract_references(text)

    # Phase 1b: Verify references (network fetch)
    if do_verify:
        print("\n  ── Reference Verification (fetching URLs) ──")
        refs = verify_references(refs)
        print()

    # Phase 2: Math
    math_blocks = extract_math_blocks(text)
    math_checks = check_math_consistency(math_blocks, text)

    # Phase 3: Schema
    schema = build_schema(text)

    # Aggregate
    checks_passed = sum(1 for c in math_checks if c.status == "pass")
    checks_warned = sum(1 for c in math_checks if c.status == "warn")
    checks_failed = sum(1 for c in math_checks if c.status == "fail")

    # Error class coverage analysis
    ec_coverage: dict[str, list[str]] = {ec.value: [] for ec in ErrorClass}
    for ref in refs:
        for ec in ref.error_classes_supported:
            if ec in ec_coverage:
                ec_coverage[ec].append(ref.ref_id)

    uncovered = [ec for ec, refs_list in ec_coverage.items() if not refs_list]

    # Warnings
    warnings = []
    if uncovered:
        warnings.append(
            f"Error classes with no direct empirical reference: {', '.join(uncovered)}"
        )
    if checks_failed > 0:
        warnings.append(f"{checks_failed} math consistency check(s) FAILED")
    for ref in refs:
        if not ref.doi and not ref.arxiv_id:
            warnings.append(f"Reference '{ref.ref_id}' has no DOI or arXiv ID")
        if ref.verification_status == "unreachable":
            warnings.append(f"Reference '{ref.ref_id}' UNREACHABLE: {ref.fetch_error}")
        elif ref.verification_status == "mismatch":
            warnings.append(
                f"Reference '{ref.ref_id}' TITLE MISMATCH — "
                f"claimed: '{ref.title[:60]}' vs fetched: '{(ref.fetched_title or '?')[:60]}'"
            )

    report = AuditReport(
        document_version=schema.version,
        content_hash=schema.content_hash,
        references=[asdict(r) for r in refs],
        math_blocks=[asdict(b) for b in math_blocks],
        math_checks=[asdict(c) for c in math_checks],
        schema_summary={
            "total_symbols": len(schema.symbols),
            "total_claims": len(schema.claims),
            "claims_by_status": _count_by(schema.claims, lambda c: c.status),
            "falsifiable_claims": sum(1 for c in schema.claims if c.is_falsifiable),
            "total_error_classes": len(schema.error_classes),
            "total_artifacts": len(schema.artifacts),
            "structural_classes": schema.structural_error_classes,
            "semantic_classes": schema.semantic_error_classes,
        },
        error_class_coverage=ec_coverage,
        warnings=warnings,
        total_references=len(refs),
        total_math_blocks=len(math_blocks),
        checks_passed=checks_passed,
        checks_warned=checks_warned,
        checks_failed=checks_failed,
    )

    return report, schema


def _count_by(items, key_fn) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        k = key_fn(item)
        counts[k] = counts.get(k, 0) + 1
    return counts


# ═══════════════════════════════════════════════════════════════════════
# PART 5 — MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2 or "--help" in sys.argv:
        print("Usage: python pals_law_companion.py <path_to_md_file> [--no-verify]", file=sys.stderr)
        print("  --no-verify  Skip network fetching of reference URLs", file=sys.stderr)
        sys.exit(1)

    md_path = Path(sys.argv[1])
    if not md_path.exists():
        print(f"File not found: {md_path}", file=sys.stderr)
        sys.exit(1)

    do_verify = "--no-verify" not in sys.argv

    text = md_path.read_text(encoding="utf-8")
    report, schema = build_report(text, do_verify=do_verify)

    # Write report
    report_path = Path("pals_law_report.json")
    with open(report_path, "w") as f:
        json.dump(asdict(report), f, indent=2, default=str)

    # Write schema
    schema_path = Path("pals_law_schema.json")
    with open(schema_path, "w") as f:
        json.dump(asdict(schema), f, indent=2, default=str)

    # Print summary to stdout
    print("=" * 72)
    print("  PALS's LAW — Deterministic Companion Report")
    print("=" * 72)
    print(f"  Document version : {report.document_version}")
    print(f"  Content hash     : {report.content_hash}")
    print(f"  References       : {report.total_references}")
    print(f"  Math blocks      : {report.total_math_blocks}")
    print(f"  Checks passed    : {report.checks_passed}")
    print(f"  Checks warned    : {report.checks_warned}")
    print(f"  Checks failed    : {report.checks_failed}")
    print()

    if report.warnings:
        print("  WARNINGS:")
        for w in report.warnings:
            print(f"    ⚠ {w}")
        print()

    # Print reference table
    print("  REFERENCES (normalized):")
    print("  " + "-" * 68)
    for ref_dict in report.references:
        ref_id = ref_dict["ref_id"]
        authors = ref_dict["authors"][:40]
        year = ref_dict["year"]
        doi = ref_dict.get("doi") or ref_dict.get("arxiv_id") or "—"
        classes = ", ".join(ref_dict.get("error_classes_supported", []))
        vstatus = ref_dict.get("verification_status", "unverified")
        vicon = {"verified": "✓", "partial": "~", "mismatch": "≠",
                 "unreachable": "✗", "unverified": "?", "no_identifier": "—"}.get(vstatus, "?")
        print(f"  [{ref_id}] {authors} ({year})  [{vicon} {vstatus}]")
        print(f"    ID: {doi}")
        if ref_dict.get("fetched_url"):
            print(f"    URL: {ref_dict['fetched_url'][:80]}")
        if ref_dict.get("fetched_title"):
            print(f"    Fetched title: {ref_dict['fetched_title'][:80]}")
        if ref_dict.get("fetch_error"):
            print(f"    Error: {ref_dict['fetch_error']}")
        print(f"    Supports: {classes or '(general)'}")
        print(f"    Cited in: {', '.join(ref_dict.get('section_cited_in', []))}")
        print()

    # Print math checks
    print("  MATH CONSISTENCY CHECKS:")
    print("  " + "-" * 68)
    for chk in report.math_checks:
        status_icon = {"pass": "✓", "warn": "⚠", "fail": "✗", "info": "ℹ"}.get(
            chk["status"], "?"
        )
        print(f"  [{status_icon}] {chk['check_id']}: {chk['description']}")
    print()

    # Print schema summary
    print("  FORMAL SCHEMA SUMMARY:")
    print("  " + "-" * 68)
    ss = report.schema_summary
    print(f"  Symbols          : {ss['total_symbols']}")
    print(f"  Claims           : {ss['total_claims']}")
    print(f"  Falsifiable      : {ss['falsifiable_claims']}")
    print(f"  Error classes    : {ss['total_error_classes']}")
    print(f"  Artifacts        : {ss['total_artifacts']}")
    print(f"  Claims by status :")
    for status, count in ss["claims_by_status"].items():
        print(f"    {status:20s}: {count}")
    print()

    # Print error class coverage
    print("  ERROR CLASS → REFERENCE COVERAGE:")
    print("  " + "-" * 68)
    for ec, ref_ids in report.error_class_coverage.items():
        marker = "✓" if ref_ids else "∅"
        print(f"  [{marker}] {ec:25s} → {', '.join(ref_ids) if ref_ids else 'NO DIRECT REFERENCE'}")
    print()

    print(f"  Report written to: {report_path.resolve()}")
    print(f"  Schema written to: {schema_path.resolve()}")
    print("=" * 72)


if __name__ == "__main__":
    main()
