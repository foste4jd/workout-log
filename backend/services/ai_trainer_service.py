"""
AI Trainer service.

Provider-abstracted: swap OpenAIProvider for AnthropicProvider (or any other)
by changing _get_provider() without touching callers.

Context token budget: ~900–1800 tokens per call (compact summarization keeps costs low).
Model and limits controlled via backend/ai_config.py.
"""

import json
import logging
import os
import re
import time
from datetime import datetime, timezone, timedelta

from backend import ai_config

logger = logging.getLogger(__name__)

# Per-user daily request counter — (user_id, YYYY-MM-DD) → count.
# Resets automatically: old dates are never incremented so they stay harmless.
_daily_counts: dict = {}

from backend.db.database import db
from backend.models.workout import Workout
from backend.models.exercise import Exercise
from backend.models.exercise_set import ExerciseSet
from backend.models.training_max import TrainingMax
from backend.models.exercise_library import ExerciseLibrary
from backend.models.ai_knowledge import AIKnowledge


# ── Movement-pattern map (for recency tracking) ────────────────────────────────

_OVERHEAD = {
    "Overhead Press", "Arnold Press", "Seated Dumbbell Press",
    "Machine Shoulder Press", "Handstand Push-up", "Strict Handstand Push-up",
    "Thruster", "Dumbbell Thruster", "Push Jerk", "Split Jerk", "Jerk",
}
_ROWS = {
    "Bent Over Row", "T-Bar Row", "Seated Cable Row",
    "Single Arm Dumbbell Row", "Upright Row",
}
_CAT_TO_PATTERN = {
    "Squat":    "squat",
    "Hinge":    "hinge",
    "Press":    "horizontal_push",
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


def _exercise_pattern(lib_entry):
    if lib_entry is None:
        return None
    if lib_entry.name in _OVERHEAD:
        return "vertical_push"
    if lib_entry.name in _ROWS:
        return "horizontal_pull"
    return _CAT_TO_PATTERN.get(lib_entry.category)


# ── Provider abstraction (shared — see ai_provider.py) ────────────────────────

from backend.services.ai_provider import AIProvider, get_provider as _get_provider, truncate as _truncate  # noqa: E402


# ── Web search (Phase 2) ───────────────────────────────────────────────────────

# Single words that strongly suggest an educational/reference question.
_SEARCH_EDU_WORDS = frozenset({
    "evidence", "research", "study", "studies", "science", "scientific",
    "hypertrophy", "periodization", "adaptation", "mechanism", "mechanisms",
    "efficacy", "optimal", "optimize", "optimise",
    "accessory", "accessories",
    "recommend", "recommended", "recommendation",
    "deload", "deloading",
    "frequency", "volume", "intensity",
    "causes", "cause", "causation",
    "elbow", "shoulder", "wrist", "knee",
    "irritation", "inflammation", "tendinitis", "tendonitis",
    "nutrition", "protein", "creatine", "supplementation",
    "fatigue", "overtraining", "recovery",
    "range", "ranges",  # "rep range" (only fires with a question word present)
})

# Words that confirm a question orientation.
_QUESTION_WORDS = frozenset({
    "what", "why", "how", "is", "does", "do", "should", "which",
    "can", "are", "would", "explain", "difference", "best",
})

# Substrings that flag explicit workout-generation requests — hard block on search.
_GENERATION_SIGNALS = (
    "generate", "create", "build", "make me", "give me", "plan for",
    "leg day", "upper body", "lower body", "push day", "pull day",
    "arm day", "chest day", "back day", "shoulder day", "full body",
    "today's workout", "workout for today",
)

# Substrings that flag personal/history questions — app data covers these, not search.
_PERSONAL_SIGNALS = (
    "my squat", "my bench", "my deadlift", "my progress", "my training",
    "how am i", "how have i", "how's my", "how is my",
    "this week", "last week", "am i progressing",
)


def _classify_needs_search(prompt: str) -> bool:
    """
    Fast heuristic: returns True when the prompt is a general educational
    training/lifting question that could benefit from external references.

    Never returns True for workout-generation or personal-history queries —
    those are fully served by app data.
    """
    if not prompt or len(prompt.strip()) < 8:
        return False

    lower = prompt.lower()
    words = set(re.findall(r"\w+", lower))

    if any(sig in lower for sig in _GENERATION_SIGNALS):
        return False
    if any(sig in lower for sig in _PERSONAL_SIGNALS):
        return False
    if not (words & _QUESTION_WORDS):
        return False
    return bool(words & _SEARCH_EDU_WORDS)


def search_web(query: str) -> list:
    """
    Execute a Tavily search. Returns compact [{title, url, content}] dicts.
    Returns [] if TAVILY_API_KEY is absent or the search fails.
    Failure is always silent — callers should treat [] as "no results".
    """
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return []

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        resp    = client.search(
            query,
            max_results=ai_config.MAX_SEARCH_RESULTS,
            search_depth="basic",
        )
        results = resp.get("results") or []
        return [
            {
                "title":   (r.get("title") or "")[:100],
                "url":     r.get("url") or "",
                "content": (r.get("content") or "")[:ai_config.MAX_SEARCH_CHARS],
            }
            for r in results[:ai_config.MAX_SEARCH_RESULTS]
        ]
    except Exception:
        logger.warning("ai_trainer | Tavily search failed for query=%r", query[:80])
        return []


_DISTILL_SYSTEM_PROMPT = (
    "You are a concise research summarizer for a strength training coaching app. "
    "Given web search results about a training question, return compact JSON:\n"
    '{"summary": "2-3 sentence distilled insight. Evidence-based and actionable. No filler.", '
    '"sources": [{"title": "...", "url": "..."}]}\n'
    "Maximum 2 sources. If results are low-quality or irrelevant to strength training, "
    'return {"summary": "", "sources": []}.'
)


def _distill_search_results(results: list, query: str, provider: AIProvider) -> tuple:
    """
    Use complete_mini() to distill raw search results into a compact summary.
    Returns (summary_str, sources_list). Both are empty on failure or irrelevance.
    """
    if not results:
        return "", []

    results_text = "\n\n".join(
        f"[{r['title']}]\n{r['content']}"
        for r in results
    )
    messages = [
        {"role": "system", "content": _DISTILL_SYSTEM_PROMPT},
        {"role": "user",   "content": f"QUESTION: {query}\n\nSEARCH RESULTS:\n{results_text}"},
    ]
    try:
        raw  = provider.complete_mini(messages)
        data = json.loads(raw)
        summary = _truncate(data.get("summary") or "", ai_config.SEARCH_DISTILL_CHARS)
        sources = (data.get("sources") or [])[:2]
        return summary, sources
    except Exception:
        return "", []


def _store_web_knowledge(user_id: int, query: str, distilled: str, sources: list) -> None:
    """
    Persist distilled search knowledge as a web_reference memory entry.
    Skips trivially short text and near-duplicates of existing web_reference entries.
    """
    if not distilled or len(distilled.strip()) < 40:
        return

    existing = AIKnowledge.query.filter_by(
        user_id=user_id, source_type="web_reference", is_active=True
    ).all()
    if any(_text_similarity(distilled.lower(), e.text.lower()) > 0.6 for e in existing):
        return

    now  = _now()
    meta = json.dumps({
        "query":       query[:120],
        "sources":     sources[:2],
        "searched_at": now.isoformat(),
    })
    db.session.add(AIKnowledge(
        user_id     = user_id,
        type        = "memory",
        category    = "other",
        text        = _truncate(distilled, ai_config.MAX_NOTE_CHARS),
        priority    = "low",
        source_type = "web_reference",
        is_active   = True,
        created_at  = now,
        updated_at  = now,
        meta        = meta,
    ))
    db.session.commit()


def check_and_record_daily_request(user_id: int) -> bool:
    """
    Increment the per-user daily counter. Returns True if allowed, False if
    the daily limit has been reached. Keyed by (user_id, UTC date string) so
    it resets automatically at the user's local midnight.
    """
    date_str = _user_local_now(user_id).strftime("%Y-%m-%d")
    key = (user_id, date_str)
    count = _daily_counts.get(key, 0)
    if count >= ai_config.MAX_DAILY_REQUESTS:
        return False
    _daily_counts[key] = count + 1
    return True


def _aggregate_older_workouts(workouts: list) -> list:
    """
    Collapse a list of workouts into compact per-week summaries.
    Returns one entry per week (ISO week) with exercise name frequency.
    Used for the 'older history' portion of the prompt to save tokens.
    """
    from collections import defaultdict
    weeks: dict = defaultdict(lambda: {"exercises": defaultdict(int), "count": 0})
    for w in workouts:
        week_key = w["date"][:7] if isinstance(w, dict) else w.date.strftime("%Y-%m")
        entry = weeks[week_key]
        entry["count"] += 1
        exs = w.get("exercises", []) if isinstance(w, dict) else [ex.name for ex in w.exercises]
        for ex in exs:
            ex_name = ex if isinstance(ex, str) else (ex.get("name") or "")
            # Strip the rep/weight suffix if present (format: "Name: 3×5 @225lb")
            ex_name = ex_name.split(":")[0].strip() if ":" in ex_name else ex_name
            if ex_name:
                entry["exercises"][ex_name] += 1

    result = []
    for week, data in sorted(weeks.items(), reverse=True):
        top_exs = sorted(data["exercises"].items(), key=lambda x: -x[1])[:6]
        ex_str = ", ".join(f"{name}×{cnt}" for name, cnt in top_exs)
        result.append(f"  {week}: {data['count']} sessions — {ex_str}")
    return result


# ── System prompt ──────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a strength training analysis and programming tool. \
You receive athlete data and return structured JSON — no prose, no markdown.

OUTPUT SCHEMA (always return valid JSON in this exact shape):
{
  "mode": "workout" | "answer",
  "workout_name": "string or null",
  "workout_goal": "string or null",
  "summary": "2-4 sentence analytical explanation",
  "ai_noticed": ["up to 3 short bullet strings, or empty array"],
  "memory_candidates": [
    {"category": "schedule|recovery|injury|preferences|performance_pattern|other",
     "text": "string", "priority": "low|medium|high"}
  ],
  "training_max_recommendations": [
    {"exercise_name": "string", "current_tm": number_or_null,
     "recommended_tm": number_or_null, "reason": "string"}
  ],
  "workout": {
    "name": "string",
    "exercises": [
      {
        "exercise_name": "string — match exercise library names exactly when possible",
        "notes": "string or null",
        "blocks": [
          {"set_type": "warmup|working|amrap|emom|failure",
           "sets": integer,
           "reps": "string or integer or null",
           "weight": number_or_null,
           "percent": number_or_null,
           "duration_seconds": number_or_null,
           "notes": "string or null"}
        ]
      }
    ]
  },
  "answer": {"title": "string", "content": "string",
             "suggested_action": "adjust_today_workout|generate_workout|none"}
}

RULES:
- If prompt requests a workout → mode=workout, populate workout object, set answer=null
- If prompt is a training question → mode=answer, populate answer object, set workout=null
- Never prescribe % sets without a known training max. Use absolute weights or reps-only instead.
- If training max exists: use it for main lifts. Accessories use reps/sets, not strict %.
- Never jump more than 5% above the athlete's recent working % on main lifts.
- If the recency map shows <24h since a pattern was trained, avoid that pattern unless explicitly requested.
- If the athlete missed reps in the last session, do NOT increase the % on that lift.
- If 5+ sessions this week: recommend deload or recovery day.
- Pain/injury context: suggest reduced volume, substitutes, or rest. No diagnosis language.
- Training max recommendations: allowed, but NEVER auto-apply. Always flag as recommendation only.
- memory_candidates: extract only durable, non-trivial facts worth remembering across sessions.
  Skip single-session observations. Focus on schedule, injuries, preferences, recurring patterns.
- summary: analytical, 2-4 sentences. No filler. No "Great job!" style language.
- ai_noticed: max 3 items. Only include if genuinely useful. Empty array is fine."""


# ── Context builder ────────────────────────────────────────────────────────────

def _now():
    """Naive UTC now — used for timestamps only."""
    return datetime.utcnow()


def _user_local_now(user_id: int):
    """Return naive datetime in the user's local timezone for date-boundary logic."""
    from zoneinfo import ZoneInfo
    from backend.models.user import User
    user = User.query.get(user_id)
    tz = ZoneInfo(user.timezone or "UTC") if user else ZoneInfo("UTC")
    return datetime.now(tz).replace(tzinfo=None)


def build_context(user_id: int, days: int = 21) -> dict:
    total_limit = ai_config.MAX_RECENT_WORKOUTS + ai_config.MAX_OLDER_WORKOUTS
    now = _user_local_now(user_id)
    since = now - timedelta(days=days)

    workouts = (
        Workout.query
        .filter(Workout.user_id == user_id, Workout.date >= since)
        .order_by(Workout.date.desc())
        .limit(total_limit)
        .all()
    )

    tms = TrainingMax.query.filter_by(user_id=user_id).all()
    training_maxes = {
        tm.exercise.name: tm.training_max_weight
        for tm in tms if tm.exercise
    }

    recency  = _build_recency_map(workouts, now)
    trends   = _build_trends(workouts)
    memories = get_relevant_memories(user_id, limit=ai_config.MAX_MEMORIES)
    week_count = sum(1 for w in workouts if (now - w.date).days < 7)

    from backend.services.profile_service import get_profile_context
    athlete_profile = get_profile_context(user_id)

    recent = workouts[:ai_config.MAX_RECENT_WORKOUTS]
    older  = workouts[ai_config.MAX_RECENT_WORKOUTS:]

    return {
        "today":            now.strftime("%Y-%m-%d (%A)"),
        "athlete_profile":  athlete_profile,
        "training_maxes":   training_maxes,
        "recency":          recency,
        "trends":           trends,
        "week_count":       week_count,
        "recent_workouts": _summarize_workouts(recent),
        "older_workouts":  _aggregate_older_workouts(older),
        "memories":        memories,
    }


def _build_recency_map(workouts: list, now=None) -> dict:
    today = (now or _now()).date()
    last_trained: dict = {}

    for w in workouts:
        w_date = w.date.date() if hasattr(w.date, "date") else w.date
        for ex in w.exercises:
            lib = None
            if ex.exercise_library_id:
                lib = ExerciseLibrary.query.get(ex.exercise_library_id)
            pattern = _exercise_pattern(lib)
            if pattern:
                if pattern not in last_trained or w_date > last_trained[pattern]:
                    last_trained[pattern] = w_date

    patterns = [
        "squat", "hinge", "horizontal_push", "vertical_push",
        "horizontal_pull", "vertical_pull", "arms", "carry", "core",
    ]
    return {
        p: (today - last_trained[p]).days if p in last_trained else None
        for p in patterns
    }


def _build_trends(workouts: list) -> dict:
    # Key by library ID when available so renamed exercises still accumulate correctly.
    # display_name tracks the canonical label to show in context output.
    sessions_by_key: dict = {}
    display_name: dict    = {}

    for w in workouts:
        for ex in w.exercises:
            if not ex.name:
                continue
            key = f"lib:{ex.exercise_library_id}" if ex.exercise_library_id else f"name:{ex.name.lower()}"
            if key not in sessions_by_key:
                sessions_by_key[key] = []
                display_name[key]    = ex.name
            if len(sessions_by_key[key]) >= 4:
                continue
            sets_data = [
                {
                    "reps":      s.reps,
                    "weight_lb": s.weight_lb,
                    "percent":   s.percent,
                    "completed": s.completed,
                }
                for s in ex.set_records
            ]
            sessions_by_key[key].append({"date": w.date.strftime("%Y-%m-%d"), "sets": sets_data})

    sessions_by_ex = {display_name[k]: v for k, v in sessions_by_key.items()}

    trends = {}
    for name, sessions in sessions_by_ex.items():
        if not sessions:
            continue
        latest = sessions[0]
        missed_last = any(not s.get("completed", True) for s in latest["sets"])

        def avg_w(sess):
            ws = [s["weight_lb"] for s in sess["sets"] if s.get("weight_lb")]
            return sum(ws) / len(ws) if ws else 0

        if len(sessions) >= 2:
            delta = avg_w(sessions[0]) - avg_w(sessions[-1])
            trend = "progressing" if delta > 2 else ("declining" if delta < -2 else "stalled")
        else:
            trend = "insufficient_data"

        trends[name] = {
            "trend":       trend,
            "missed_last": missed_last,
            "sessions":    sessions[:4],
        }
    return trends


def _summarize_workouts(workouts: list) -> list:
    """Compact representation — keeps token count manageable."""
    result = []
    for w in workouts:
        exs = []
        for ex in w.exercises:
            sets = ex.set_records
            if not sets:
                continue
            working = [s for s in sets if s.set_type == "working"]
            rep_str = f"{len(working)} sets"
            if working:
                # e.g. "3×5 @ 225lb (80%)"
                avg_w  = sum(s.weight_lb or 0 for s in working) / len(working)
                avg_p  = sum(s.percent or 0 for s in working) / len(working)
                reps   = working[0].reps or "?"
                missed = sum(1 for s in sets if not s.completed)
                rep_str = f"{len(working)}×{reps}"
                if avg_w:
                    rep_str += f" @{round(avg_w)}lb"
                if avg_p:
                    rep_str += f" ({round(avg_p)}%)"
                if missed:
                    rep_str += f" [{missed} miss]"
            exs.append(f"{ex.name}: {rep_str}")
        if exs:
            result.append({
                "date":      w.date.strftime("%Y-%m-%d"),
                "title":     w.title,
                "duration":  w.duration_minutes,
                "exercises": exs,
            })
    return result


# ── Memory management ──────────────────────────────────────────────────────────

def get_relevant_memories(user_id: int, limit: int = 12) -> list:
    """Return active memories for this user, prioritised by priority + recency."""
    priority_order = {"high": 0, "medium": 1, "low": 2}
    entries = (
        AIKnowledge.query
        .filter_by(user_id=user_id, is_active=True)
        .order_by(AIKnowledge.updated_at.desc())
        .all()
    )
    entries.sort(key=lambda e: (priority_order.get(e.priority, 1), -(e.updated_at.timestamp() if e.updated_at else 0)))
    selected = entries[:limit]

    now = _now()
    for e in selected:
        e.last_used_at = now
    db.session.commit()

    return [{"category": e.category, "text": e.text, "priority": e.priority} for e in selected]


def store_memories(user_id: int, candidates: list) -> None:
    """Persist memory candidates returned by the AI. Deduplicates on text similarity."""
    if not candidates:
        return
    existing_texts = [
        e.text.lower() for e in
        AIKnowledge.query.filter_by(user_id=user_id, is_active=True).all()
    ]
    now = _now()
    for c in candidates:
        text = (c.get("text") or "").strip()
        if not text:
            continue
        # Simple dedup: skip if very similar text already exists
        if any(_text_similarity(text.lower(), ex) > 0.75 for ex in existing_texts):
            continue
        db.session.add(AIKnowledge(
            user_id    = user_id,
            type       = "memory",
            category   = c.get("category", "other"),
            text       = text,
            priority   = c.get("priority", "medium"),
            source_type= "user_prompt",
            is_active  = True,
            created_at = now,
            updated_at = now,
        ))
    db.session.commit()


def _text_similarity(a: str, b: str) -> float:
    """Rough word-overlap similarity to avoid storing near-duplicate memories."""
    wa, wb = set(re.findall(r"\w+", a)), set(re.findall(r"\w+", b))
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def detect_patterns_on_save(user_id: int, workout_id: int) -> None:
    """
    Lightweight pattern detection called when a workout is completed.
    Adds to ai_knowledge only for high-confidence, durable signals.
    Runs synchronously but is fast (no AI call — pure DB analysis).
    """
    try:
        now = _user_local_now(user_id)
        since = now - timedelta(days=30)
        workouts = (
            Workout.query
            .filter(Workout.user_id == user_id, Workout.date >= since)
            .order_by(Workout.date.desc())
            .limit(20)
            .all()
        )
        if len(workouts) < 4:
            return  # Not enough history

        # Pattern: consistently high training frequency
        week_count = sum(1 for w in workouts if (now - w.date).days < 7)
        if week_count >= 6:
            _maybe_store_pattern(
                user_id,
                "performance_pattern",
                f"Training {week_count} days per week in recent weeks — monitor recovery.",
                "detected_pattern",
                "medium",
            )

        # Pattern: repeated missed reps on a specific exercise (3+ recent sessions)
        miss_counts: dict = {}
        for w in workouts[:8]:
            for ex in w.exercises:
                missed = sum(1 for s in ex.set_records if not s.completed)
                if missed:
                    miss_counts[ex.name] = miss_counts.get(ex.name, 0) + 1
        for ex_name, count in miss_counts.items():
            if count >= 3:
                _maybe_store_pattern(
                    user_id,
                    "performance_pattern",
                    f"Frequently missing reps on {ex_name} — may need volume or intensity adjustment.",
                    "detected_pattern",
                    "medium",
                )
    except Exception:
        pass  # Pattern detection is best-effort — never block the save flow


def _maybe_store_pattern(user_id, category, text, source_type, priority):
    existing = AIKnowledge.query.filter_by(
        user_id=user_id, is_active=True, category=category
    ).all()
    if any(_text_similarity(text.lower(), e.text.lower()) > 0.6 for e in existing):
        return
    now = _now()
    db.session.add(AIKnowledge(
        user_id    = user_id,
        type       = "memory",
        category   = category,
        text       = text,
        priority   = priority,
        source_type= source_type,
        is_active  = True,
        created_at = now,
        updated_at = now,
    ))
    db.session.commit()


# ── Main AI handler ────────────────────────────────────────────────────────────

def handle_suggest(user_id: int, prompt: str, allow_web: bool = False) -> dict:
    """
    Build context, optionally enrich with web search, call AI, validate, store memories.
    Returns the parsed response dict.

    Web search is secondary and tightly controlled:
    - Only fires when ALLOW_WEB_SEARCH=True (env-var opt-in)
    - Only fires when _classify_needs_search() identifies an educational question
    - Never fires for workout generation
    - Results are distilled to a compact summary before injection
    """
    # ── Rate limit check ───────────────────────────────────────────────────────
    if not check_and_record_daily_request(user_id):
        return {
            "mode": "answer",
            "summary": f"Daily limit of {ai_config.MAX_DAILY_REQUESTS} AI requests reached. Resets at midnight UTC.",
            "ai_noticed": [],
            "memory_candidates": [],
            "training_max_recommendations": [],
            "workout": None,
            "answer": {
                "title": "Daily limit reached",
                "content": f"You've used all {ai_config.MAX_DAILY_REQUESTS} AI requests for today. Try again tomorrow.",
                "suggested_action": "none",
            },
        }

    # ── Truncate prompt ────────────────────────────────────────────────────────
    prompt = _truncate((prompt or "").strip(), ai_config.MAX_PROMPT_CHARS)

    provider = _get_provider()
    context  = build_context(user_id)

    # ── Web search (Phase 2) — only for educational questions ─────────────────
    search_context  = ""
    search_sources: list = []
    web_used        = False
    search_query    = None

    if ai_config.ALLOW_WEB_SEARCH and _classify_needs_search(prompt):
        try:
            raw_results = search_web(prompt)
        except Exception:
            raw_results = []
        if raw_results:
            search_context, search_sources = _distill_search_results(
                raw_results, prompt, provider
            )
            web_used     = bool(search_context)
            search_query = prompt if web_used else None

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user",   "content": _build_user_message(context, prompt, search_context)},
    ]

    t0  = time.monotonic()
    raw = None
    try:
        raw    = provider.complete(messages, temperature=0.3)
        result = json.loads(raw)
    except json.JSONDecodeError:
        latency = round(time.monotonic() - t0, 2)
        usage   = getattr(provider, "last_usage", {})
        logger.error(
            "ai_trainer | user=%s model=%s latency=%.2fs in=%s out=%s "
            "web_search=%s error=json_decode raw_snippet=%s",
            user_id, ai_config.AI_MODEL, latency,
            usage.get("input_tokens", "?"), usage.get("output_tokens", "?"),
            web_used, repr((raw or "")[:120]),
        )
        return _error_response("AI returned malformed JSON. Please try rephrasing your request.")
    except Exception as e:
        latency = round(time.monotonic() - t0, 2)
        usage   = getattr(provider, "last_usage", {})
        logger.error(
            "ai_trainer | user=%s model=%s latency=%.2fs in=%s out=%s "
            "web_search=%s error=%s",
            user_id, ai_config.AI_MODEL, latency,
            usage.get("input_tokens", "?"), usage.get("output_tokens", "?"),
            web_used, str(e),
        )
        return _error_response(f"AI generation failed — check OPENAI_API_KEY and server logs. ({e})")

    latency = round(time.monotonic() - t0, 2)
    usage   = getattr(provider, "last_usage", {})
    mode    = result.get("mode", "unknown")

    # ── Telemetry log ─────────────────────────────────────────────────────────
    logger.info(
        "ai_trainer | user=%s model=%s mode=%s latency=%.2fs in=%s out=%s "
        "web_search=%s search_query=%s",
        user_id, ai_config.AI_MODEL, mode, latency,
        usage.get("input_tokens", "?"), usage.get("output_tokens", "?"),
        web_used, repr(search_query[:60]) if search_query else None,
    )

    # ── Validate "mode" present — reject malformed response without retry ─────
    if "mode" not in result:
        return _error_response("AI response missing required 'mode' field.")

    # ── Store any durable memories the AI extracted from the prompt/context ───
    candidates = result.get("memory_candidates") or []
    if candidates:
        store_memories(user_id, candidates)

    # ── Store distilled web knowledge for future reuse ─────────────────────────
    if web_used and search_context and mode == "answer":
        _store_web_knowledge(user_id, prompt, search_context, search_sources)

    return result


def _error_response(message: str) -> dict:
    return {
        "mode": "answer",
        "summary": message,
        "ai_noticed": [],
        "memory_candidates": [],
        "training_max_recommendations": [],
        "workout": None,
        "answer": {
            "title": "Error",
            "content": message,
            "suggested_action": "none",
        },
    }


def _build_user_message(context: dict, prompt: str, search_context: str = "") -> str:
    lines = [
        f"TODAY: {context['today']}",
        f"SESSIONS THIS WEEK: {context['week_count']}",
        "",
        "TRAINING MAXES:",
    ]
    if context["training_maxes"]:
        for name, w in context["training_maxes"].items():
            lines.append(f"  {name}: {w} lb")
    else:
        lines.append("  (none set)")

    lines += ["", "MUSCLE GROUP RECENCY (days since last trained, null=not in window):"]
    for pat, days in context["recency"].items():
        days_str = f"{days}d" if days is not None else "null"
        lines.append(f"  {pat}: {days_str}")

    if context["memories"]:
        lines += ["", "STORED MEMORIES:"]
        for m in context["memories"]:
            lines.append(f"  [{m['category']}] {_truncate(m['text'], ai_config.MAX_NOTE_CHARS)}")

    if context["trends"]:
        lines += ["", "PERFORMANCE TRENDS (last 4 sessions per lift):"]
        for ex_name, t in list(context["trends"].items())[:10]:
            missed = " ⚠ missed reps last session" if t["missed_last"] else ""
            lines.append(f"  {ex_name}: {t['trend']}{missed}")
            for sess in t["sessions"][:2]:
                set_strs = [
                    f"{s['reps']}r @{s['weight_lb']}lb"
                    for s in sess["sets"][:3]
                    if s.get("weight_lb") and s.get("reps") is not None
                ]
                lines.append(f"    {sess['date']}: {'; '.join(set_strs)}")

    if context.get("recent_workouts"):
        lines += ["", f"RECENT WORKOUTS (last {ai_config.MAX_RECENT_WORKOUTS}, full detail):"]
        for w in context["recent_workouts"]:
            title = _truncate(w["title"], ai_config.MAX_NOTE_CHARS)
            lines.append(f"  {w['date']} — {title}" + (f" ({w['duration']}min)" if w["duration"] else ""))
            for ex_line in w["exercises"]:
                lines.append(f"    {ex_line}")

    if context.get("older_workouts"):
        lines += ["", "OLDER HISTORY (weekly summaries):"]
        lines.extend(context["older_workouts"])

    if search_context:
        lines += [
            "",
            "WEB REFERENCE (external sources, distilled — supplementary only):",
            search_context,
            "Note: Use athlete history, training maxes, and memory first. "
            "Treat this as supporting context, not primary programming input.",
        ]

    prompt_text = _truncate(prompt, ai_config.MAX_PROMPT_CHARS) if prompt and prompt.strip() \
        else "(no prompt — use history and memory to decide the best workout for today)"
    lines += ["", f"ATHLETE REQUEST: {prompt_text}"]

    return "\n".join(lines)


# ── Accept / save AI workout to DB ─────────────────────────────────────────────

def accept_workout(user_id: int, ai_result: dict, date_str: str = None) -> dict:
    """
    Convert an AI-generated workout dict into real workout/exercise/set DB records.
    Returns the new workout's to_dict().
    """
    from backend.services import workout_service, exercise_service

    workout_data = ai_result.get("workout") or {}
    name = workout_data.get("name") or ai_result.get("workout_name") or "AI Workout"
    date = date_str or _now().strftime("%Y-%m-%dT12:00:00")

    workout = workout_service.create_workout(user_id, {
        "title": name,
        "date":  date,
        "notes": ai_result.get("summary"),
    })

    # Load library for name matching
    library = ExerciseLibrary.query.filter_by(is_active=True).all()
    lib_by_name = {e.name.lower(): e for e in library}

    exercises_data = workout_data.get("exercises") or []
    try:
        for order, ex_ai in enumerate(exercises_data):
            ex_name = (ex_ai.get("exercise_name") or "").strip()
            if not ex_name:
                continue

            # Case-insensitive library lookup with word-level partial fallback
            lib_entry = lib_by_name.get(ex_name.lower())
            if not lib_entry:
                ex_words = set(re.findall(r"\w+", ex_name.lower()))
                for lib_name, entry in lib_by_name.items():
                    lib_words = set(re.findall(r"\w+", lib_name))
                    shorter = ex_words if len(ex_words) <= len(lib_words) else lib_words
                    longer  = lib_words if len(ex_words) <= len(lib_words) else ex_words
                    if len(shorter) >= 2 and shorter.issubset(longer):
                        lib_entry = entry
                        break

            sets_payload = _blocks_to_sets(ex_ai.get("blocks") or [], lib_entry, user_id)
            if not sets_payload:
                continue

            exercise_service.create_exercise(workout.id, {
                "name":                ex_name if not lib_entry else lib_entry.name,
                "exercise_library_id": lib_entry.id if lib_entry else None,
                "notes":               ex_ai.get("notes"),
                "sets":                sets_payload,
            })
    except Exception:
        # Best-effort cleanup: remove the partially-created workout on failure
        try:
            db.session.rollback()
            db.session.delete(workout)
            db.session.commit()
        except Exception:
            pass
        raise

    return workout.to_dict()


def _blocks_to_sets(blocks: list, lib_entry, user_id: int) -> list:
    """Expand AI set blocks into individual set records."""
    sets = []
    set_num = 1
    tm = None
    if lib_entry:
        tm_row = TrainingMax.query.filter_by(
            user_id=user_id, exercise_id=lib_entry.id
        ).first()
        tm = tm_row.training_max_weight if tm_row else None

    for block in blocks:
        count = max(1, int(float(block.get("sets") or 1)))
        for _ in range(count):
            weight_lb = block.get("weight")
            percent   = block.get("percent")
            reps_raw  = block.get("reps")
            reps      = int(reps_raw) if reps_raw and str(reps_raw).isdigit() else None

            # Resolve percent → weight_lb if TM known
            if percent and tm and not weight_lb:
                weight_lb = round(tm * percent / 100 / 2.5) * 2.5

            sets.append({
                "set_number":       set_num,
                "set_type":         block.get("set_type", "working"),
                "reps":             reps,
                "weight_lb":        weight_lb,
                "percent":          percent,
                "duration_seconds": block.get("duration_seconds"),
            })
            set_num += 1
    return sets


def save_as_template(user_id: int, ai_result: dict) -> dict:
    """Save an AI-generated workout directly as a template (bypassing workout record)."""
    from backend.services import template_service

    workout_data = ai_result.get("workout") or {}
    name = workout_data.get("name") or ai_result.get("workout_name") or "AI Template"
    library = ExerciseLibrary.query.filter_by(is_active=True).all()
    lib_by_name = {e.name.lower(): e for e in library}

    exercises_payload = []
    for order, ex_ai in enumerate(workout_data.get("exercises") or []):
        ex_name  = (ex_ai.get("exercise_name") or "").strip()
        lib_entry = lib_by_name.get(ex_name.lower())
        if not lib_entry:
            continue  # Templates require library exercises
        sets = []
        sn = 1
        for block in (ex_ai.get("blocks") or []):
            count = max(1, int(block.get("sets") or 1))
            for _ in range(count):
                sets.append({
                    "set_number":       sn,
                    "set_type":         block.get("set_type", "working"),
                    "reps":             block.get("reps"),
                    "weight":           block.get("weight"),
                    "percent":          block.get("percent"),
                    "duration_seconds": block.get("duration_seconds"),
                })
                sn += 1
        exercises_payload.append({
            "exercise_id": lib_entry.id,
            "order_index": order,
            "notes":       ex_ai.get("notes"),
            "sets":        sets,
        })

    template = template_service.create_template(user_id, {
        "name":        name,
        "description": ai_result.get("summary", ""),
        "exercises":   exercises_payload,
    })


# ── Title generation ───────────────────────────────────────────────────────────

def generate_title(exercise_names: list, weekday: str) -> str:
    """Generate a short workout title from exercise names and weekday."""
    if not exercise_names:
        return ""
    names = ", ".join(str(n)[:40] for n in exercise_names[:6])
    provider = _get_provider()
    messages = [
        {
            "role": "system",
            "content": (
                "You name workouts. "
                "Respond ONLY with valid JSON: {\"title\": \"...\"}. "
                "Title is 2-4 words, punchy, no punctuation."
            ),
        },
        {
            "role": "user",
            "content": f"Exercises: {names}. Day: {weekday}. Generate a workout title.",
        },
    ]
    try:
        raw = provider.complete_mini(messages)
        data = json.loads(raw)
        title = data.get("title", "").strip()
        # Fallback: strip JSON wrapper if model returned raw text
        if not title:
            import re as _re
            m = _re.search(r'"title"\s*:\s*"([^"]+)"', raw)
            if m:
                title = m.group(1).strip()
        return title[:60]
    except Exception:
        return ""
    return template.to_dict(include_exercises=True)
