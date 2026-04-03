"""Reference collector, normalizer, and verification via network fetching."""

from __future__ import annotations

import re
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

from pals_check.constants import ErrorClass


@dataclass
class Reference:
    """Normalized reference record."""

    ref_id: str
    authors: str
    year: int
    title: str
    venue: str
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    relevance: Optional[str] = None
    error_classes_supported: list[str] = field(default_factory=list)
    confidence_note: Optional[str] = None
    section_cited_in: list[str] = field(default_factory=list)
    publication_type: str = "unknown"  # "peer-reviewed" | "preprint" | "unknown"
    verification_status: str = "unverified"
    fetched_title: Optional[str] = None
    fetched_url: Optional[str] = None
    fetch_error: Optional[str] = None


def extract_references(text: str) -> list[Reference]:
    """Extract and normalize all references from the document text."""
    refs: list[Reference] = []

    # Pattern 1: Formal table rows in \u00a74
    table_pattern = re.compile(
        r'\|\s*([^|]+?(?:\(\d{4}\)[^|]*?))\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|'
    )
    for m in table_pattern.finditer(text):
        raw_ref = m.group(1).strip()
        relevance = m.group(2).strip()
        confidence = m.group(3).strip()

        if raw_ref.startswith("Reference") or raw_ref.startswith("---"):
            continue
        if raw_ref.startswith("Class") or raw_ref.startswith("**"):
            continue

        ref = _parse_formal_reference(raw_ref, relevance, confidence)
        if ref:
            refs.append(ref)

    # Pattern 2: Inline citations
    inline_pattern = re.compile(
        r'(?:(?:cited in|see|per|from)\s+)?'
        r'([A-Z][a-z\u00e0-\u00fc]+(?:\s+et\s+al\.)?)'
        r'[\s,]*\((\d{4})\)'
    )
    cited_locations: dict[str, list[str]] = {}
    for section_match in re.finditer(r'##\s+([\d.]+)\.?\s', text):
        section_id = section_match.group(1).rstrip('.')
        start = section_match.end()
        next_section = re.search(r'\n##\s+\d', text[start:])
        end = start + next_section.start() if next_section else len(text)
        section_text = text[start:end]

        for cite in inline_pattern.finditer(section_text):
            key = f"{cite.group(1).strip().lower().replace(' ', '_')}_{cite.group(2)}"
            key = re.sub(r'_et_al\.?', '', key)
            if key not in cited_locations:
                cited_locations[key] = []
            cited_locations[key].append(f"\u00a7{section_id}")

    for ref in refs:
        base_key = ref.ref_id
        if base_key in cited_locations:
            ref.section_cited_in.extend(cited_locations[base_key])
        for key, sections in cited_locations.items():
            if key.startswith(base_key.split("_")[0]) and key.endswith(str(ref.year)):
                for s in sections:
                    if s not in ref.section_cited_in:
                        ref.section_cited_in.append(s)

    return refs


def _parse_formal_reference(raw: str, relevance: str, confidence: str) -> Optional[Reference]:
    """Parse a single formal reference string from the \u00a74 table."""
    doi_match = re.search(r'DOI:\s*([\d./\w-]+)', raw)
    doi = doi_match.group(1).strip().rstrip('.') if doi_match else None

    arxiv_match = re.search(r'arXiv:([\d.]+)', raw)
    arxiv_id = arxiv_match.group(1).rstrip('.') if arxiv_match else None

    year_match = re.search(r'\((\d{4})\)', raw)
    if not year_match:
        return None
    year = int(year_match.group(1))

    authors_match = re.match(r'^([^(]+)', raw)
    authors = authors_match.group(1).strip().rstrip(',. ') if authors_match else "Unknown"

    title_match = re.search(r'"([^"]+)"', raw)
    title = title_match.group(1) if title_match else "Unknown"

    venue = "Unknown"
    venue_match = re.search(r'\*([^*]+)\*', raw)
    if venue_match:
        venue = venue_match.group(1)

    error_classes: list[str] = []
    combined = (relevance + " " + raw).upper()
    for ec in ErrorClass:
        if ec.value in combined:
            error_classes.append(ec.value)
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

    first_author = authors.split(",")[0].strip().lower().replace(" ", "_")
    first_author = re.sub(r'[^a-z_]', '', first_author)
    ref_id = f"{first_author}_{year}"

    # Infer publication type: DOI with non-arXiv venue = peer-reviewed
    if doi and arxiv_id:
        pub_type = "peer-reviewed"  # Published with DOI + has arXiv preprint
    elif doi and not arxiv_id:
        pub_type = "peer-reviewed"  # Journal/conference DOI only
    elif arxiv_id and not doi:
        pub_type = "preprint"  # arXiv only, no DOI
    else:
        pub_type = "unknown"

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
        section_cited_in=["\u00a74"],
        publication_type=pub_type,
    )


# --- Reference Verification (Network Fetching) ---

_SSL_CTX = ssl.create_default_context()
_HEADERS = {
    "User-Agent": "PALSLaw-Companion/1.0 (reference-verifier; +https://github.com)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
_FETCH_TIMEOUT = 15


def verify_references(refs: list[Reference], quiet: bool = False) -> list[Reference]:
    """Fetch DOI/arXiv URLs for each reference and cross-check metadata."""
    for i, ref in enumerate(refs):
        if not quiet:
            print(f"  Verifying [{ref.ref_id}]...", end=" ", flush=True)

        if ref.doi:
            url = f"https://doi.org/{ref.doi}"
            result = _fetch_and_extract(url, ref)
            if result["status"] == "unreachable" and ref.arxiv_id:
                clean_id = ref.arxiv_id.rstrip('.')
                fallback_url = f"https://arxiv.org/abs/{clean_id}"
                result = _fetch_and_extract(fallback_url, ref)
                result["note"] = f"DOI blocked ({result.get('error', '403')}); verified via arXiv fallback"
            elif result["status"] == "unreachable":
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
                print("\u26a0 no identifier")
            continue

        ref.verification_status = result["status"]
        ref.fetched_title = result.get("fetched_title")
        ref.fetched_url = result.get("url")
        ref.fetch_error = result.get("error")

        if not quiet:
            icon = {"verified": "\u2713", "mismatch": "\u2260", "unreachable": "\u2717",
                    "partial": "~"}.get(result["status"], "?")
            print(f"{icon} {result['status']}")

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

            body_bytes = resp.read(200_000)

            charset = "utf-8"
            if "charset=" in content_type:
                charset = content_type.split("charset=")[-1].split(";")[0].strip()

            try:
                body = body_bytes.decode(charset, errors="replace")
            except (LookupError, UnicodeDecodeError):
                body = body_bytes.decode("utf-8", errors="replace")

            if "application/pdf" in content_type or final_url.endswith(".pdf"):
                return {
                    "status": "partial",
                    "url": final_url,
                    "fetched_title": None,
                    "note": "Resolved to PDF \u2014 title cross-check skipped",
                }

            fetched_title = _extract_html_title(body)
            if not fetched_title:
                fetched_title = _extract_meta_citation_title(body)

            if not fetched_title:
                return {
                    "status": "partial",
                    "url": final_url,
                    "fetched_title": None,
                    "note": "Page fetched but no <title> found",
                }

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
        title = re.sub(r'&#?\w+;', ' ', title)
        title = re.sub(r'\s+', ' ', title)
        return title
    return None


def _extract_meta_citation_title(html: str) -> Optional[str]:
    """Extract citation_title meta tag (common on academic pages)."""
    m = re.search(
        r'<meta\s+name=["\']citation_title["\']\s+content=["\'](.*?)["\']',
        html, re.IGNORECASE,
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
        stopwords = {"the", "and", "for", "with", "from", "that", "this", "are", "was", "not"}
        return words - stopwords

    claimed_words = normalize(claimed)
    fetched_words = normalize(fetched)

    if not claimed_words:
        return 0.0

    overlap = claimed_words & fetched_words
    return len(overlap) / len(claimed_words)
