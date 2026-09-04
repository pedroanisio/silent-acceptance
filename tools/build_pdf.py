"""Render the Markdown specification to PDF with pandoc and LuaLaTeX.

Usage:
    python3 -m tools.build_pdf SILENT_ACCEPTANCE-v2.0.0.md output/SILENT_ACCEPTANCE-v2.0.0.pdf

What the build does to the source before handing it to pandoc:

1. Strips the YAML front matter. It stays in the Markdown source (project rule:
   every Markdown document carries it) but is not rendered; the document's own
   provenance section (§11) carries the verification statement and the generation
   disclosure in prose.
2. Lifts the ``# Title`` / ``### Subtitle`` lines and the two title-page lines that
   follow them (bold author, ``Preprint, v…`` line) into pandoc metadata so they are
   typeset as a title block instead of body text.
3. Substitutes the handful of code-point glyphs that the LaTeX fonts do not carry
   (double-struck E, script D, the warning sign, the up arrow) with ASCII fallbacks.
   The substitution is applied only inside fenced code blocks and to the warning
   sign in prose; display and inline math are untouched.

Pandoc and LuaLaTeX are required (``pandoc``, ``lualatex`` on PATH). The pure
transformation functions have no external dependencies and are unit-tested.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from pals_check.constants import document_version

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
AUTHOR_LINE_RE = re.compile(r"^\*\*(.+?)\*\*\s*$")
PREPRINT_LINE_RE = re.compile(r"^(Preprint,\s*v[\d.]+.*?)\s*$")

# Glyphs that neither Latin Modern nor DejaVu reliably provide in verbatim text.
CODE_GLYPH_FALLBACKS: dict[str, str] = {
    "𝔼": "E",
    "𝒟": "D",
    "⚠": "(!)",
    "↑": "^",
}

PROSE_GLYPH_FALLBACKS: dict[str, str] = {
    "⚠": "(!)",
}


@dataclass(frozen=True)
class TitleBlock:
    title: str
    subtitle: str
    author: str
    date_line: str
    body: str


def strip_frontmatter(text: str) -> tuple[str, str]:
    """Return ``(frontmatter_yaml, body)``; the YAML is empty if there is none."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return "", text
    return m.group(1), text[m.end() :]


def split_title_block(body: str) -> TitleBlock:
    """Lift the title page (title, subtitle, bold author, preprint line) out of the body.

    Any of the four elements may be absent; whatever is not recognized stays in the
    body untouched.
    """
    lines = body.lstrip("\n").split("\n")
    title = subtitle = author = date_line = ""
    idx = 0

    def skip_blank() -> None:
        nonlocal idx
        while idx < len(lines) and not lines[idx].strip():
            idx += 1

    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()
        idx = 1
        skip_blank()
        if idx < len(lines) and lines[idx].startswith("### "):
            subtitle = lines[idx][4:].strip()
            idx += 1
        skip_blank()
        m_author = AUTHOR_LINE_RE.match(lines[idx]) if idx < len(lines) else None
        if m_author:
            author = m_author.group(1).strip()
            idx += 1
        m_date = PREPRINT_LINE_RE.match(lines[idx]) if idx < len(lines) else None
        if m_date:
            date_line = m_date.group(1).strip()
            idx += 1
    return TitleBlock(title, subtitle, author, date_line, "\n".join(lines[idx:]).lstrip("\n"))


def substitute_glyphs(body: str) -> str:
    """Apply the fallback maps: full map inside fenced code, prose map elsewhere."""
    out: list[str] = []
    in_fence = False
    for line in body.split("\n"):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            out.append(line)
            continue
        table = CODE_GLYPH_FALLBACKS if in_fence else PROSE_GLYPH_FALLBACKS
        for glyph, repl in table.items():
            line = line.replace(glyph, repl)
        out.append(line)
    return "\n".join(out)


# Tagging must be requested before \documentclass, which pandoc will not do
# from a header include. The build therefore goes Markdown -> .tex -> PDF so
# this line can be prepended. Requires TeX Live 2024+.
DOCUMENT_METADATA = r"\DocumentMetadata{testphase={phase-III}}"


def latex_header(
    running_title: str, *, title: str = "", author: str = "", subject: str = "", keywords: str = ""
) -> str:
    """Preamble additions: running head, code-block wrapping, PDF metadata."""
    return rf"""
\usepackage{{fancyhdr}}
\usepackage{{microtype}}
\usepackage{{fvextra}}
\usepackage{{etoolbox}}
\pagestyle{{fancy}}
\fancyhf{{}}
\fancyhead[L]{{\small {running_title}}}
\fancyfoot[C]{{\thepage}}
\setlength{{\emergencystretch}}{{3em}}

%% Code blocks wrap instead of running past the margin. The contract block in
%% §10.1 is wide enough to clip without this.
\fvset{{breaklines=true,breakanywhere=true,breaksymbolleft={{}}}}

%% Reference tables one step up from the surrounding body text.
\AtBeginEnvironment{{longtable}}{{\normalsize}}

%% hyperref arrives with \usepackage{{bookmark}}, which pandoc emits after this
%% include, so setting metadata here directly is a no-op. Defer it.
\AtBeginDocument{{%
  \hypersetup{{
    pdftitle={{{title}}},
    pdfauthor={{{author}}},
    pdfsubject={{{subject}}},
    pdfkeywords={{{keywords}}},
    pdflang={{en}},
  }}%
}}
"""


def prepare_markdown(text: str) -> tuple[str, TitleBlock]:
    """Run the whole source transformation; returns (markdown, title block)."""
    _, body = strip_frontmatter(text)
    tb = split_title_block(body)
    return substitute_glyphs(tb.body), tb


def build(spec_path: Path, pdf_path: Path) -> None:
    for tool in ("pandoc", "lualatex"):
        if shutil.which(tool) is None:
            raise SystemExit(f"{tool} not found on PATH")

    text = spec_path.read_text(encoding="utf-8")
    md, tb = prepare_markdown(text)
    version = document_version(text)
    running_title = f"{tb.title} v{version}"
    author = tb.author or "Pedro Anisio de Luna e Silva"
    subject = (
        "Silent acceptance: passing LLM output to a consumer with no declared "
        "verification boundary is an architectural defect."
    )
    keywords = (
        "LLM; hallucination; verification boundary; silent acceptance; "
        "agent harness; solver configuration; software architecture; evaluation"
    )

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="spec-pdf-") as tmp:
        tmp_dir = Path(tmp)
        md_file = tmp_dir / "spec.md"
        header_file = tmp_dir / "header.tex"
        md_file.write_text(md, encoding="utf-8")
        header_file.write_text(
            latex_header(running_title, title=tb.title, author=author, subject=subject, keywords=keywords),
            encoding="utf-8",
        )

        tex_file = tmp_dir / "spec.tex"
        common = [
            "-f",
            "markdown+pipe_tables+tex_math_dollars+raw_attribute+autolink_bare_uris",
            "--toc",
            "--toc-depth=2",
            "-V",
            f"title={tb.title}",
            "-V",
            f"subtitle={tb.subtitle}",
            "-V",
            f"author={author}",
            "-V",
            f"date={tb.date_line or f'Preprint, v{version}'}",
            "-V",
            "documentclass=article",
            "-V",
            "geometry:margin=1in",
            "-V",
            "fontsize=11pt",
            "-V",
            "mainfont=DejaVu Serif",
            "-V",
            "sansfont=DejaVu Sans",
            "-V",
            "monofont=DejaVu Sans Mono",
            "-V",
            "monofontoptions=Scale=0.82",
            "-V",
            "colorlinks=true",
            "-V",
            "linkcolor=blue!60!black",
            "-V",
            "urlcolor=blue!60!black",
            "-H",
            str(header_file),
        ]
        subprocess.run(["pandoc", str(md_file), "-o", str(tex_file), "--standalone", *common], check=True)

        # Prepend the tagging request; it must precede \documentclass.
        tex = tex_file.read_text(encoding="utf-8")
        tex_file.write_text(f"{DOCUMENT_METADATA}\n{tex}", encoding="utf-8")

        # Twice, so the table of contents resolves.
        for _ in range(2):
            subprocess.run(
                ["lualatex", "-interaction=nonstopmode", "spec.tex"],
                cwd=tmp_dir,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        produced = tmp_dir / "spec.pdf"
        if not produced.exists():
            raise SystemExit("lualatex produced no PDF; see the log in " + str(tmp_dir))

        log = (tmp_dir / "spec.log").read_text(encoding="utf-8", errors="replace")
        overfull = [ln for ln in log.splitlines() if "Overfull \\hbox" in ln]
        if overfull:
            print(f"warning: {len(overfull)} overfull hbox(es) - content may clip:")
            for ln in overfull[:5]:
                print("  " + ln.strip())

        shutil.copyfile(produced, pdf_path)
    print(f"PDF written to {pdf_path}")


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: python3 -m tools.build_pdf <spec.md> <out.pdf>", file=sys.stderr)
        return 1
    build(Path(argv[1]), Path(argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
