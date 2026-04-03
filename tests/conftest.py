"""Shared fixtures for pals_check tests."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
PROJECT_ROOT = Path(__file__).parent.parent


@pytest.fixture
def real_md_text() -> str:
    """Load the actual PALS's LAW markdown document."""
    md_path = PROJECT_ROOT / "PALS_LAW-v1.5.4.md"
    return md_path.read_text(encoding="utf-8")


@pytest.fixture
def minimal_md_text() -> str:
    """A minimal synthetic document with all required structural elements."""
    return """\
---
disclaimer:
  generated_by: "test"
---

# PALS's LAW

**Document version:** 0.0.1

---

## 1. Preamble

This is the preamble.

---

## 3. Formal Statement

### 3.1 Definitions

Let M be a model.

$$
\\varepsilon(y, x) \\in \\{0, 1\\}
$$

### 3.2 Operative Form

$$
\\forall M \\in \\mathcal{M},\\ \\forall \\text{ realistic } \\mathcal{D}: \\mathbb{E}_{x \\sim \\mathcal{D}}[\\varepsilon(M(x), x)] \\geq \\delta > 0
$$

### 3.3 Existential Form

$$
\\forall M \\in \\mathcal{M}: \\exists x \\in \\mathcal{X} \\text{ s.t. } P_\\theta(\\varepsilon(M(x),x)=1) > 0
$$

### 3.4 Pipeline Compounding

Assuming independence between stages:

$$
P(\\text{error-free}) = \\prod_{i=1}^{n}(1-p_i)
$$

$$
P(\\geq 1 \\text{ error}) = 1 - \\prod_{i=1}^{n}(1-p_i) \\to 1 \\text{ as } n \\to \\infty
$$

---

## 4. Empirical Support

| Reference | Relevance | Confidence |
| --- | --- | --- |
| Ji, Z., et al. (2023), "Survey of Hallucination in NLG," *ACM Computing Surveys*, DOI: 10.1145/3571730 | hallucination rates | High — meta-analysis |
| Kadavath, S., et al. (2022), "Language Models Know What They Don't Know," arXiv:2207.05221 | calibration of confidence | Medium |

---

## 5. Error Taxonomy

Nine error classes.

---

## 6. Argument Sketch

### 6.1 Autoregressive Factorization

$$
P_\\theta(y \\mid x) = \\prod_{t=1}^{|y|} P_\\theta(y_t \\mid y_{<t}, x)
$$

### 6.2 Finite Parameters

Pigeonhole argument.

### 6.3 Evaluation vs Generation

Correct beliefs may not surface.

---

## 7. Known Limitations

### 7.1 Scope

Applies to current architectures.

### 7.3 Independence Assumption

Pipeline formula assumes independence. Correlated errors may reduce or amplify risk.

### 7.5 Boolean Simplification

The binary predicate is a deliberate simplification.

---

## 8. Corollaries

$$
\\frac{\\partial D_c}{\\partial C} \\leq 0 \\quad c \\in \\{ERR\\_OMISSION, ERR\\_SCHEMA, ERR\\_TRUNCATION, ERR\\_INSTRUCTION\\}
$$

$$
\\frac{\\partial D_c}{\\partial C} > 0 \\quad c \\in \\{ERR\\_HALLUCINATION, ERR\\_SEMANTIC, ERR\\_SYCOPHANCY, ERR\\_CALIBRATION, ERR\\_REASONING\\}
$$

---

## 9. Practitioner Artifacts

### 9.1 Full Contract Block

This block contains the operative form and pipeline corollary with independence caveat.
ERR_HALLUCINATION checklist included.

### 9.2 Short-Form

Non-negligible error rate.

### 9.3 Inline Banner

Minimal banner.

### 9.4 CLAUDE.md Block

Non-negligible error rate. Pipeline compounding. Independence caveat noted.
"""
