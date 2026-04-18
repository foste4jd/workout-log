"""Unit tests — AIKnowledge model."""
import json
import pytest
from datetime import datetime, timezone

from backend.models.ai_knowledge import AIKnowledge


def test_to_dict_has_required_keys(app, db):
    with app.app_context():
        entry = AIKnowledge(
            user_id=1,
            type="memory",
            category="schedule",
            text="I train Monday/Wednesday/Friday",
            priority="high",
            source_type="user_prompt",
        )
        db.session.add(entry)
        db.session.commit()

        d = entry.to_dict()
        for key in ("id", "user_id", "type", "category", "text",
                    "priority", "source_type", "is_active",
                    "created_at", "updated_at", "last_used_at"):
            assert key in d, f"Missing key: {key}"


def test_get_meta_returns_empty_dict_when_null(app, db):
    with app.app_context():
        entry = AIKnowledge(
            user_id=1, type="memory", category="other", text="test", meta=None
        )
        assert entry.get_meta() == {}


def test_get_meta_parses_json(app, db):
    with app.app_context():
        entry = AIKnowledge(
            user_id=1, type="memory", category="other",
            text="test", meta=json.dumps({"source_url": "https://example.com"})
        )
        assert entry.get_meta()["source_url"] == "https://example.com"


def test_get_meta_handles_corrupt_json(app, db):
    with app.app_context():
        entry = AIKnowledge(
            user_id=1, type="memory", category="other",
            text="test", meta="not-valid-json{{{"
        )
        assert entry.get_meta() == {}


def test_defaults(app, db):
    with app.app_context():
        entry = AIKnowledge(
            user_id=1, type="memory", category="other", text="test"
        )
        db.session.add(entry)
        db.session.commit()

        assert entry.is_active is True
        assert entry.priority == "medium"
        assert entry.created_at is not None
