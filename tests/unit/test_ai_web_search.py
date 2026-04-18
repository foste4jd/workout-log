"""
Unit tests — Phase 2 web search: classification, search execution,
distillation, memory storage.
"""
import json
import pytest
from unittest.mock import patch, MagicMock

from backend.services.ai_trainer_service import (
    _classify_needs_search,
    search_web,
    _distill_search_results,
    _store_web_knowledge,
    _build_user_message,
)
from backend.models.ai_knowledge import AIKnowledge


# ── _classify_needs_search ─────────────────────────────────────────────────────

class TestClassifyNeedsSearch:
    def test_educational_evidence_question(self):
        assert _classify_needs_search(
            "what does evidence suggest about deload frequency"
        ) is True

    def test_hypertrophy_question(self):
        assert _classify_needs_search(
            "is high volume better for hypertrophy"
        ) is True

    def test_rep_range_question(self):
        assert _classify_needs_search(
            "what is a good rep range for hypertrophy"
        ) is True

    def test_accessory_question(self):
        assert _classify_needs_search(
            "best accessory lifts for weak hamstrings"
        ) is True

    def test_injury_question(self):
        assert _classify_needs_search(
            "what are common causes of elbow irritation from bench pressing"
        ) is True

    def test_research_question(self):
        assert _classify_needs_search(
            "what does the research say about training frequency"
        ) is True

    def test_workout_generation_blocked(self):
        assert _classify_needs_search("build me a leg day") is False

    def test_workout_generation_upper_body_blocked(self):
        assert _classify_needs_search("give me an upper body workout") is False

    def test_workout_generation_create_blocked(self):
        assert _classify_needs_search("create a full body program for me") is False

    def test_personal_history_blocked(self):
        assert _classify_needs_search("how is my squat progressing") is False

    def test_personal_this_week_blocked(self):
        assert _classify_needs_search("how am I doing this week") is False

    def test_blank_returns_false(self):
        assert _classify_needs_search("") is False

    def test_none_like_returns_false(self):
        assert _classify_needs_search("   ") is False

    def test_no_question_word_returns_false(self):
        # Educational keyword but no question word
        assert _classify_needs_search("hypertrophy deload periodization") is False

    def test_short_prompt_returns_false(self):
        assert _classify_needs_search("hi") is False

    def test_todays_workout_blocked(self):
        assert _classify_needs_search("give me today's workout") is False


# ── search_web ────────────────────────────────────────────────────────────────

class TestSearchWeb:
    def test_missing_api_key_returns_empty(self):
        with patch.dict("os.environ", {}, clear=True):
            # Ensure TAVILY_API_KEY is absent
            import os
            os.environ.pop("TAVILY_API_KEY", None)
            result = search_web("what is hypertrophy")
        assert result == []

    def test_tavily_exception_returns_empty(self):
        with patch.dict("os.environ", {"TAVILY_API_KEY": "fake-key"}):
            with patch("tavily.TavilyClient") as mock_cls:
                mock_cls.return_value.search.side_effect = Exception("connection error")
                result = search_web("what is hypertrophy")
        assert result == []

    def test_returns_compact_results(self):
        fake_resp = {
            "results": [
                {"title": "Hypertrophy Guide", "url": "http://ex.com/1",
                 "content": "x" * 800},  # long content should be truncated
                {"title": "Volume Research",   "url": "http://ex.com/2",
                 "content": "Volume matters."},
            ]
        }
        with patch.dict("os.environ", {"TAVILY_API_KEY": "fake-key"}):
            with patch("tavily.TavilyClient") as mock_cls:
                mock_cls.return_value.search.return_value = fake_resp
                results = search_web("hypertrophy volume")

        assert len(results) == 2
        for r in results:
            assert "title"   in r
            assert "url"     in r
            assert "content" in r
            # Content should be capped
            assert len(r["content"]) <= 600 + 5  # MAX_SEARCH_CHARS + buffer

    def test_caps_at_max_results(self):
        """Even if Tavily returns more, we cap at MAX_SEARCH_RESULTS."""
        fake_resp = {
            "results": [
                {"title": f"Source {i}", "url": f"http://ex.com/{i}", "content": "text"}
                for i in range(10)
            ]
        }
        with patch.dict("os.environ", {"TAVILY_API_KEY": "fake-key"}):
            with patch("tavily.TavilyClient") as mock_cls:
                mock_cls.return_value.search.return_value = fake_resp
                results = search_web("test")

        from backend import ai_config
        assert len(results) <= ai_config.MAX_SEARCH_RESULTS

    def test_empty_results_from_tavily_returns_empty(self):
        with patch.dict("os.environ", {"TAVILY_API_KEY": "fake-key"}):
            with patch("tavily.TavilyClient") as mock_cls:
                mock_cls.return_value.search.return_value = {"results": []}
                result = search_web("test")
        assert result == []


# ── _distill_search_results ───────────────────────────────────────────────────

class TestDistillSearchResults:
    def _make_provider(self, response_dict):
        from backend.services.ai_trainer_service import OpenAIProvider
        provider = MagicMock(spec=OpenAIProvider)
        provider.complete_mini.return_value = json.dumps(response_dict)
        provider.last_usage = {}
        return provider

    def test_returns_summary_and_sources(self):
        provider = self._make_provider({
            "summary": "High volume supports hypertrophy when intensity is sufficient.",
            "sources": [{"title": "Research Paper", "url": "http://ex.com"}],
        })
        summary, sources = _distill_search_results(
            [{"title": "T", "url": "u", "content": "c"}],
            "is high volume better for hypertrophy",
            provider,
        )
        assert "hypertrophy" in summary
        assert len(sources) == 1
        assert sources[0]["url"] == "http://ex.com"

    def test_empty_results_returns_empty(self):
        provider = self._make_provider({"summary": "", "sources": []})
        summary, sources = _distill_search_results([], "test", provider)
        assert summary == ""
        assert sources == []

    def test_truncates_long_summary(self):
        provider = self._make_provider({
            "summary": "x" * 1000,
            "sources": [],
        })
        summary, _ = _distill_search_results(
            [{"title": "T", "url": "u", "content": "c"}],
            "test",
            provider,
        )
        from backend import ai_config
        assert len(summary) <= ai_config.SEARCH_DISTILL_CHARS

    def test_complete_mini_failure_returns_empty(self):
        from backend.services.ai_trainer_service import OpenAIProvider
        provider = MagicMock(spec=OpenAIProvider)
        provider.complete_mini.side_effect = Exception("API down")
        summary, sources = _distill_search_results(
            [{"title": "T", "url": "u", "content": "c"}],
            "test",
            provider,
        )
        assert summary == ""
        assert sources == []

    def test_caps_sources_at_two(self):
        provider = self._make_provider({
            "summary": "Some insight.",
            "sources": [
                {"title": "A", "url": "u1"},
                {"title": "B", "url": "u2"},
                {"title": "C", "url": "u3"},  # should be dropped
            ],
        })
        _, sources = _distill_search_results(
            [{"title": "T", "url": "u", "content": "c"}],
            "test",
            provider,
        )
        assert len(sources) <= 2


# ── _store_web_knowledge ──────────────────────────────────────────────────────

class TestStoreWebKnowledge:
    def test_stores_new_knowledge(self, app, db, user_id):
        with app.app_context():
            before = AIKnowledge.query.filter_by(
                user_id=user_id, source_type="web_reference"
            ).count()
            _store_web_knowledge(
                user_id,
                "what does evidence say about deload frequency",
                "Deloads every 4-6 weeks are commonly recommended based on accumulated fatigue markers.",
                [{"title": "Source", "url": "http://ex.com"}],
            )
            entries = AIKnowledge.query.filter_by(
                user_id=user_id, source_type="web_reference"
            ).all()
            assert len(entries) == before + 1
            assert any("deload" in e.text.lower() for e in entries)

    def test_skips_trivially_short_text(self, app, db, user_id):
        with app.app_context():
            before = AIKnowledge.query.filter_by(
                user_id=user_id, source_type="web_reference"
            ).count()
            _store_web_knowledge(user_id, "query", "Too short.", [])
            after = AIKnowledge.query.filter_by(
                user_id=user_id, source_type="web_reference"
            ).count()
            assert after == before

    def test_deduplicates_similar_knowledge(self, app, db, user_id):
        with app.app_context():
            text = "Deloads every 4-6 weeks help manage accumulated fatigue in trained athletes."
            _store_web_knowledge(user_id, "deload query", text, [])
            count_before = AIKnowledge.query.filter_by(
                user_id=user_id, source_type="web_reference"
            ).count()

            # Near-duplicate — should be skipped
            _store_web_knowledge(user_id, "deload query 2",
                                 "Deloads every 4-6 weeks manage accumulated fatigue in athletes.", [])
            count_after = AIKnowledge.query.filter_by(
                user_id=user_id, source_type="web_reference"
            ).count()
            assert count_after == count_before

    def test_stores_source_metadata_in_meta_field(self, app, db, user_id):
        with app.app_context():
            _store_web_knowledge(
                user_id,
                "hypertrophy rep range",
                "Hypertrophy can occur across a wide rep range when volume is equated.",
                [{"title": "Schoenfeld 2017", "url": "http://pubmed.com/123"}],
            )
            entry = AIKnowledge.query.filter_by(
                user_id=user_id, source_type="web_reference"
            ).first()
            meta = entry.get_meta()
            assert "query" in meta
            assert "sources" in meta

    def test_marked_as_web_reference_source_type(self, app, db, user_id):
        with app.app_context():
            _store_web_knowledge(
                user_id,
                "training frequency",
                "Training each muscle 2x per week is a common evidence-based recommendation.",
                [],
            )
            entry = AIKnowledge.query.filter_by(
                user_id=user_id, source_type="web_reference"
            ).first()
            assert entry is not None
            assert entry.source_type == "web_reference"
            assert entry.priority == "low"


# ── _build_user_message with search context ───────────────────────────────────

class TestBuildUserMessageWithSearch:
    def test_search_context_injected_when_present(self, app, db, user_id):
        with app.app_context():
            from backend.services.ai_trainer_service import build_context
            ctx = build_context(user_id)
            msg = _build_user_message(
                ctx, "what does evidence say about deload",
                search_context="Deloads every 4-6 weeks are commonly supported by research.",
            )
            assert "WEB REFERENCE" in msg
            assert "Deloads every 4-6 weeks" in msg
            assert "supplementary" in msg.lower()

    def test_no_search_context_no_web_reference_section(self, app, db, user_id):
        with app.app_context():
            from backend.services.ai_trainer_service import build_context
            ctx = build_context(user_id)
            msg = _build_user_message(ctx, "heavy leg day", search_context="")
            assert "WEB REFERENCE" not in msg
