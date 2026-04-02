"""Property-based tests using Hypothesis for mathematical and string-matching logic."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from pals_check.references import _title_match


# --- _title_match properties ---


class TestTitleMatchProperties:
    @given(st.text(min_size=1, max_size=200))
    @settings(max_examples=100)
    def test_title_match_self_is_max_or_zero(self, title: str):
        """Matching a title against itself should yield 1.0 (or 0.0 if no valid words)."""
        score = _title_match(title, title)
        assert score == 0.0 or score == 1.0

    @given(st.text(min_size=1, max_size=200), st.text(min_size=1, max_size=200))
    @settings(max_examples=100)
    def test_title_match_bounded_zero_to_one(self, a: str, b: str):
        """Score must always be in [0.0, 1.0]."""
        score = _title_match(a, b)
        assert 0.0 <= score <= 1.0

    @given(st.text(min_size=0, max_size=200))
    @settings(max_examples=50)
    def test_title_match_empty_claimed_returns_zero(self, fetched: str):
        """Empty claimed title always returns 0.0."""
        assert _title_match("", fetched) == 0.0

    @given(st.text(min_size=0, max_size=200))
    @settings(max_examples=50)
    def test_title_match_empty_fetched_returns_zero(self, claimed: str):
        """Empty fetched title always returns 0.0."""
        assert _title_match(claimed, "") == 0.0

    @given(
        st.lists(st.from_regex(r"[a-z]{4,10}", fullmatch=True), min_size=3, max_size=8),
        st.lists(st.from_regex(r"[a-z]{4,10}", fullmatch=True), min_size=1, max_size=3),
    )
    @settings(max_examples=50)
    def test_title_match_superset_fetched_scores_one(self, words: list[str], extra: list[str]):
        """If fetched contains all claimed words (plus more), score should be 1.0."""
        claimed = " ".join(words)
        fetched = " ".join(words + extra)
        score = _title_match(claimed, fetched)
        assert score == 1.0

    @given(
        st.lists(st.from_regex(r"[a-z]{4,10}", fullmatch=True), min_size=2, max_size=6, unique=True),
    )
    @settings(max_examples=50)
    def test_title_match_disjoint_words_score_zero(self, words: list[str]):
        """Completely disjoint word sets should score 0.0."""
        mid = len(words) // 2
        if mid == 0:
            return  # Need at least 1 word per side
        claimed = " ".join(words[:mid])
        fetched = " ".join(words[mid:])
        score = _title_match(claimed, fetched)
        assert score == 0.0
