"""Digital signature for verification artifacts.

Produces a tamper-evident seal binding the report/schema content
to the source document and tool version. The signature covers
the canonical JSON encoding of the payload — any modification
to the output invalidates the digest.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

TOOL_ID = "pals-check"
TOOL_VERSION = "1.0.0"
SIGNATURE_VERSION = "1"
HASH_ALGORITHM = "sha256"


def sign_artifact(payload: dict[str, Any], source_hash: str) -> dict[str, Any]:
    """Compute a digital signature block for a verification artifact.

    Args:
        payload: The report or schema dict to sign (without the signature field).
        source_hash: The content_hash of the source document.

    Returns:
        A new dict that is ``payload`` plus a ``_signature`` block.
    """
    # Canonical encoding: sorted keys, no trailing whitespace, deterministic
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    payload_digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    signature_block = {
        "signature_version": SIGNATURE_VERSION,
        "algorithm": HASH_ALGORITHM,
        "tool_id": TOOL_ID,
        "tool_version": TOOL_VERSION,
        "signed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_document_hash": source_hash,
        "payload_digest": payload_digest,
    }

    # The seal digest covers both the payload and the signature metadata
    # (excluding the seal itself) to prevent metadata tampering
    seal_input = json.dumps(
        {**signature_block, "payload_digest": payload_digest},
        sort_keys=True,
        ensure_ascii=False,
    )
    signature_block["seal"] = hashlib.sha256(seal_input.encode("utf-8")).hexdigest()

    return {**payload, "_signature": signature_block}


def generate_certificate(
    md_text: str,
    report_dict: dict[str, Any],
    schema_dict: dict[str, Any],
) -> dict[str, Any]:
    """Generate a hash-binding certificate for an .md + report + schema triple.

    The certificate is a standalone JSON object that binds the three
    artifacts together via content hashes. A verifier can re-hash each
    file and confirm all three digests match, proving the report and
    schema were generated from that exact spec revision.

    Args:
        md_text: The raw Markdown source text.
        report_dict: The report dict (may or may not include ``_signature``).
        schema_dict: The schema dict (may or may not include ``_signature``).

    Returns:
        A certificate dict ready to be written as JSON.
    """
    # Hash the source .md
    spec_digest = hashlib.sha256(md_text.encode("utf-8")).hexdigest()

    # Hash the report and schema payloads (excluding per-artifact signatures)
    report_payload = {k: v for k, v in report_dict.items() if k != "_signature"}
    schema_payload = {k: v for k, v in schema_dict.items() if k != "_signature"}

    report_canonical = json.dumps(report_payload, sort_keys=True, ensure_ascii=False, default=str)
    schema_canonical = json.dumps(schema_payload, sort_keys=True, ensure_ascii=False, default=str)

    report_digest = hashlib.sha256(report_canonical.encode("utf-8")).hexdigest()
    schema_digest = hashlib.sha256(schema_canonical.encode("utf-8")).hexdigest()

    # Extract check results from the report
    checks_passed = report_payload.get("checks_passed", 0)
    checks_warned = report_payload.get("checks_warned", 0)
    checks_failed = report_payload.get("checks_failed", 0)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    certificate: dict[str, Any] = {
        "certificate_version": "1",
        "tool_id": TOOL_ID,
        "tool_version": TOOL_VERSION,
        "generated_at": timestamp,
        "spec": {
            "algorithm": HASH_ALGORITHM,
            "digest": spec_digest,
        },
        "report": {
            "algorithm": HASH_ALGORITHM,
            "digest": report_digest,
            "version": report_payload.get("document_version", "unknown"),
        },
        "schema": {
            "algorithm": HASH_ALGORITHM,
            "digest": schema_digest,
            "version": schema_payload.get("version", "unknown"),
        },
        "checks": {
            "passed": checks_passed,
            "warned": checks_warned,
            "failed": checks_failed,
            "total": checks_passed + checks_warned + checks_failed,
        },
    }

    # Binding hash: covers the entire certificate (except the binding itself)
    binding_input = json.dumps(certificate, sort_keys=True, ensure_ascii=False)
    certificate["binding"] = {
        "algorithm": HASH_ALGORITHM,
        "digest": hashlib.sha256(binding_input.encode("utf-8")).hexdigest(),
    }

    return certificate


def verify_certificate(
    certificate: dict[str, Any],
    md_text: str | None = None,
    report_dict: dict[str, Any] | None = None,
    schema_dict: dict[str, Any] | None = None,
) -> tuple[bool, list[str]]:
    """Verify a certificate against the original artifacts.

    Pass any combination of the three artifacts. Each provided artifact
    is hash-checked against the certificate; omitted artifacts are skipped.

    Args:
        certificate: The certificate dict.
        md_text: The raw Markdown source text (optional).
        report_dict: The report dict (optional, ``_signature`` stripped automatically).
        schema_dict: The schema dict (optional, ``_signature`` stripped automatically).

    Returns:
        (all_valid, messages) — True only if every provided artifact matches.
    """
    if certificate.get("certificate_version") != "1":
        return False, [f"Unknown certificate version: {certificate.get('certificate_version')}"]

    # Verify the binding hash first (proves certificate wasn't tampered with)
    binding = certificate.get("binding")
    if not binding:
        return False, ["No binding block found in certificate"]

    cert_without_binding = {k: v for k, v in certificate.items() if k != "binding"}
    binding_input = json.dumps(cert_without_binding, sort_keys=True, ensure_ascii=False)
    expected_binding = hashlib.sha256(binding_input.encode("utf-8")).hexdigest()

    if binding.get("digest") != expected_binding:
        return False, ["Binding hash mismatch — certificate has been modified"]

    messages: list[str] = []
    all_valid = True

    if md_text is not None:
        spec_digest = hashlib.sha256(md_text.encode("utf-8")).hexdigest()
        if spec_digest == certificate["spec"]["digest"]:
            messages.append("spec: OK")
        else:
            messages.append(f"spec: MISMATCH (expected {certificate['spec']['digest'][:16]}..., got {spec_digest[:16]}...)")
            all_valid = False

    if report_dict is not None:
        payload = {k: v for k, v in report_dict.items() if k != "_signature"}
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if digest == certificate["report"]["digest"]:
            messages.append("report: OK")
        else:
            messages.append(f"report: MISMATCH (expected {certificate['report']['digest'][:16]}..., got {digest[:16]}...)")
            all_valid = False

    if schema_dict is not None:
        payload = {k: v for k, v in schema_dict.items() if k != "_signature"}
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if digest == certificate["schema"]["digest"]:
            messages.append("schema: OK")
        else:
            messages.append(f"schema: MISMATCH (expected {certificate['schema']['digest'][:16]}..., got {digest[:16]}...)")
            all_valid = False

    if not messages:
        messages.append("No artifacts provided for verification")
        all_valid = False

    return all_valid, messages


def verify_artifact(signed: dict[str, Any]) -> tuple[bool, str]:
    """Verify the integrity of a signed artifact.

    Args:
        signed: A dict that includes a ``_signature`` block.

    Returns:
        (is_valid, message) tuple.
    """
    sig = signed.get("_signature")
    if not sig:
        return False, "No _signature block found"

    if sig.get("signature_version") != SIGNATURE_VERSION:
        return False, f"Unknown signature version: {sig.get('signature_version')}"

    # Reconstruct the payload without the signature
    payload = {k: v for k, v in signed.items() if k != "_signature"}
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    expected_digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    if sig.get("payload_digest") != expected_digest:
        return False, (
            f"Payload digest mismatch: expected {expected_digest}, "
            f"got {sig.get('payload_digest')}"
        )

    # Verify the seal covers the signature metadata
    seal_input_block = {k: v for k, v in sig.items() if k != "seal"}
    seal_input = json.dumps(seal_input_block, sort_keys=True, ensure_ascii=False)
    expected_seal = hashlib.sha256(seal_input.encode("utf-8")).hexdigest()

    if sig.get("seal") != expected_seal:
        return False, (
            f"Seal mismatch: signature metadata may have been tampered with"
        )

    return True, (
        f"Valid — signed by {sig['tool_id']} v{sig['tool_version']} "
        f"at {sig['signed_at']}"
    )
