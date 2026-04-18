# AI Trainer — Full Implementation Plan

This document is the single source of truth for building the AI trainer feature.
It consolidates the design in `ai-trainer-plan.md` and `ai-trainer-memory.md` into
exact file contents and a build order with checkpoints.

---

## Dependencies

Add to requirements.txt (or `pip install` before starting):

```
anthropic>=0.25.0
apscheduler>=3.10.0
tavily-python>=0.3.0   # Phase 2 only
```

Set in environment (add to `.env` or shell):

```
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...          # Phase 2 only
```

---

## Phase 1 — Core (no web search)

Build order: model → service → route → Mode 1 UI → Mode 2 UI → memory reads

---

### Step 1 — AIKnowledge model

**New file: `backend/models/ai_knowledge.py`**

```python
import json
from datetime import datetime, timezone
from backend.db.database import db


class AIKnowledge(db.Model):
    __tablename__ = "ai_knowledge"

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    type         = db.Column(db.String(20), nullable=False)   # 'external' | 'user_pattern'
    category     = db.Column(db.String(40), nullable=False)   # 'programming' | 'exercise_science' |
                                                              #  'periodization' | 'recovery' |
                                                              #  'technique' | 'user_pattern'
    tags         = db.Column(db.Text, nullable=False)         # JSON array string
    summary      = db.Column(db.String(300), nullable=False)
    source       = db.Column(db.Text, nullable=True)          # URL for external, NULL for patterns
    confidence   = db.Column(db.Float, default=1.0)
    archived     = db.Column(db.Boolean, default=False)
    created_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_used_at = db.Column(db.DateTime, nullable=True)
    use_count    = db.Column(db.Integer, default=0)

    def get_tags(self):
        return json.loads(self.tags) if self.tags else []

    def to_dict(self):
        return {
            "id":           self.id,
            "type":         self.type,
            "category":     self.category,
            "tags":         self.get_tags(),
            "summary":      self.summary,
            "source":       self.source,
            "confidence":   self.confidence,
            "use_count":    self.use_count,
            "created_at":   self.created_at.isoformat() if self.created_at else None,
        }
```

---

### Step 2 — Register model + migration in app.py

**`backend/app.py` changes:**

1. Add model import (with the other model imports):
```python
from backend.models.ai_knowledge import AIKnowledge  # noqa: F401
```

2. Add blueprint registration (with the other imports and the `for bp in (...)` list):
```python
from backend.api.routes.ai_trainer import ai_trainer_bp
# add ai_trainer_bp to the for bp in (...) tuple
```

3. Add migration statements (append to the `migrations` list in `_run_migrations()`):
```python
"ALTER TABLE ai_knowledge ADD COLUMN archived BOOLEAN NOT NULL DEFAULT 0",
```
Note: `db.create_all()` handles new tables, so only ALTER TABLE statements for
*new columns on existing tables* go in the migration list. The `ai_knowledge`
table itself will be created by `db.create_all()` once the model is imported.

---

### Step 3 — AI Trainer Service

**New file: `backend/services/ai_trainer_service.py`**

```python
import json
import os
from datetime import datetime, timezone, timedelta

from anthropic import Anthropic

from backend.db.database import db
from backend.models.workout import Workout
from backend.models.exercise import Exercise
from backend.models.exercise_set import ExerciseSet
from backend.models.training_max import TrainingMax
from backend.models.exercise_library import ExerciseLibrary
from backend.models.ai_knowledge import AIKnowledge

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# ── Movement pattern map ──────────────────────────────────────────────────────
# Maps exercise library categories to movement patterns for the recency map.

CATEGORY_TO_PATTERN = {
    "Squat":    "squat",
    "Hinge":    "hinge",
    "Press":    "horizontal_push",   # refined below for overhead
    "Pull":     "vertical_pull",
    "Olympic":  "hinge",
    "Arms":     "arms",
    "Shoulders":"horizontal_push",
    "Chest":    "horizontal_push",
    "Glutes":   "hinge",
    "Legs":     "squat",
    "Carry":    "carry",
    "Core":     "core",
}

OVERHEAD_PRESS_NAMES = {
    "Overhead Press", "Arnold Press", "Seated Dumbbell Press",
    "Machine Shoulder Press", "Handstand Push-up", "Strict Handstand Push-up",
    "Thruster", "Dumbbell Thruster", "Push Jerk", "Split Jerk", "Jerk",
}

ROW_NAMES = {
    "Bent Over Row", "T-Bar Row", "Seated Cable Row",
    "Single Arm Dumbbell Row", "Upright Row",
}


# ── Context builder ───────────────────────────────────────────────────────────

def build_context(user_id, days=21):
    """Return a dict that gets serialised into the Claude system prompt."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # 1. Recent workouts with exercises and sets
    workouts = (
        Workout.query
        .filter(Workout.user_id == user_id, Workout.date >= since)
        .order_by(Workout.date.desc())
        .all()
    )
    workout_data = []
    for w in workouts:
        exercises = []
        for ex in w.exercises:
            sets = []
            for s in ex.sets:
                sets.append({
                    "set_type":  s.set_type,
                    "reps":      s.reps,
                    "weight_lb": s.weight_lb,
                    "percent":   s.percent,
                    "completed": s.completed,
                })
            exercises.append({
                "name":                ex.exercise_library.name if ex.exercise_library else ex.name,
                "exercise_library_id": ex.exercise_library_id,
                "category":            ex.exercise_library.category if ex.exercise_library else None,
                "sets":                sets,
            })
        workout_data.append({
            "id":               w.id,
            "date":             w.date.strftime("%Y-%m-%d"),
            "title":            w.title,
            "duration_minutes": w.duration_minutes,
            "exercises":        exercises,
        })

    # 2. Training maxes
    tms = TrainingMax.query.filter_by(user_id=user_id).all()
    training_maxes = {}
    for tm in tms:
        lib = ExerciseLibrary.query.get(tm.exercise_library_id)
        if lib:
            training_maxes[lib.name] = tm.weight_lb

    # 3. Recency map — days since each movement pattern was last trained
    recency = _build_recency_map(workouts)

    # 4. Performance trends — last 4 sessions per key lift
    trends = _build_trends(workouts)

    # 5. Exercise library (for name matching)
    library = ExerciseLibrary.query.order_by(ExerciseLibrary.category, ExerciseLibrary.name).all()
    library_list = [{"id": e.id, "name": e.name, "category": e.category} for e in library]

    # 6. Relevant knowledge from memory
    relevant_tags = _extract_tags(recency, trends, training_maxes)
    knowledge = _get_relevant_knowledge(user_id, relevant_tags, limit=8)

    return {
        "workouts":       workout_data,
        "training_maxes": training_maxes,
        "recency":        recency,
        "trends":         trends,
        "library":        library_list,
        "knowledge":      knowledge,
        "today":          datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }


def _build_recency_map(workouts):
    """Return {pattern: days_since_last_trained}. None means never trained."""
    today = datetime.now(timezone.utc).date()
    last_trained = {}  # pattern -> date

    for w in workouts:
        w_date = w.date.date() if hasattr(w.date, "date") else w.date
        for ex in w.exercises:
            if not ex.exercise_library:
                continue
            pattern = _exercise_to_pattern(ex.exercise_library)
            if pattern and (pattern not in last_trained or w_date > last_trained[pattern]):
                last_trained[pattern] = w_date

    all_patterns = [
        "squat", "hinge", "horizontal_push", "horizontal_pull",
        "vertical_pull", "arms", "carry", "core"
    ]
    recency = {}
    for p in all_patterns:
        if p in last_trained:
            recency[p] = (today - last_trained[p]).days
        else:
            recency[p] = None  # never trained in window

    return recency


def _exercise_to_pattern(lib_entry):
    if lib_entry.name in OVERHEAD_PRESS_NAMES:
        return "vertical_push"
    if lib_entry.name in ROW_NAMES:
        return "horizontal_pull"
    return CATEGORY_TO_PATTERN.get(lib_entry.category)


def _build_trends(workouts):
    """For each lift trained in the last 4 sessions, note trend + missed reps."""
    # Gather last 4 sessions per exercise (by library name)
    sessions_by_exercise = {}
    for w in workouts:
        for ex in w.exercises:
            name = ex.exercise_library.name if ex.exercise_library else None
            if not name:
                continue
            if name not in sessions_by_exercise:
                sessions_by_exercise[name] = []
            if len(sessions_by_exercise[name]) < 4:
                sessions_by_exercise[name].append({
                    "date":   w.date.strftime("%Y-%m-%d"),
                    "sets":   [{"reps": s.reps, "weight_lb": s.weight_lb,
                                "percent": s.percent, "completed": s.completed}
                               for s in ex.sets],
                })

    trends = {}
    for name, sessions in sessions_by_exercise.items():
        if not sessions:
            continue
        latest = sessions[0]
        missed_last = any(not s["completed"] for s in latest["sets"])

        # Simple trend: compare average weight of latest vs oldest in window
        def avg_weight(sess):
            ws = [s["weight_lb"] for s in sess["sets"] if s.get("weight_lb")]
            return sum(ws) / len(ws) if ws else 0

        if len(sessions) >= 2:
            latest_avg = avg_weight(sessions[0])
            oldest_avg = avg_weight(sessions[-1])
            if latest_avg > oldest_avg * 1.02:
                trend = "progressing"
            elif latest_avg < oldest_avg * 0.98:
                trend = "declining"
            else:
                trend = "stalled"
        else:
            trend = "insufficient_data"

        trends[name] = {
            "trend":                   trend,
            "missed_reps_last_session": missed_last,
            "sessions":                sessions,
        }

    return trends


def _extract_tags(recency, trends, training_maxes):
    """Build a tag list from current context to query the knowledge table."""
    tags = set()

    # Add tags for exercises that are stalled or have missed reps
    for name, t in trends.items():
        name_lower = name.lower().replace(" ", "_")
        tags.add(name_lower)
        if t["trend"] == "stalled":
            tags.update(["plateau", "stall"])
        if t["missed_reps_last_session"]:
            tags.add("missed_reps")

    # Add tags for movement patterns trained today or recently
    for pattern, days in recency.items():
        if days is not None:
            tags.add(pattern)

    # Always include general programming
    tags.add("programming")
    return list(tags)


# ── Knowledge / Memory ────────────────────────────────────────────────────────

def _get_relevant_knowledge(user_id, tags, limit=8):
    """Fetch knowledge entries whose tags overlap with context tags."""
    if not tags:
        return []

    filters = [AIKnowledge.tags.contains(t) for t in tags]
    entries = (
        AIKnowledge.query
        .filter(
            db.or_(AIKnowledge.user_id == user_id, AIKnowledge.user_id.is_(None)),
            AIKnowledge.archived == False,
            db.or_(*filters),
        )
        .order_by(
            AIKnowledge.user_id.desc(),    # user-specific patterns first
            AIKnowledge.use_count.desc(),  # most-used first
        )
        .limit(limit)
        .all()
    )

    # Increment use_count
    now = datetime.now(timezone.utc)
    for e in entries:
        e.use_count += 1
        e.last_used_at = now
    db.session.commit()

    return [
        f"[{e.category}] {e.summary}"
        for e in entries
    ]


def is_duplicate(tags, summary, user_id=None):
    """Return True if we already have a very similar entry."""
    tag_set = set(tags)
    candidates = (
        AIKnowledge.query
        .filter(db.or_(AIKnowledge.user_id == user_id, AIKnowledge.user_id.is_(None)))
        .all()
    )
    for c in candidates:
        existing_tags = set(c.get_tags())
        overlap = len(tag_set & existing_tags) / max(len(tag_set | existing_tags), 1)
        if overlap > 0.6 and abs(len(summary) - len(c.summary)) < 50:
            return True
    return False


def distill_and_store(search_query, raw_results, source_url=None):
    """Called after every web search. Distils the result into one entry."""
    prompt = f"""Web search query: "{search_query}"
Raw results: {raw_results[:3000]}

Extract the single most useful, generalizable insight from these results
for a strength training context. Return JSON only, no markdown:

{{
  "summary": "one sentence, max 250 chars, the key actionable insight",
  "category": "programming|exercise_science|periodization|recovery|technique",
  "tags": ["tag1", "tag2"],
  "confidence": 0.85
}}

Do NOT include: author opinions, anecdotes, product recommendations, or anything
not directly applicable to strength training programming.
"""
    try:
        result = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        text = result.content[0].text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        entry = json.loads(text)

        if not is_duplicate(entry["tags"], entry["summary"]):
            db.session.add(AIKnowledge(
                user_id=None,
                type="external",
                tags=json.dumps(entry["tags"]),
                summary=entry["summary"][:300],
                category=entry["category"],
                source=source_url,
                confidence=entry.get("confidence", 0.9),
            ))
            db.session.commit()
    except Exception as e:
        # Distillation is best-effort — never block the main response
        print(f"[ai_memory] distill_and_store error: {e}")


def detect_user_patterns(user_id, app):
    """
    Weekly background job. Scans 90 days of history and stores new patterns.
    Must be called with app context: detect_user_patterns(user_id, app)
    """
    with app.app_context():
        context = build_context(user_id, days=90)
        existing = [
            e.summary for e in
            AIKnowledge.query.filter_by(user_id=user_id, type="user_pattern").all()
        ]

        prompt = f"""Analyze this athlete's 90-day training history.
Already known patterns (do not repeat these):
{json.dumps(existing, indent=2)}

Training data:
{json.dumps(context['workouts'], indent=2)}

Look for NEW, specific, repeatable patterns — things like:
- Performance correlations ("bench drops after back-to-back training days")
- Recovery signals ("deadlift suffers when squatted within 48hrs")
- Progression rates ("squat TM is likely 10-15lb behind actual strength")
- Volume responses ("performs better on 4+ sets than 2-3 sets")

Return a JSON array of NEW patterns only (empty array [] if nothing new):
[
  {{
    "summary": "one sentence, max 250 chars",
    "tags": ["user", "bench", "fatigue"],
    "confidence": 0.8
  }}
]

Only report patterns with at least 3 supporting data points. Do NOT speculate.
Return raw JSON only, no markdown.
"""
        try:
            result = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            text = result.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            patterns = json.loads(text)
            for p in patterns:
                if not is_duplicate(p["tags"], p["summary"], user_id):
                    db.session.add(AIKnowledge(
                        user_id=user_id,
                        type="user_pattern",
                        category="user_pattern",
                        tags=json.dumps(p["tags"]),
                        summary=p["summary"][:300],
                        confidence=p.get("confidence", 0.8),
                    ))
            db.session.commit()
        except Exception as e:
            print(f"[ai_memory] detect_user_patterns error: {e}")


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an experienced strength and conditioning coach with full access to
the athlete's recent training history, training maxes, and performance trends.

ALWAYS:
- Read the recency map before programming any lift — never load a movement pattern
  that was trained within the last 24 hours unless the athlete explicitly requests it.
- If an athlete missed reps last session on a lift, do NOT increase the percentage.
- If the athlete has trained 5+ days this week, suggest a deload or active recovery day.
- Match exercise names EXACTLY to the provided exercise library list.
- Return your response as valid JSON matching the schema below — no markdown, no prose outside the JSON.

RESPONSE SCHEMA:
{
  "reasoning": "2-3 sentence explanation of why you chose this workout",
  "reply": "conversational message to the athlete (chat mode only, omit in auto mode)",
  "workout": {
    "title": "Workout Title",
    "exercises": [
      {
        "name": "Exercise Name (must match library exactly)",
        "exercise_library_id": 1,
        "sets": [
          {
            "set_type": "working",
            "reps": 5,
            "percent": 75,
            "weight_lb": null
          }
        ]
      }
    ]
  }
}

Set fields:
- set_type: "warmup" | "working" | "amrap" | "emom" | "backoff"
- percent: percentage of training max (omit if not TM-based)
- weight_lb: absolute weight in lbs (omit if using percent)
- reps: target reps (omit for time-based sets)
- duration_seconds: for timed sets (omit otherwise)

IN CHAT MODE:
- Honor the athlete's stated constraints (equipment, muscle focus, time, injuries).
- If they push back or request changes, revise the workout and return a new JSON block.
- Keep "reply" concise — 2-3 sentences max before presenting the workout.

IN AUTO MODE:
- Omit the "reply" field.
- Decide the workout entirely based on history and recency.
- Explain the choice in 2-3 sentences in "reasoning".
"""


# ── Main handler ──────────────────────────────────────────────────────────────

def handle_request(user_id, mode, message=None, history=None, allow_web=False):
    """
    mode: "auto" | "chat"
    message: str (chat mode only)
    history: list of {"role": "user"|"assistant", "content": str}
    allow_web: bool — Phase 2: enables Tavily web search tool
    """
    context = build_context(user_id, days=21)
    context_block = _format_context_block(context)

    if mode == "auto":
        user_content = f"""{context_block}

Based on this athlete's history, build the best workout for today.
Consider the recency map, performance trends, and any known patterns."""
    else:
        user_content = f"""{context_block}

Athlete's request: {message}"""

    messages = list(history or []) + [{"role": "user", "content": user_content}]

    # Phase 2: add web search tool here
    tools = []
    if allow_web:
        tools = [_tavily_tool_definition()]

    kwargs = {
        "model":      "claude-opus-4-6",
        "max_tokens": 4096,
        "system":     SYSTEM_PROMPT,
        "messages":   messages,
    }
    if tools:
        kwargs["tools"] = tools

    response = client.messages.create(**kwargs)

    # Handle tool_use loop (Phase 2)
    while response.stop_reason == "tool_use":
        tool_result = _handle_tool_use(response, user_id)
        messages = messages + [
            {"role": "assistant", "content": response.content},
            {"role": "user",      "content": tool_result},
        ]
        response = client.messages.create(**kwargs | {"messages": messages})

    return _parse_response(response, mode)


def _format_context_block(context):
    lines = [
        f"TODAY: {context['today']}",
        "",
        "TRAINING MAXES:",
        json.dumps(context["training_maxes"], indent=2),
        "",
        "RECENCY MAP (days since last trained, None = not in last 21 days):",
        json.dumps(context["recency"], indent=2),
        "",
        "PERFORMANCE TRENDS (last 4 sessions per lift):",
        json.dumps(context["trends"], indent=2),
        "",
        "RECENT WORKOUTS (last 21 days, newest first):",
        json.dumps(context["workouts"], indent=2),
        "",
        "EXERCISE LIBRARY (use exact names from this list):",
        json.dumps(context["library"], indent=2),
    ]
    if context["knowledge"]:
        lines += [
            "",
            "RELEVANT KNOWLEDGE FROM MEMORY:",
            *context["knowledge"],
        ]
    return "\n".join(lines)


def _parse_response(response, mode):
    text = ""
    for block in response.content:
        if hasattr(block, "text"):
            text = block.text
            break

    # Strip markdown code fences
    clean = text.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
        clean = clean.rsplit("```")[0]

    try:
        data = json.loads(clean)
    except json.JSONDecodeError:
        # Fallback: return raw text so the caller has something
        return {
            "reasoning": "Unable to parse structured response.",
            "reply":     text,
            "workout":   None,
        }

    if mode == "auto" and "reply" not in data:
        data["reply"] = data.get("reasoning", "")

    return data


# ── Phase 2 stubs (filled in when Tavily is added) ───────────────────────────

def _tavily_tool_definition():
    return {
        "name":        "web_search",
        "description": "Search the web for strength training programming information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"}
            },
            "required": ["query"],
        },
    }


def _handle_tool_use(response, user_id):
    """Execute web search tool calls and return results as tool_result blocks."""
    results = []
    for block in response.content:
        if block.type != "tool_use":
            continue
        if block.name == "web_search":
            raw = _tavily_search(block.input["query"])
            # Async distillation — best effort
            try:
                distill_and_store(block.input["query"], raw)
            except Exception:
                pass
            results.append({
                "type":        "tool_result",
                "tool_use_id": block.id,
                "content":     raw[:4000],
            })
    return results


def _tavily_search(query):
    """Phase 2: real implementation. Returns stub text until Tavily is wired up."""
    try:
        from tavily import TavilyClient
        tc = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY", ""))
        result = tc.search(query, search_depth="basic", max_results=3)
        texts = [r.get("content", "") for r in result.get("results", [])]
        return "\n\n".join(texts)
    except Exception:
        return f"[web search not available: {query}]"
```

---

### Step 4 — AI Trainer Route

**New file: `backend/api/routes/ai_trainer.py`**

```python
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.services import ai_trainer_service

ai_trainer_bp = Blueprint("ai_trainer", __name__, url_prefix="/api/ai")


@ai_trainer_bp.post("/suggest")
@jwt_required()
def suggest():
    user_id = int(get_jwt_identity())
    data    = request.get_json() or {}

    mode      = data.get("mode", "auto")        # "auto" | "chat"
    message   = data.get("message")             # chat mode only
    history   = data.get("history", [])         # list of {role, content}
    allow_web = data.get("allow_web", False)

    if mode not in ("auto", "chat"):
        return jsonify({"error": "mode must be 'auto' or 'chat'"}), 400
    if mode == "chat" and not message:
        return jsonify({"error": "message is required in chat mode"}), 400

    result = ai_trainer_service.handle_request(
        user_id   = user_id,
        mode      = mode,
        message   = message,
        history   = history,
        allow_web = allow_web,
    )
    return jsonify(result)
```

---

### Step 5 — Register in app.py (complete diff)

```python
# In the model imports block, add:
from backend.models.ai_knowledge import AIKnowledge  # noqa: F401

# In the blueprint imports block, add:
from backend.api.routes.ai_trainer import ai_trainer_bp

# In the for bp in (...) tuple, add ai_trainer_bp
for bp in (
    users_bp, workouts_bp, exercises_bp, views_bp, stats_bp,
    maxes_bp, library_bp, training_maxes_bp, templates_bp,
    ai_trainer_bp,   # ← add this
):
    app.register_blueprint(bp)

# In _run_migrations(), the ai_knowledge table is created by db.create_all().
# No ALTER TABLE needed unless you add columns to it later.
```

---

### Step 6 — APScheduler (weekly pattern detection)

Add to `app.py` `create_app()` after `db.create_all()`:

```python
def _start_scheduler(app):
    from apscheduler.schedulers.background import BackgroundScheduler
    from backend.services.ai_trainer_service import detect_user_patterns
    from backend.models.user import User

    def run_pattern_detection():
        with app.app_context():
            users = User.query.all()
            for user in users:
                detect_user_patterns(user.id, app)

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_pattern_detection,
        trigger="cron",
        day_of_week="sun",
        hour=3,
        minute=0,
        id="weekly_pattern_detection",
        replace_existing=True,
    )
    scheduler.start()
```

Then call `_start_scheduler(app)` at the bottom of `create_app()`, before `return app`.

---

### ✅ Checkpoint 1 — Test the API

Start the server and test both modes:

```bash
# Auto mode
curl -X POST http://localhost:8080/api/ai/suggest \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"mode": "auto"}'

# Chat mode
curl -X POST http://localhost:8080/api/ai/suggest \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"mode": "chat", "message": "Give me a heavy leg day"}'
```

Expected: JSON response with `reasoning`, `reply`, and `workout` fields.

---

### Step 7 — Mode 1: "Build My Workout" card on /log page

Add the following HTML block to `frontend/templates/log.html`, **above** the
`#exercise-builder` section (find `<!-- EXERCISES -->` or the builder div):

```html
<!-- ── AI Trainer Card ──────────────────────────────────────────── -->
<div class="ai-trainer-card" id="ai-trainer-card">
  <div class="ai-trainer-header" onclick="toggleTrainerCard()">
    <span class="ai-trainer-icon">✦</span>
    <span class="ai-trainer-title">AI TRAINER</span>
    <span class="ai-trainer-toggle" id="ai-trainer-chevron">▼</span>
  </div>
  <div class="ai-trainer-body" id="ai-trainer-body">
    <p class="ai-trainer-tagline">Not sure what to do today? Let the trainer decide.</p>
    <label class="ai-web-toggle">
      <input type="checkbox" id="ai-allow-web"> Also search the web for programming ideas
    </label>
    <button class="btn-primary ai-build-btn" id="ai-build-btn" onclick="buildAIWorkout()">
      Build My Workout →
    </button>
    <div class="ai-reasoning-box" id="ai-reasoning-box" style="display:none;">
      <div class="ai-reasoning-label">Trainer's Reasoning</div>
      <div class="ai-reasoning-text" id="ai-reasoning-text"></div>
    </div>
  </div>
</div>
```

Add the following JS to the `<script>` block at the bottom of `log.html`:

```javascript
function toggleTrainerCard() {
  const body    = document.getElementById("ai-trainer-body");
  const chevron = document.getElementById("ai-trainer-chevron");
  const open    = body.style.display !== "none";
  body.style.display  = open ? "none" : "block";
  chevron.textContent = open ? "▶" : "▼";
}

async function buildAIWorkout() {
  const btn       = document.getElementById("ai-build-btn");
  const allowWeb  = document.getElementById("ai-allow-web").checked;
  const reasoning = document.getElementById("ai-reasoning-box");
  const reasonTxt = document.getElementById("ai-reasoning-text");

  btn.disabled    = true;
  btn.textContent = "Building…";

  try {
    const res = await apiFetch("/api/ai/suggest", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ mode: "auto", allow_web: allowWeb }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Request failed");

    // Show reasoning
    reasonTxt.textContent = data.reasoning || "";
    reasoning.style.display = "block";

    // Populate the workout builder
    if (data.workout) {
      document.getElementById("workout-title").value = data.workout.title || "";
      clearExercises();
      for (const ex of data.workout.exercises || []) {
        addExerciseFromAI(ex);
      }
    }
  } catch (err) {
    alert("Trainer error: " + err.message);
  } finally {
    btn.disabled    = false;
    btn.textContent = "Build My Workout →";
  }
}

function clearExercises() {
  // Clear all current exercise rows from the builder
  const container = document.getElementById("exercises-container");
  if (container) container.innerHTML = "";
}

function addExerciseFromAI(ex) {
  // Re-use the existing addExercise() helper, then populate its sets.
  // Assumes addExercise() returns a reference or appends to exercises array.
  const idx = exercises.length;
  exercises.push({
    name:                ex.name || "",
    exercise_library_id: ex.exercise_library_id || null,
    sets:                [],
  });

  // Add sets
  for (const s of ex.sets || []) {
    exercises[idx].sets.push({
      set_type:         s.set_type || "working",
      reps:             s.reps || null,
      weight_lb:        s.weight_lb || null,
      percent:          s.percent || null,
      duration_seconds: s.duration_seconds || null,
      completed:        true,
    });
  }

  renderBuilder();
}
```

> **Note:** The exact integration with `addExercise()` / `renderBuilder()` depends
> on the current log.html JS structure. Adjust the `addExerciseFromAI` implementation
> to match the existing exercise array and render pattern.

---

### Step 8 — Mode 2: /trainer chat page

**New file: `frontend/templates/trainer.html`**

This is the full page. It uses the same nav as dashboard.html and the same
`apiFetch` / unit utilities from main.js.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Trainer — WorkoutLog</title>
  <link rel="stylesheet" href="/static/css/main.css">
</head>
<body>
  <nav class="navbar">
    <a class="nav-brand" href="/dashboard">WorkoutLog</a>
    <div class="nav-links">
      <a href="/dashboard">Dashboard</a>
      <a href="/workouts">Workouts</a>
      <a href="/templates">Templates</a>
      <a href="/maxes">Maxes</a>
      <a href="/trainer" class="active">Trainer</a>
    </div>
    <div class="nav-right">
      <button class="unit-toggle" id="unit-toggle-btn">lbs</button>
      <a href="#" onclick="logout()">Logout</a>
    </div>
  </nav>

  <main class="trainer-page">
    <div class="trainer-header">
      <h1>Your Trainer</h1>
      <p>Knows your last 21 days of training. Ask it anything.</p>
    </div>

    <div class="trainer-conversation" id="conversation">
      <!-- Messages rendered here by JS -->
      <div class="trainer-empty" id="trainer-empty">
        <p>Start a conversation. Try:</p>
        <div class="trainer-suggestions">
          <button onclick="sendSuggestion(this)">Heavy leg day, just a squat rack</button>
          <button onclick="sendSuggestion(this)">Full body, only 40 minutes</button>
          <button onclick="sendSuggestion(this)">My lower back is sore — upper body day</button>
          <button onclick="sendSuggestion(this)">Deload week — what should I do?</button>
          <button onclick="sendSuggestion(this)">Am I overtraining this week?</button>
        </div>
      </div>
    </div>

    <div class="trainer-input-area">
      <div class="trainer-web-toggle">
        <label>
          <input type="checkbox" id="trainer-allow-web">
          Let trainer search the web
        </label>
      </div>
      <div class="trainer-input-row">
        <textarea
          id="trainer-input"
          placeholder='Type anything — e.g. "push day, 45 minutes, no bench"'
          rows="2"
          onkeydown="handleTrainerKey(event)"
        ></textarea>
        <button class="btn-primary trainer-send-btn" id="trainer-send-btn" onclick="sendMessage()">
          Send ▶
        </button>
      </div>
    </div>
  </main>

  <script src="/static/js/main.js"></script>
  <script>
    // ── Conversation state ────────────────────────────────────────────────────
    let history = [];  // [{role, content}] — session only, not persisted

    // Restore from sessionStorage on load (survives refresh, not browser close)
    function loadSession() {
      const saved = sessionStorage.getItem("trainerHistory");
      if (saved) {
        history = JSON.parse(saved);
        renderHistory();
      }
    }

    function saveSession() {
      sessionStorage.setItem("trainerHistory", JSON.stringify(history));
    }

    // ── Render ────────────────────────────────────────────────────────────────
    function renderHistory() {
      const conv  = document.getElementById("conversation");
      const empty = document.getElementById("trainer-empty");
      if (history.length === 0) {
        empty.style.display = "block";
        return;
      }
      empty.style.display = "none";

      // Re-render all messages
      const existing = conv.querySelectorAll(".trainer-bubble");
      existing.forEach(el => el.remove());

      for (const msg of history) {
        conv.appendChild(buildBubble(msg.role, msg.content, msg.workout));
      }
      conv.scrollTop = conv.scrollHeight;
    }

    function buildBubble(role, content, workout) {
      const wrap = document.createElement("div");
      wrap.className = `trainer-bubble trainer-bubble--${role}`;

      const label = document.createElement("div");
      label.className = "trainer-bubble-label";
      label.textContent = role === "user" ? "You" : "Trainer";
      wrap.appendChild(label);

      const text = document.createElement("div");
      text.className = "trainer-bubble-text";
      text.textContent = content;
      wrap.appendChild(text);

      if (workout && role === "assistant") {
        wrap.appendChild(buildWorkoutBlock(workout));
      }
      return wrap;
    }

    function buildWorkoutBlock(workout) {
      const block = document.createElement("div");
      block.className = "trainer-workout-block";

      const title = document.createElement("div");
      title.className = "trainer-workout-title";
      title.textContent = workout.title || "Suggested Workout";
      block.appendChild(title);

      for (const ex of workout.exercises || []) {
        const row = document.createElement("div");
        row.className = "trainer-workout-exercise";

        const name = document.createElement("span");
        name.className = "trainer-ex-name";
        name.textContent = ex.name;
        row.appendChild(name);

        const sets = document.createElement("span");
        sets.className = "trainer-ex-sets";
        sets.textContent = formatSets(ex.sets);
        row.appendChild(sets);

        block.appendChild(row);
      }

      const actions = document.createElement("div");
      actions.className = "trainer-workout-actions";

      const logBtn = document.createElement("button");
      logBtn.className = "btn-primary btn-sm";
      logBtn.textContent = "Log This Today";
      logBtn.onclick = () => logWorkout(workout);
      actions.appendChild(logBtn);

      const tplBtn = document.createElement("button");
      tplBtn.className = "btn-secondary btn-sm";
      tplBtn.textContent = "Save as Template";
      tplBtn.onclick = () => saveAsTemplate(workout);
      actions.appendChild(tplBtn);

      block.appendChild(actions);
      return block;
    }

    function formatSets(sets) {
      if (!sets || sets.length === 0) return "";
      const grouped = {};
      for (const s of sets) {
        const key = s.percent
          ? `${s.reps}@${s.percent}%`
          : s.weight_lb
            ? `${s.reps}×${toDisplayWeight(s.weight_lb)}${unitLabel()}`
            : `${s.reps} reps`;
        grouped[key] = (grouped[key] || 0) + 1;
      }
      return Object.entries(grouped)
        .map(([k, n]) => `${n}×${k}`)
        .join("  ");
    }

    // ── Send message ──────────────────────────────────────────────────────────
    function handleTrainerKey(e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    }

    function sendSuggestion(btn) {
      document.getElementById("trainer-input").value = btn.textContent;
      sendMessage();
    }

    async function sendMessage() {
      const input   = document.getElementById("trainer-input");
      const sendBtn = document.getElementById("trainer-send-btn");
      const message = input.value.trim();
      if (!message) return;

      const allowWeb = document.getElementById("trainer-allow-web").checked;

      // Add user message to history and render
      history.push({ role: "user", content: message });
      renderHistory();
      input.value   = "";
      sendBtn.disabled = true;

      // Show typing indicator
      const conv = document.getElementById("conversation");
      const typing = document.createElement("div");
      typing.className = "trainer-bubble trainer-bubble--assistant trainer-typing";
      typing.innerHTML = '<div class="trainer-bubble-label">Trainer</div><div class="trainer-dots"><span></span><span></span><span></span></div>';
      conv.appendChild(typing);
      conv.scrollTop = conv.scrollHeight;

      try {
        // Build history for API — only role/content, strip workout data
        const apiHistory = history.slice(0, -1).map(m => ({
          role:    m.role,
          content: m.content,
        }));

        const res = await apiFetch("/api/ai/suggest", {
          method:  "POST",
          headers: { "Content-Type": "application/json" },
          body:    JSON.stringify({
            mode:      "chat",
            message,
            history:   apiHistory,
            allow_web: allowWeb,
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Request failed");

        const assistantContent = data.reply || data.reasoning || "";
        history.push({
          role:    "assistant",
          content: assistantContent,
          workout: data.workout || null,
        });
        saveSession();

      } catch (err) {
        history.push({ role: "assistant", content: `Error: ${err.message}` });
      } finally {
        typing.remove();
        sendBtn.disabled = false;
        renderHistory();
      }
    }

    // ── Log / Save actions ────────────────────────────────────────────────────
    async function logWorkout(workout) {
      // Navigate to /log with workout pre-filled via sessionStorage
      sessionStorage.setItem("aiWorkout", JSON.stringify(workout));
      window.location.href = "/log";
    }

    async function saveAsTemplate(workout) {
      const name = prompt("Template name:", workout.title || "AI Workout");
      if (!name) return;

      const exercises = (workout.exercises || []).map((ex, i) => ({
        exercise_id: ex.exercise_library_id,
        order_index: i,
        sets: (ex.sets || []).map((s, j) => ({
          set_number: j + 1,
          set_type:   s.set_type || "working",
          reps:       s.reps,
          percent:    s.percent,
          weight:     s.weight_lb,
        })),
      }));

      try {
        const res = await apiFetch("/api/templates/", {
          method:  "POST",
          headers: { "Content-Type": "application/json" },
          body:    JSON.stringify({ name, exercises }),
        });
        if (res.ok) {
          alert(`Template "${name}" saved!`);
        }
      } catch (err) {
        alert("Save failed: " + err.message);
      }
    }

    // ── Init ──────────────────────────────────────────────────────────────────
    initUnitToggle(() => renderHistory());
    loadSession();
  </script>
</body>
</html>
```

---

### Step 9 — Add /trainer route to views.py

In `backend/api/routes/views.py`, add a route for the trainer page:

```python
@views_bp.get("/trainer")
def trainer():
    return render_template("trainer.html")
```

---

### Step 10 — Add "Trainer" link to all navbars

All HTML templates with a navbar need a `<a href="/trainer">Trainer</a>` link.
Files to update: `dashboard.html`, `workouts.html`, `session.html`, `maxes.html`,
`templates.html`, `log.html`, `index.html`, `login.html`.

Pattern to add (after the Templates link):
```html
<a href="/trainer">Trainer</a>
```

---

### Step 11 — CSS additions for trainer page

Add to `frontend/static/css/main.css`:

```css
/* ── AI Trainer Card (log page) ─────────────────────────────────────────── */
.ai-trainer-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  margin-bottom: 1.5rem;
  overflow: hidden;
}
.ai-trainer-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  cursor: pointer;
  user-select: none;
}
.ai-trainer-icon { color: var(--accent); font-size: 1rem; }
.ai-trainer-title { font-weight: 700; font-size: 0.85rem; letter-spacing: 0.05em; flex: 1; }
.ai-trainer-toggle { font-size: 0.75rem; color: var(--text-muted); }
.ai-trainer-body {
  padding: 0 1rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.ai-trainer-tagline { font-size: 0.9rem; color: var(--text-muted); margin: 0; }
.ai-web-toggle { font-size: 0.85rem; color: var(--text-muted); display: flex; align-items: center; gap: 0.4rem; }
.ai-build-btn { align-self: flex-start; }
.ai-reasoning-box {
  background: var(--bg);
  border-left: 3px solid var(--accent);
  padding: 0.75rem 1rem;
  border-radius: 0 var(--radius) var(--radius) 0;
}
.ai-reasoning-label { font-size: 0.75rem; font-weight: 700; color: var(--text-muted); margin-bottom: 0.4rem; letter-spacing: 0.05em; }
.ai-reasoning-text { font-size: 0.9rem; line-height: 1.5; }

/* ── Trainer Chat Page ───────────────────────────────────────────────────── */
.trainer-page {
  max-width: 780px;
  margin: 0 auto;
  padding: 1.5rem 1rem;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 56px);
}
.trainer-header { margin-bottom: 1rem; }
.trainer-header h1 { font-size: 1.4rem; margin: 0 0 0.25rem; }
.trainer-header p { color: var(--text-muted); font-size: 0.9rem; margin: 0; }

.trainer-conversation {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding-bottom: 1rem;
}
.trainer-empty { text-align: center; padding: 2rem 1rem; color: var(--text-muted); }
.trainer-empty p { margin-bottom: 1rem; }
.trainer-suggestions { display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: center; }
.trainer-suggestions button {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 0.4rem 0.9rem;
  font-size: 0.85rem;
  cursor: pointer;
  color: var(--text);
}
.trainer-suggestions button:hover { border-color: var(--accent); }

.trainer-bubble { max-width: 90%; display: flex; flex-direction: column; gap: 0.3rem; }
.trainer-bubble--user { align-self: flex-end; }
.trainer-bubble--assistant { align-self: flex-start; }
.trainer-bubble-label { font-size: 0.75rem; font-weight: 700; color: var(--text-muted); letter-spacing: 0.05em; }
.trainer-bubble--user .trainer-bubble-label { text-align: right; }
.trainer-bubble-text {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0.75rem 1rem;
  font-size: 0.9rem;
  line-height: 1.5;
  white-space: pre-wrap;
}
.trainer-bubble--user .trainer-bubble-text { background: var(--accent); color: #fff; border-color: var(--accent); }

.trainer-workout-block {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0.75rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  min-width: 280px;
}
.trainer-workout-title { font-weight: 700; font-size: 0.95rem; margin-bottom: 0.25rem; }
.trainer-workout-exercise { display: flex; justify-content: space-between; font-size: 0.85rem; }
.trainer-ex-name { font-weight: 600; }
.trainer-ex-sets { color: var(--text-muted); }
.trainer-workout-actions { display: flex; gap: 0.5rem; margin-top: 0.5rem; }

.trainer-typing .trainer-dots { display: flex; gap: 4px; padding: 0.75rem 1rem; }
.trainer-dots span {
  width: 7px; height: 7px;
  background: var(--text-muted);
  border-radius: 50%;
  animation: dot-bounce 1.2s infinite;
}
.trainer-dots span:nth-child(2) { animation-delay: 0.2s; }
.trainer-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes dot-bounce {
  0%, 80%, 100% { transform: translateY(0); }
  40%           { transform: translateY(-6px); }
}

.trainer-input-area {
  border-top: 1px solid var(--border);
  padding-top: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.trainer-web-toggle { font-size: 0.85rem; color: var(--text-muted); }
.trainer-input-row { display: flex; gap: 0.5rem; }
.trainer-input-row textarea {
  flex: 1;
  resize: none;
  font-family: inherit;
  font-size: 0.9rem;
  padding: 0.6rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  color: var(--text);
  line-height: 1.4;
}
.trainer-input-row textarea:focus { outline: none; border-color: var(--accent); }
.trainer-send-btn { align-self: flex-end; white-space: nowrap; }
```

---

### ✅ Checkpoint 2 — End-to-End Test

1. Start the server.
2. Go to `/log` — confirm the "✦ AI TRAINER" card appears, click "Build My Workout",
   confirm exercises are pre-filled.
3. Go to `/trainer` — confirm chat UI loads, send a message, confirm structured
   workout response with "Log This Today" and "Save as Template" buttons.
4. Click "Log This Today" — confirm redirect to `/log` (sessionStorage handoff
   wires up in Step 12 below).
5. Check the `ai_knowledge` table after running any web-enabled request.

---

### Step 12 — Wire /log to accept pre-filled AI workout from sessionStorage

In `log.html`'s init block, add after the page loads:

```javascript
// Pick up a workout pre-filled by the trainer page
const aiWorkout = sessionStorage.getItem("aiWorkout");
if (aiWorkout) {
  sessionStorage.removeItem("aiWorkout");
  const workout = JSON.parse(aiWorkout);
  document.getElementById("workout-title").value = workout.title || "";
  clearExercises();
  for (const ex of workout.exercises || []) {
    addExerciseFromAI(ex);
  }
  // Show the trainer's reasoning card if available
  const aiCard = document.getElementById("ai-trainer-card");
  if (aiCard) aiCard.scrollIntoView({ behavior: "smooth" });
}
```

---

## Phase 2 — Web Search

Web search is already stubbed in `ai_trainer_service.py` via `_tavily_search()`.
To activate:

1. `pip install tavily-python`
2. Set `TAVILY_API_KEY` in environment.
3. The `_tavily_search()` function will detect the installed package and use it.
4. Verify `distill_and_store()` fires after searches and rows appear in `ai_knowledge`.

No other code changes required — the tool definition and tool-use loop are already
wired in `handle_request()`.

---

## Phase 3 — Polish

### Skeleton loader (log page)
Replace the "Building…" button text with a CSS shimmer overlay on the exercise
builder while the AI request is in-flight.

### Streaming (trainer page)
Replace the typing indicator with real streaming using the Anthropic streaming API:

```python
# In ai_trainer_service.py, use stream=True and yield chunks
with client.messages.stream(...) as stream:
    for text in stream.text_stream:
        yield text
```

On the frontend, use `fetch` + `ReadableStream` to append text as it arrives.

### sessionStorage conversation persistence
Already implemented — `saveSession()` / `loadSession()` in trainer.html persist
the conversation in `sessionStorage` across page refreshes (but not browser close).

---

## File Summary

| File | Action |
|------|--------|
| `backend/models/ai_knowledge.py` | **Create** |
| `backend/services/ai_trainer_service.py` | **Create** |
| `backend/api/routes/ai_trainer.py` | **Create** |
| `frontend/templates/trainer.html` | **Create** |
| `backend/app.py` | **Modify** — add model import, blueprint, scheduler |
| `backend/api/routes/views.py` | **Modify** — add /trainer route |
| `frontend/static/css/main.css` | **Modify** — add trainer styles |
| `frontend/templates/log.html` | **Modify** — add AI Trainer card + JS |
| All other templates | **Modify** — add "Trainer" nav link |

---

## Dependencies Summary

```
anthropic>=0.25.0       # Claude API
apscheduler>=3.10.0     # Weekly pattern detection job
tavily-python>=0.3.0    # Phase 2: web search tool
```

Environment variables:
```
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...   # Phase 2
```
