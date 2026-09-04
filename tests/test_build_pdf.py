"""Tests for tools.build_pdf — the pure source transformations behind the PDF build."""

from __future__ import annotations

from tools.build_pdf import (
    latex_header,
    prepare_markdown,
    split_title_block,
    strip_frontmatter,
    substitute_glyphs,
)

SAMPLE = """\
---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
  generated_by: "Author with Model via Tool"
  date: "2026-09-03"
---

# Silent Acceptance
### LLM Output Error as an Architectural Invariant

**Pedro Anisio de Luna e Silva**
Preprint, v2.0.0 — September 2026
*Versions 1.x were published as PALS's Law; see §11.*

---

## 1. Preamble

> **⚠ Independence caveat:** prose warning.

```typescript
 * 𝔼[ε(M(x), x)] ≥ δ > 0
 *   ↑ REQUIRED ⚠
```

$$
\\mathbb{E}[\\varepsilon] \\geq \\delta
$$
"""


class TestStripFrontmatter:
    def test_splits_yaml_and_body(self):
        yaml_text, body = strip_frontmatter(SAMPLE)
        assert yaml_text.startswith("disclaimer:")
        assert body.lstrip().startswith("# Silent Acceptance")

    def test_no_frontmatter_returns_empty_yaml(self):
        yaml_text, body = strip_frontmatter("# Title\n\nbody")
        assert yaml_text == ""
        assert body == "# Title\n\nbody"

    def test_frontmatter_never_reaches_the_rendered_body(self):
        md, _ = prepare_markdown(SAMPLE)
        assert "taken for granted" not in md
        assert "generated_by" not in md


class TestSplitTitleBlock:
    def test_lifts_title_subtitle_author_and_preprint_line(self):
        _, body = strip_frontmatter(SAMPLE)
        tb = split_title_block(body)
        assert tb.title == "Silent Acceptance"
        assert tb.subtitle == "LLM Output Error as an Architectural Invariant"
        assert tb.author == "Pedro Anisio de Luna e Silva"
        assert tb.date_line == "Preprint, v2.0.0 — September 2026"
        assert tb.body.startswith("*Versions 1.x were published as PALS's Law")

    def test_body_without_title_is_unchanged(self):
        tb = split_title_block("## 1. Section\n\ntext")
        assert tb.title == "" and tb.subtitle == "" and tb.author == "" and tb.date_line == ""
        assert tb.body == "## 1. Section\n\ntext"

    def test_v1_style_header_keeps_its_metadata_lines_in_body(self):
        body = "# PALS's LAW\n### Subtitle\n\n**Author of the principle:** Someone  \n**Document version:** 1.5.4\n"
        tb = split_title_block(body)
        assert tb.title == "PALS's LAW"
        assert tb.author == ""
        assert "**Document version:** 1.5.4" in tb.body

    def test_real_spec_title_block(self, real_md_text: str):
        _, body = strip_frontmatter(real_md_text)
        tb = split_title_block(body)
        assert tb.title == "Silent Acceptance"
        assert tb.author == "Pedro Anisio de Luna e Silva"
        assert tb.date_line.startswith("Preprint, v2.0.0")
        assert "peer review pending" not in real_md_text


class TestSubstituteGlyphs:
    def test_code_blocks_get_full_fallback_map(self):
        _, body = strip_frontmatter(SAMPLE)
        out = substitute_glyphs(body)
        assert "E[ε(M(x), x)]" in out
        assert "^ REQUIRED (!)" in out
        assert "𝔼" not in out and "↑" not in out

    def test_prose_only_replaces_warning_sign(self):
        _, body = strip_frontmatter(SAMPLE)
        out = substitute_glyphs(body)
        assert "**(!) Independence caveat:**" in out

    def test_math_is_untouched(self):
        _, body = strip_frontmatter(SAMPLE)
        out = substitute_glyphs(body)
        assert "\\mathbb{E}[\\varepsilon] \\geq \\delta" in out

    def test_fence_state_toggles(self):
        text = "```\n↑\n```\n↑ outside\n"
        out = substitute_glyphs(text)
        assert out == "```\n^\n```\n↑ outside\n"


class TestLatexHeader:
    def test_running_header_has_title_only_no_status_line(self):
        header = latex_header("Silent Acceptance v2.0.0")
        assert "fancyhead[L]{\\small Silent Acceptance v2.0.0}" in header
        assert "fancyhead[R]" not in header
        assert "peer review" not in header
        assert "disclaimer" not in header.lower()
