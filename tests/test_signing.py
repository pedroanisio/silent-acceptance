"""Tests for pals_check.signing — digital signature and verification."""

from __future__ import annotations

import json

from pals_check.signing import (
    HASH_ALGORITHM,
    SIGNATURE_VERSION,
    TOOL_ID,
    TOOL_VERSION,
    generate_certificate,
    sign_artifact,
    verify_artifact,
    verify_certificate,
)


class TestSignArtifact:
    def test_sign_artifact_adds_signature_block(self):
        payload = {"key": "value", "number": 42}
        signed = sign_artifact(payload, "abc123")
        assert "_signature" in signed
        sig = signed["_signature"]
        assert sig["algorithm"] == HASH_ALGORITHM
        assert sig["tool_id"] == TOOL_ID
        assert sig["tool_version"] == TOOL_VERSION
        assert sig["signature_version"] == SIGNATURE_VERSION
        assert sig["source_document_hash"] == "abc123"
        assert len(sig["payload_digest"]) == 64  # SHA-256 hex
        assert len(sig["seal"]) == 64
        assert "signed_at" in sig

    def test_sign_artifact_preserves_payload(self):
        payload = {"a": 1, "b": [2, 3]}
        signed = sign_artifact(payload, "hash")
        assert signed["a"] == 1
        assert signed["b"] == [2, 3]

    def test_sign_artifact_deterministic_digest(self):
        payload = {"key": "value"}
        s1 = sign_artifact(payload, "h")
        s2 = sign_artifact(payload, "h")
        assert s1["_signature"]["payload_digest"] == s2["_signature"]["payload_digest"]

    def test_sign_artifact_different_payloads_different_digests(self):
        s1 = sign_artifact({"key": "a"}, "h")
        s2 = sign_artifact({"key": "b"}, "h")
        assert s1["_signature"]["payload_digest"] != s2["_signature"]["payload_digest"]

    def test_sign_artifact_different_source_hash_different_seal(self):
        payload = {"key": "value"}
        s1 = sign_artifact(payload, "hash1")
        s2 = sign_artifact(payload, "hash2")
        # Same payload digest, but different seal (source_hash is in seal input)
        assert s1["_signature"]["payload_digest"] == s2["_signature"]["payload_digest"]
        assert s1["_signature"]["seal"] != s2["_signature"]["seal"]


class TestVerifyArtifact:
    def test_verify_valid_artifact(self):
        payload = {"data": "test", "items": [1, 2, 3]}
        signed = sign_artifact(payload, "source_hash")
        valid, msg = verify_artifact(signed)
        assert valid is True
        assert "Valid" in msg
        assert TOOL_ID in msg

    def test_verify_tampered_payload_fails(self):
        signed = sign_artifact({"key": "original"}, "h")
        signed["key"] = "tampered"
        valid, msg = verify_artifact(signed)
        assert valid is False
        assert "Payload digest mismatch" in msg

    def test_verify_tampered_signature_metadata_fails(self):
        signed = sign_artifact({"key": "value"}, "h")
        signed["_signature"]["tool_version"] = "999.0.0"
        valid, msg = verify_artifact(signed)
        assert valid is False
        assert "Seal mismatch" in msg

    def test_verify_missing_signature_block(self):
        valid, msg = verify_artifact({"key": "value"})
        assert valid is False
        assert "No _signature block" in msg

    def test_verify_unknown_signature_version(self):
        signed = sign_artifact({"key": "value"}, "h")
        signed["_signature"]["signature_version"] = "99"
        valid, msg = verify_artifact(signed)
        assert valid is False
        assert "Unknown signature version" in msg

    def test_verify_added_field_fails(self):
        signed = sign_artifact({"key": "value"}, "h")
        signed["injected"] = "malicious"
        valid, msg = verify_artifact(signed)
        assert valid is False

    def test_verify_removed_field_fails(self):
        signed = sign_artifact({"key": "value", "other": "data"}, "h")
        del signed["other"]
        valid, msg = verify_artifact(signed)
        assert valid is False

    def test_roundtrip_through_json_serialization(self):
        """Signature survives JSON serialize/deserialize cycle."""
        payload = {"data": [1, 2], "nested": {"a": True}}
        signed = sign_artifact(payload, "hash123")
        json_str = json.dumps(signed, indent=2, default=str)
        restored = json.loads(json_str)
        valid, msg = verify_artifact(restored)
        assert valid is True


# --- Certificate generation and verification ---


class TestGenerateCertificate:
    MD = "# Test spec\n\nContent here."
    REPORT = {"document_version": "1.0", "checks_passed": 3, "checks_warned": 0, "checks_failed": 0, "data": [1]}
    SCHEMA = {"version": "1.0", "symbols": [], "claims": []}

    def test_certificate_has_required_fields(self):
        cert = generate_certificate(self.MD, self.REPORT, self.SCHEMA)
        assert cert["certificate_version"] == "1"
        assert cert["tool_id"] == TOOL_ID
        assert cert["tool_version"] == TOOL_VERSION
        assert "generated_at" in cert
        assert cert["spec"]["algorithm"] == HASH_ALGORITHM
        assert len(cert["spec"]["digest"]) == 64
        assert len(cert["report"]["digest"]) == 64
        assert len(cert["schema"]["digest"]) == 64
        assert cert["binding"]["algorithm"] == HASH_ALGORITHM
        assert len(cert["binding"]["digest"]) == 64

    def test_certificate_checks_summary(self):
        cert = generate_certificate(self.MD, self.REPORT, self.SCHEMA)
        assert cert["checks"]["passed"] == 3
        assert cert["checks"]["warned"] == 0
        assert cert["checks"]["failed"] == 0
        assert cert["checks"]["total"] == 3

    def test_certificate_version_extracted(self):
        cert = generate_certificate(self.MD, self.REPORT, self.SCHEMA)
        assert cert["report"]["version"] == "1.0"
        assert cert["schema"]["version"] == "1.0"

    def test_different_md_produces_different_spec_digest(self):
        c1 = generate_certificate(self.MD, self.REPORT, self.SCHEMA)
        c2 = generate_certificate(self.MD + " extra", self.REPORT, self.SCHEMA)
        assert c1["spec"]["digest"] != c2["spec"]["digest"]

    def test_different_report_produces_different_report_digest(self):
        c1 = generate_certificate(self.MD, self.REPORT, self.SCHEMA)
        c2 = generate_certificate(self.MD, {**self.REPORT, "extra": True}, self.SCHEMA)
        assert c1["report"]["digest"] != c2["report"]["digest"]

    def test_strips_signature_from_report(self):
        """_signature in report/schema must not affect the certificate digest."""
        signed_report = {**self.REPORT, "_signature": {"seal": "abc"}}
        c1 = generate_certificate(self.MD, self.REPORT, self.SCHEMA)
        c2 = generate_certificate(self.MD, signed_report, self.SCHEMA)
        assert c1["report"]["digest"] == c2["report"]["digest"]

    def test_roundtrip_through_json(self):
        cert = generate_certificate(self.MD, self.REPORT, self.SCHEMA)
        json_str = json.dumps(cert, indent=2)
        restored = json.loads(json_str)
        valid, messages = verify_certificate(restored, self.MD, self.REPORT, self.SCHEMA)
        assert valid is True


class TestVerifyCertificate:
    MD = "# Test spec\n\nContent here."
    REPORT = {"document_version": "1.0", "checks_passed": 2, "checks_warned": 1, "checks_failed": 0, "items": [1, 2]}
    SCHEMA = {"version": "1.0", "symbols": ["a"], "claims": ["b"]}

    def _cert(self):
        return generate_certificate(self.MD, self.REPORT, self.SCHEMA)

    def test_all_three_valid(self):
        valid, msgs = verify_certificate(self._cert(), self.MD, self.REPORT, self.SCHEMA)
        assert valid is True
        assert "spec: OK" in msgs
        assert "report: OK" in msgs
        assert "schema: OK" in msgs

    def test_spec_only(self):
        valid, msgs = verify_certificate(self._cert(), md_text=self.MD)
        assert valid is True
        assert len(msgs) == 1
        assert "spec: OK" in msgs[0]

    def test_report_only(self):
        valid, msgs = verify_certificate(self._cert(), report_dict=self.REPORT)
        assert valid is True
        assert "report: OK" in msgs[0]

    def test_tampered_spec_fails(self):
        valid, msgs = verify_certificate(self._cert(), md_text="tampered")
        assert valid is False
        assert any("MISMATCH" in m for m in msgs)

    def test_tampered_report_fails(self):
        valid, msgs = verify_certificate(self._cert(), report_dict={"tampered": True})
        assert valid is False
        assert any("MISMATCH" in m for m in msgs)

    def test_tampered_schema_fails(self):
        valid, msgs = verify_certificate(self._cert(), schema_dict={"tampered": True})
        assert valid is False
        assert any("MISMATCH" in m for m in msgs)

    def test_tampered_binding_fails(self):
        cert = self._cert()
        cert["binding"]["digest"] = "0" * 64
        valid, msgs = verify_certificate(cert, self.MD)
        assert valid is False
        assert any("Binding hash mismatch" in m for m in msgs)

    def test_tampered_certificate_field_fails(self):
        """Modifying any certificate field invalidates the binding."""
        cert = self._cert()
        cert["checks"]["failed"] = 99
        valid, msgs = verify_certificate(cert, self.MD)
        assert valid is False
        assert any("Binding hash mismatch" in m for m in msgs)

    def test_no_artifacts_provided_fails(self):
        valid, msgs = verify_certificate(self._cert())
        assert valid is False
        assert any("No artifacts provided" in m for m in msgs)

    def test_unknown_version_fails(self):
        cert = self._cert()
        cert["certificate_version"] = "99"
        valid, msgs = verify_certificate(cert, self.MD)
        assert valid is False
        assert any("Unknown certificate version" in m for m in msgs)

    def test_partial_match_mixed_result(self):
        """Valid spec + tampered report = failure."""
        valid, msgs = verify_certificate(
            self._cert(), md_text=self.MD, report_dict={"tampered": True}
        )
        assert valid is False
        assert any("spec: OK" in m for m in msgs)
        assert any("MISMATCH" in m for m in msgs)
