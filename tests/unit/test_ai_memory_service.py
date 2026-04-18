"""Unit tests — memory storage, retrieval, and deduplication."""
import pytest
from unittest.mock import patch

from backend.models.ai_knowledge import AIKnowledge
from backend.services.ai_trainer_service import (
    _text_similarity,
    store_memories,
    get_relevant_memories,
)


# ── _text_similarity ───────────────────────────────────────────────────────────

def test_similarity_identical():
    assert _text_similarity("bench press stalls", "bench press stalls") == 1.0


def test_similarity_completely_different():
    assert _text_similarity("bench press", "recovery sleep") == 0.0


def test_similarity_partial_overlap():
    score = _text_similarity("i play hockey wednesday", "hockey on wednesday evenings")
    assert 0.3 < score < 1.0


def test_similarity_empty_strings():
    assert _text_similarity("", "") == 0.0
    assert _text_similarity("something", "") == 0.0


# ── store_memories ─────────────────────────────────────────────────────────────

def test_store_memories_persists_new_entry(app, db, user_id):
    with app.app_context():
        store_memories(user_id, [
            {"category": "schedule", "text": "I train on Monday and Thursday", "priority": "high"}
        ])
        entries = AIKnowledge.query.filter_by(user_id=user_id, is_active=True).all()
        assert any("Monday" in e.text for e in entries)


def test_store_memories_skips_blank_text(app, db, user_id):
    with app.app_context():
        before = AIKnowledge.query.filter_by(user_id=user_id).count()
        store_memories(user_id, [
            {"category": "schedule", "text": "", "priority": "medium"},
            {"category": "other",    "text": "   ", "priority": "low"},
        ])
        after = AIKnowledge.query.filter_by(user_id=user_id).count()
        assert after == before


def test_store_memories_deduplicates_similar(app, db, user_id):
    with app.app_context():
        store_memories(user_id, [
            {"category": "schedule", "text": "I play hockey on Wednesday evenings", "priority": "high"}
        ])
        count_before = AIKnowledge.query.filter_by(user_id=user_id).count()

        # Very similar text — should be blocked
        store_memories(user_id, [
            {"category": "schedule", "text": "I play hockey wednesday evenings", "priority": "high"}
        ])
        count_after = AIKnowledge.query.filter_by(user_id=user_id).count()
        assert count_after == count_before


def test_store_memories_allows_different_text(app, db, user_id):
    with app.app_context():
        store_memories(user_id, [
            {"category": "recovery", "text": "Needs 48 hours after leg day", "priority": "medium"}
        ])
        count_before = AIKnowledge.query.filter_by(user_id=user_id).count()

        store_memories(user_id, [
            {"category": "preferences", "text": "Prefers front squats for warm-up", "priority": "low"}
        ])
        count_after = AIKnowledge.query.filter_by(user_id=user_id).count()
        assert count_after == count_before + 1


def test_store_memories_handles_empty_list(app, db, user_id):
    with app.app_context():
        before = AIKnowledge.query.filter_by(user_id=user_id).count()
        store_memories(user_id, [])
        after = AIKnowledge.query.filter_by(user_id=user_id).count()
        assert after == before


# ── get_relevant_memories ──────────────────────────────────────────────────────

def test_get_relevant_memories_returns_active_only(app, db, user_id):
    with app.app_context():
        # Add active and inactive entries
        db.session.add(AIKnowledge(
            user_id=user_id, type="memory", category="recovery",
            text="Active memory entry", is_active=True, priority="medium"
        ))
        db.session.add(AIKnowledge(
            user_id=user_id, type="memory", category="recovery",
            text="Inactive memory entry", is_active=False, priority="medium"
        ))
        db.session.commit()

        memories = get_relevant_memories(user_id)
        texts = [m["text"] for m in memories]
        assert "Active memory entry" in texts
        assert "Inactive memory entry" not in texts


def test_get_relevant_memories_respects_limit(app, db, user_id):
    with app.app_context():
        for i in range(10):
            db.session.add(AIKnowledge(
                user_id=user_id, type="memory", category="other",
                text=f"Unique memory entry number {i} with distinct content",
                is_active=True, priority="low"
            ))
        db.session.commit()

        memories = get_relevant_memories(user_id, limit=3)
        assert len(memories) <= 3


def test_get_relevant_memories_user_scoped(app, db, user_id):
    with app.app_context():
        other_user_id = 9999
        db.session.add(AIKnowledge(
            user_id=other_user_id, type="memory", category="schedule",
            text="Other user secret schedule info", is_active=True, priority="high"
        ))
        db.session.commit()

        memories = get_relevant_memories(user_id)
        texts = [m["text"] for m in memories]
        assert "Other user secret schedule info" not in texts


def test_get_relevant_memories_high_priority_first(app, db, user_id):
    with app.app_context():
        db.session.add(AIKnowledge(
            user_id=user_id, type="memory", category="injury",
            text="High priority shoulder injury note", is_active=True, priority="high"
        ))
        db.session.add(AIKnowledge(
            user_id=user_id, type="memory", category="preferences",
            text="Low priority exercise preference note", is_active=True, priority="low"
        ))
        db.session.commit()

        memories = get_relevant_memories(user_id, limit=12)
        priorities = [m["priority"] for m in memories]
        high_idx = next((i for i, p in enumerate(priorities) if p == "high"), None)
        low_idx  = next((i for i, p in enumerate(priorities) if p == "low"),  None)
        if high_idx is not None and low_idx is not None:
            assert high_idx < low_idx
