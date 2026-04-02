"""Tests for pals_check.schema — formal schema construction."""

from __future__ import annotations

from pals_check.schema import (
    PALSLawSchema,
    _build_claims,
    _build_dependency_graph,
    _build_error_classes,
    _build_symbols,
    build_schema,
)


# --- build_schema ---


class TestBuildSchema:
    def test_build_schema_returns_correct_type(self, minimal_md_text: str):
        schema = build_schema(minimal_md_text)
        assert isinstance(schema, PALSLawSchema)

    def test_build_schema_extracts_version(self, minimal_md_text: str):
        schema = build_schema(minimal_md_text)
        assert schema.version == "0.0.1"

    def test_build_schema_computes_content_hash(self, minimal_md_text: str):
        schema = build_schema(minimal_md_text)
        assert len(schema.content_hash) == 16
        assert all(c in "0123456789abcdef" for c in schema.content_hash)

    def test_build_schema_deterministic_hash(self, minimal_md_text: str):
        s1 = build_schema(minimal_md_text)
        s2 = build_schema(minimal_md_text)
        assert s1.content_hash == s2.content_hash

    def test_build_schema_different_text_different_hash(self, minimal_md_text: str):
        s1 = build_schema(minimal_md_text)
        s2 = build_schema(minimal_md_text + "\nextra line")
        assert s1.content_hash != s2.content_hash

    def test_build_schema_real_document(self, real_md_text: str):
        schema = build_schema(real_md_text)
        assert schema.version == "1.5.0"


# --- _build_symbols ---


class TestBuildSymbols:
    def test_build_symbols_count(self):
        symbols = _build_symbols()
        assert len(symbols) == 15

    def test_build_symbols_all_have_required_fields(self):
        symbols = _build_symbols()
        for s in symbols:
            assert s.name
            assert s.latex
            assert s.type_signature
            assert s.definition
            assert s.section_defined

    def test_build_symbols_epsilon_definition(self):
        symbols = _build_symbols()
        eps = next(s for s in symbols if s.name == "epsilon")
        assert "{0, 1}" in eps.type_signature


# --- _build_claims ---


class TestBuildClaims:
    def test_build_claims_count(self):
        claims = _build_claims()
        assert len(claims) == 12

    def test_build_claims_operative_is_falsifiable(self):
        claims = _build_claims()
        operative = next(c for c in claims if c.claim_id == "OPERATIVE")
        assert operative.is_falsifiable is True
        assert operative.falsification_method is not None

    def test_build_claims_definition_is_not_falsifiable(self):
        claims = _build_claims()
        defn = next(c for c in claims if c.claim_id == "DEF_EPSILON")
        assert defn.is_falsifiable is False

    def test_build_claims_all_ids_unique(self):
        claims = _build_claims()
        ids = [c.claim_id for c in claims]
        assert len(ids) == len(set(ids))

    def test_build_claims_dependencies_reference_valid_ids(self):
        claims = _build_claims()
        all_ids = {c.claim_id for c in claims}
        # Add known argument section IDs
        all_ids.add("ARG_6.2")
        for c in claims:
            for dep in c.depends_on:
                assert dep in all_ids, f"Claim {c.claim_id} depends on unknown {dep}"

    def test_build_claims_cor5_is_hypothesis(self):
        claims = _build_claims()
        cor5 = next(c for c in claims if c.claim_id == "COR5")
        assert cor5.status == "hypothesis"


# --- _build_error_classes ---


class TestBuildErrorClasses:
    def test_build_error_classes_count(self):
        classes = _build_error_classes()
        assert len(classes) == 9

    def test_build_error_classes_structural_sign(self):
        classes = _build_error_classes()
        structural = [c for c in classes if c.detection_strategy_type == "structural"]
        for c in structural:
            assert c.corollary5_sign == "leq_0"

    def test_build_error_classes_semantic_sign(self):
        classes = _build_error_classes()
        semantic = [c for c in classes if c.detection_strategy_type == "semantic"]
        for c in semantic:
            assert c.corollary5_sign == "gt_0"

    def test_build_error_classes_all_have_examples(self):
        classes = _build_error_classes()
        for c in classes:
            assert c.example is not None


# --- _build_dependency_graph ---


class TestBuildDependencyGraph:
    def test_build_dependency_graph_keys_match_claim_ids(self):
        claims = _build_claims()
        graph = _build_dependency_graph(claims)
        assert set(graph.keys()) == {c.claim_id for c in claims}

    def test_build_dependency_graph_operative_depends_on_epsilon(self):
        claims = _build_claims()
        graph = _build_dependency_graph(claims)
        assert "DEF_EPSILON" in graph["OPERATIVE"]

    def test_build_dependency_graph_pipeline_depends_on_operative(self):
        claims = _build_claims()
        graph = _build_dependency_graph(claims)
        assert "OPERATIVE" in graph["PIPELINE"]
