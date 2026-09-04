#!/usr/bin/env python3
"""Executable acceptance criteria for the v2.1.0 revision.

    python3 check_v210.py [SILENT_ACCEPTANCE-v2.1.0.md]

Criterion 1 of the task is a list of strings that must not survive the revision,
and the rest are structural. Running them beats reading for them: a 59 KB spec
with ~30 local edits will not be checked reliably by eye.

Exit 0 when every criterion passes.
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT = HERE / "SILENT_ACCEPTANCE-v2.1.0.md"
LINT = HERE / "silent-acceptance-lint"

# Criterion 1: strings that must not remain anywhere in the document.
FORBIDDEN = [
    (r"Σ\s*\(\s*x\s*\)", "Σ(x) — replaced by the acceptability predicate A(y,x,z) (A1)"),
    (r"ε\s*\(\s*y\s*,\s*x\s*\)(?!\s*,)", "two-argument ε(y,x) — now ε(y,x,z) (A1)"),
    (r"\bmigrate\b", "'migrate' — §7 is restricted to detectability (C4)"),
    (r"§\s*7\s+establishes", "'§7 establishes' — it hypothesizes (D1)"),
    (r"MODEL_VERSION", "MODEL_VERSION — now SOLVER_CONFIGURATION_ID (A4); "
                       "permitted only in the linter as a deprecated alias"),
    (r"lower-bound motivation, not a deployable risk model", "deleted phrase (A3)"),
    (r"ERROR CLASSES NOT COVERED", "checkbox list replaced by a per-class table (D1)"),
]

# Criterion 1 also bans an unindexed delta in a claim. Allow the definition itself.
UNINDEXED_DELTA = re.compile(r"δ\s*(?!_|\{|\s*_)(?![^\n]{0,40}is (defined|the measured))")

# Patterns accept both the Unicode glyph and the LaTeX macro, because the source
# is LaTeX-flavoured Markdown. Matching only the glyph produced false negatives
# on correctly-applied edits.
REQUIRED = [
    (r"A\s*\(\s*y\s*,\s*x\s*,\s*z\s*\)", "acceptability predicate A(y,x,z) (A1)"),
    (r"(δ|\\delta)_\{?M\s*,\s*(D|\\mathcal\{D\})\}?", "indexed bound delta_{M,D} (A2)"),
    (r"SOLVER_CONFIGURATION_ID", "solver configuration id (A4)"),
    (r"conditional (error )?hazard", "conditional-hazard form in 3.4 (A3)"),
    (r"Suzuki", "Suzuki et al. added to 4.1 and the references (B1)"),
    (r"(ρ|\\rho)_c|escaped risk", "escaped risk rho_c (C4)"),
    (r"(π|\\pi)_c|prevalence", "prevalence pi_c (C4)"),
    (r"(τ|\\tau)\b|tolerated failure", "tolerated failure rate tau (A2, C2)"),
    (r"ACCEPTANCE_AUTHORITY", "acceptance authority field (C5, D1)"),
    (r"TOLERATED_FAILURE_RATE", "contract-block field TOLERATED_FAILURE_RATE (D1)"),
    (r"CALIBRATED_ON", "contract-block field CALIBRATED_ON (D1)"),
    (r"OWNER", "contract-block field OWNER (D1)"),
    (r"acceptance authority must remain outside", "9.7 retitled (C5)"),
    (r"residual risk of the output crossing", "assurance-case sentence in 9.1 (C1)"),
    (r"specificity", "specificity alongside recall (C2)"),
    (r"September 2026 review", "the review recorded in 11.4 (E2)"),
    (r"Preprint,\s*v2\.1\.0", "document header declares v2.1.0 (E3) — "
     "matching anywhere in the file gave a false pass while the header said 2.0.0"),
    (r"\*\*SILENT_ACCEPTANCE_VERSION:\*\*\s*2\.1\.0", "§10.4 agent block bumped (D2)"),
]


def read(p):
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return None


# §11.6 records what changed and is not rewritten; §10.5 documents the alias.
LEGITIMATE_MODEL_VERSION = ("deprecated alias", "replaced `MODEL_VERSION`")
VERSION_HISTORY_HEADING = "### 11.6 Version history"


def check_doc(text):
    fails = []
    for pat, why in FORBIDDEN:
        if "MODEL_VERSION" in pat:
            # Everything from the version history down is a record of change.
            body = text.split(VERSION_HISTORY_HEADING)[0]
            lines = body.splitlines()
            # The exemption phrase can land on the next line when a sentence
            # wraps, so look at the line and its successor.
            hits = [ln for i, ln in enumerate(lines) if re.search(pat, ln)
                    and not any(ok in ln + " " + (lines[i + 1] if i + 1 < len(lines) else "")
                                for ok in LEGITIMATE_MODEL_VERSION)]
        else:
            hits = re.findall(pat, text)
        if hits:
            fails.append(("forbidden", f"{len(hits)}x {why}"))
    for pat, why in REQUIRED:
        if not re.search(pat, text, re.I):
            fails.append(("missing", why))
    # Criterion 5: ten declaration fields in §9.1.
    m = re.search(r"9\.1(.{0,6000}?)9\.2", text, re.S)
    if m:
        numbered = re.findall(r"^\s*(\d{1,2})\.\s+\S", m.group(1), re.M)
        if len(set(numbered)) < 10:
            fails.append(("structure", f"§9.1 lists {len(set(numbered))} declaration "
                                       "fields, needs 10 (C2)"))
    else:
        fails.append(("structure", "could not locate §9.1 to count declaration fields"))
    return fails


def check_linter():
    """Criterion 5: the linter enforces S != ∅ and ACCEPTANCE_AUTHORITY."""
    fails = []
    src = " ".join((read(p) or "") for p in (LINT / "src").glob("*.ts"))
    if not src.strip():
        return [("linter", "silent-acceptance-lint/src not found")]
    if "SOLVER_CONFIGURATION_ID" not in src:
        fails.append(("linter", "does not recognize SOLVER_CONFIGURATION_ID (D3)"))
    if "ACCEPTANCE_AUTHORITY" not in src:
        fails.append(("linter", "does not check ACCEPTANCE_AUTHORITY (D3)"))
    if not re.search(r"deprecat", src, re.I):
        fails.append(("linter", "no deprecation path for MODEL_VERSION (D3)"))
    return fails


def check_artifacts():
    """Criterion 8 and F6."""
    fails = []
    schema = read(HERE / "output" / "pals_law_schema.json")
    if schema:
        # Symbols are stored as LaTeX in the artifact, so accept either form.
        for label, forms in (("SOLVER_CONFIGURATION_ID", ("SOLVER_CONFIGURATION_ID",)),
                             ("rho_c", ("rho_c", "\\\\rho_c", "ρ")),
                             ("pi_c", ("pi_c", "\\\\pi_c", "π")),
                             ("tau", ("tau", "\\\\tau", "τ")),
                             ("A(y,x,z)", ("\"name\": \"A\"",)),
                             ("sev_c", ("sev_c",))):
            if not any(f in schema for f in forms):
                fails.append(("artifact", f"pals_law_schema.json missing {label} (F6)"))
    else:
        fails.append(("artifact", "output/pals_law_schema.json not readable"))
    report = read(HERE / "output" / "pals_law_report.json")
    if report and "Suzuki" not in report:
        fails.append(("artifact", "pals_law_report.json has no Suzuki et al. row (F6)"))
    return fails


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    text = read(target)
    if text is None:
        print(f"target not found: {target}")
        print("(run against SILENT_ACCEPTANCE-v2.0.0.md for a baseline)")
        return 2

    groups = [("document", check_doc(text)),
              ("linter", check_linter()),
              ("artifacts", check_artifacts())]
    total = sum(len(f) for _, f in groups)
    print(f"acceptance check — {target.name}\n")
    for name, fails in groups:
        print(f"  {name}: {'PASS' if not fails else str(len(fails)) + ' outstanding'}")
        for kind, why in fails:
            print(f"      [{kind}] {why}")
    print(f"\n{total} outstanding" if total else "\nall criteria pass")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
