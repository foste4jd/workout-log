# AI Trainer — Persistent Memory & Learning

## The Core Problem

Raw web search results are huge (10–50KB per page). Storing them directly would
bloat the database fast and make every AI call slower as the context grows.

The solution: **never store raw content — only store distilled insight.**

A full web article on bench press programming might be 40KB.
The distilled insight from it is 150 bytes:

> "Bench press stalls respond better to technique resets (pause bench, close-grip)
>  than simply dropping volume. Source: renaissance-periodization.com"

That's a 99.6% storage reduction with 95% of the useful signal retained.

---

## Two Types of Memory

```
┌─────────────────────────────────────────────────────────────┐
│                    ai_knowledge table                       │
│                                                             │
│  TYPE 1: External Knowledge                                 │
│  ─────────────────────────                                  │
│  Distilled from web searches.                               │
│  Programming schemes, exercise science, periodization,      │
│  injury management, technique cues.                         │
│                                                             │
│  TYPE 2: User Patterns                                      │
│  ─────────────────────                                      │
│  Observed from YOUR workout history over time.              │
│  Things the AI notices that aren't in any textbook —        │
│  specific to how your body responds to training.            │
└─────────────────────────────────────────────────────────────┘
```

### Type 1 Examples — External Knowledge
| Tags | Distilled Insight |
|------|-------------------|
| `bench, stall, plateau` | Bench stalls respond better to technique resets (pause bench, close-grip) than volume drops |
| `squat, out_of_hole, weakness` | Box squats and pause squats at 50-60% build strength out of the hole better than just adding weight |
| `deadlift, lower_back, fatigue` | Snatch-grip and Romanian DL variations allow frequency without CNS fatigue of heavy conventional pulls |
| `deload, frequency` | Effective deloads cut volume by 40-60% while keeping intensity above 70% — full rest weeks are rarely optimal |
| `5_3_1, programming` | 5/3/1 progression: TM increases 5lb upper / 10lb lower per cycle; AMRAP sets drive adaptation |

### Type 2 Examples — User Patterns
| Tags | Observed Pattern |
|------|-----------------|
| `user, bench, fatigue` | User misses bench reps when less than 48hrs from previous squat session |
| `user, squat, recovery` | User's squat performance drops noticeably after 4+ consecutive training days |
| `user, deadlift, progress` | User's deadlift has increased consistently at ~5lb/week — TM may be lagging reality |
| `user, volume, response` | User performs well on high-rep back-off sets (10+ reps) — responds to volume not just intensity |

---

## Database Schema

One table. Small rows. Fast queries.

```sql
CREATE TABLE ai_knowledge (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER REFERENCES users(id),   -- NULL = global knowledge, set = user-specific
    type        TEXT NOT NULL,                  -- 'external' | 'user_pattern'
    category    TEXT NOT NULL,                  -- 'programming' | 'exercise_science' |
                                                --  'periodization' | 'recovery' | 'technique' |
                                                --  'user_pattern'
    tags        TEXT NOT NULL,                  -- JSON array: ["bench", "stall", "plateau"]
    summary     TEXT NOT NULL,                  -- The distilled insight, max 300 chars
    source      TEXT,                           -- URL for external, NULL for user patterns
    confidence  REAL DEFAULT 1.0,               -- 0.0–1.0; degrades if contradicted
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_used_at DATETIME,
    use_count   INTEGER DEFAULT 0
);

CREATE INDEX idx_knowledge_tags     ON ai_knowledge(tags);
CREATE INDEX idx_knowledge_user     ON ai_knowledge(user_id);
CREATE INDEX idx_knowledge_category ON ai_knowledge(category);
```

**Storage estimate:**
- Average row: ~400 bytes
- 1,000 entries: ~400KB — essentially nothing
- At aggressive usage (2 web searches/day for a year): ~300 entries/year → ~120KB/year

---

## How Memory Gets Written

### After Every Web Search

When the AI uses the web search tool, a second Claude call immediately follows to
distill the raw result into a knowledge entry:

```python
def distill_and_store(search_query, raw_results, user_id):
    """Called automatically after every web search tool use."""

    distillation_prompt = f"""
    Web search query: "{search_query}"
    Raw results: {raw_results[:3000]}  # cap at 3000 chars

    Extract the single most useful, generalizable insight from these results
    for a strength training context. Return JSON only:

    {{
      "summary": "one sentence, max 250 chars, the key actionable insight",
      "category": "programming|exercise_science|periodization|recovery|technique",
      "tags": ["tag1", "tag2"],   // 2-5 lowercase tags, specific to the topic
      "confidence": 0.0-1.0       // how reliable/well-sourced does this seem?
    }}

    Do NOT include: author opinions, anecdotes, product recommendations, or anything
    not directly applicable to strength training programming.
    """

    result = claude.messages.create(
        model="claude-haiku-4-5-20251001",  # cheap/fast for distillation
        max_tokens=256,
        messages=[{"role": "user", "content": distillation_prompt}]
    )

    entry = json.loads(result.content[0].text)

    # Dedup check — don't store if we already have a near-identical entry
    if not is_duplicate(entry["tags"], entry["summary"]):
        db.session.add(AIKnowledge(
            user_id=None,           # global — applies to all users
            type="external",
            **entry,
            source=extract_url(raw_results),
        ))
        db.session.commit()
```

### After Analyzing Workout History (User Pattern Detection)

Once per week (or on demand), a background job scans recent workouts and asks
Claude if it notices any patterns worth remembering:

```python
def detect_user_patterns(user_id):
    """Run weekly. Looks for patterns in the user's last 90 days."""

    context = build_context(user_id, days=90)
    existing_patterns = get_user_patterns(user_id)  # what we already know

    prompt = f"""
    Analyze this athlete's 90-day training history.
    Already known patterns (do not repeat): {existing_patterns}

    Look for NEW, specific, repeatable patterns — things like:
    - Performance correlations ("bench drops after back-to-back training days")
    - Recovery signals ("deadlift suffers when squatted within 48hrs")
    - Progression rates ("squat TM is likely 10-15lb behind actual strength")
    - Volume responses ("performs better on 4+ sets than 2-3 sets")

    Return a JSON array of NEW patterns only (empty array if nothing new):
    [
      {{
        "summary": "one sentence, max 250 chars",
        "tags": ["user", "bench", "fatigue"],
        "confidence": 0.0-1.0
      }}
    ]

    Only report patterns you are confident about — at least 3 data points.
    Do NOT speculate.
    """

    result = claude.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )

    patterns = json.loads(result.content[0].text)
    for p in patterns:
        if not is_duplicate(p["tags"], p["summary"], user_id):
            db.session.add(AIKnowledge(
                user_id=user_id,
                type="user_pattern",
                category="user_pattern",
                **p,
            ))
    db.session.commit()
```

---

## How Memory Gets Read

On every AI trainer call, relevant knowledge is pulled from the table and
injected into the context **before** Claude sees the request.

```python
def build_context(user_id, days=21):
    # ... existing context building ...

    # Pull relevant knowledge based on what's in the current context
    relevant_tags = extract_tags_from_context(workouts, trends)
    # e.g. if bench is stalled: ["bench", "plateau", "stall", "programming"]
    # e.g. if user mentions legs: ["squat", "leg_day", "lower_body"]

    knowledge = get_relevant_knowledge(user_id, relevant_tags, limit=8)

    return {
        "workouts": workouts,
        "maxes": maxes,
        "stats": stats,
        "recency": recency_map,
        "trends": trends,
        "knowledge": knowledge,   # ← injected here
    }


def get_relevant_knowledge(user_id, tags, limit=8):
    """
    Fetch knowledge entries whose tags overlap with the current context tags.
    User-specific patterns take priority over generic external knowledge.
    Most-used entries surface first (they've proven useful before).
    """
    return (
        AIKnowledge.query
        .filter(
            db.or_(AIKnowledge.user_id == user_id, AIKnowledge.user_id == None),
            # SQLite JSON overlap: any tag in our list appears in the entry's tags
            db.or_(*[AIKnowledge.tags.contains(t) for t in tags])
        )
        .order_by(
            AIKnowledge.user_id.desc(),   # user patterns first
            AIKnowledge.use_count.desc()  # most proven first
        )
        .limit(limit)
        .all()
    )
```

The knowledge is injected into the system prompt as a compact block:

```
RELEVANT KNOWLEDGE FROM MEMORY:
[programming] Bench stalls respond better to technique resets than volume drops
[user_pattern] This athlete misses bench reps when <48hrs from previous squat session
[periodization] Effective deloads cut volume 40-60% while keeping intensity above 70%
```

**Injecting 8 entries adds ~300 tokens to the prompt — negligible cost.**

---

## Memory Management (Staying Lean)

### Confidence Decay
If new web searches contradict an existing entry, its confidence score drops.
Entries below 0.3 confidence are automatically archived (not deleted — kept for audit).

### Deduplication
Before writing any entry, run a simple overlap check:
- If > 60% tag overlap AND similar summary length → skip, don't duplicate
- This prevents the same insight being stored 10 times from 10 searches

### Age-Based Pruning (optional, run quarterly)
```python
# Archive entries that have never been used and are > 180 days old
AIKnowledge.query
    .filter(AIKnowledge.use_count == 0,
            AIKnowledge.created_at < 180_days_ago)
    .update({"archived": True})
```

### use_count Tracking
Every time an entry is injected into a prompt, increment `use_count` and update
`last_used_at`. This surfaces the most consistently useful knowledge automatically.

---

## Full Learning Loop

```
User asks for a workout
        │
        ▼
build_context()
  ├── DB: recent workouts, TMs, trends
  └── ai_knowledge table: relevant entries  ← memory read
        │
        ▼
Claude generates workout
  ├── If web search fires:
  │     ├── Search executes
  │     ├── Result returned to Claude
  │     └── distill_and_store() runs async  ← memory write (external)
  └── Workout returned to user
        │
        ▼
Weekly background job
  └── detect_user_patterns()               ← memory write (user patterns)
        │
        ▼
Next request: memory already contains what was learned
```

---

## New Files Required

```
backend/
  models/ai_knowledge.py           ← AIKnowledge SQLAlchemy model
  services/ai_memory_service.py    ← distill_and_store(), detect_user_patterns(),
                                      get_relevant_knowledge(), is_duplicate()
```

Additions to existing files:
- `backend/services/ai_trainer_service.py` — call `get_relevant_knowledge()` in `build_context()`
- `backend/app.py` — register weekly pattern detection job (can use APScheduler)
- `backend/db/database.py` — create `ai_knowledge` table migration

---

## Summary

| Concern | Solution |
|---------|----------|
| Storage bloat | Distill to 1 sentence — 99%+ size reduction |
| Redundant entries | Tag-overlap dedup before every write |
| Stale knowledge | Confidence decay + age-based archiving |
| Slow retrieval | Tag index + limit(8) — single fast query |
| Cost of distillation | Use `claude-haiku-4-5` for distillation — ~$0.0002/search |
| User privacy | User patterns scoped to `user_id` — never shared across accounts |
| Reliability | Confidence score tracks how trustworthy each entry is over time |
