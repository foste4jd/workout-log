# AI Trainer — Design Plan

## Two Modes

The AI trainer has two distinct interaction surfaces that share the same backend
context engine and Claude integration underneath.

```
┌──────────────────────────────────────────────────────────────┐
│                    AI Trainer Backend                        │
│                                                              │
│   build_context()  ──►  Claude (claude-opus-4-6)             │
│   (workouts, TMs,         │   ▲                              │
│    recency, trends)       │   └── web_search tool (optional) │
└───────────────────────────┼──────────────────────────────────┘
                            │
              ┌─────────────┴──────────────┐
              │                            │
              ▼                            ▼
   ┌─────────────────────┐    ┌────────────────────────┐
   │  Mode 1             │    │  Mode 2                │
   │  "Build My Workout" │    │  "Ask the Trainer"     │
   │                     │    │                        │
   │  One click on the   │    │  Chat interface —      │
   │  Log page. Auto-    │    │  type anything.        │
   │  fills the form.    │    │  Conversational.       │
   └─────────────────────┘    └────────────────────────┘
```

---

## Mode 1 — "Build My Workout" (Log Workout Page)

### What It Is
A single button on the existing `/log` page. You click it, the AI reads your
history and silently pre-fills the entire exercise builder with a suggested
workout for today. You review, tweak if needed, and save.

Zero typing. Zero friction.

### UX Flow

```
/log page (existing)
│
├── [Date]  [Title]  [Duration]
│
├── ✦ AI TRAINER ──────────────────────────────────────────────┐
│   "Not sure what to do today? Let the trainer decide."      │
│   [ ] Also search the web for programming ideas             │
│                               [ Build My Workout → ]        │
│   ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
│   ┌─ Trainer's Reasoning ──────────────────────────────┐    │
│   │ "You squatted heavy 2 days ago and your bench has  │    │
│   │  stalled for 3 sessions. Today is upper body —     │    │
│   │  lighter bench with pause work, rows, and arms."   │    │
│   └────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
│
├── EXERCISES  (pre-filled by trainer)
│   ├── Bench Press    [warmup 5×45%] [3×70%] [3×75%] [3×75%]
│   ├── Incline Press  [4×8]
│   ├── Bent-Over Row  [4×8]
│   └── Tricep PD      [3×15]
│
└── [ Cancel ]  [ Save Workout ]
```

### What Changes on the Log Page
- A collapsible "AI Trainer" card added above the exercise builder
- "Build My Workout" button calls `POST /api/ai/suggest`
- Response auto-populates title field and drops exercises into the builder
  exactly as if you had typed them manually — unit-aware, TM-aware
- Trainer's reasoning shows in the card (collapsible)
- User can still add/remove/edit any exercise before saving

---

## Mode 2 — "Ask the Trainer" (Dedicated `/trainer` Page)

### What It Is
A full chat interface. You type in plain English. The trainer responds with
reasoning AND a structured workout. Multi-turn — you can push back, ask for
changes, add constraints, and it will revise.

### UX Flow

```
/trainer
│
├── NAV: Dashboard | Workouts | Templates | Maxes | Trainer ◄ new
│
├── ─────────────────────────────────────────────────────────
│   YOUR TRAINER
│   Knows your last 21 days. Ask it anything.
│   ─────────────────────────────────────────────────────────
│
├── CONVERSATION ─────────────────────────────────────────────
│
│   ┌─ You ──────────────────────────────────────────────────┐
│   │ "Give me a heavy leg day with bicep-focused            │
│   │  accessories. I have dumbbells and a squat rack."      │
│   └────────────────────────────────────────────────────────┘
│
│   ┌─ Trainer ──────────────────────────────────────────────┐
│   │ Your last squat session was 3 days ago (Day 4,         │
│   │ Thick Thigh Thursday) — you hit 85% cleanly. You're   │
│   │ recovered and ready to go heavy. Here's your day:      │
│   │                                                         │
│   │ HEAVY LEG DAY + BICEP ACCESSORIES                      │
│   │ ─────────────────────────────────                      │
│   │ Back Squat      5@65%, 5@75%, 3@83%, 3@87%, 1@92%     │
│   │ Romanian DL     4×5 (heavy)                            │
│   │ Bulgarian Split 3×8 each leg                           │
│   │ ── Accessories ──                                       │
│   │ Barbell Curl    4×8                                    │
│   │ Hammer Curl     3×12                                   │
│   │ Concentration   3×15                                   │
│   │                                                         │
│   │ [  Log This Today  ]  [  Save as Template  ]           │
│   └────────────────────────────────────────────────────────┘
│
│   ┌─ You ──────────────────────────────────────────────────┐
│   │ "Actually drop the Bulgarian splits, my hip flexors    │
│   │  are pretty tight today"                               │
│   └────────────────────────────────────────────────────────┘
│
│   ┌─ Trainer ──────────────────────────────────────────────┐
│   │ Got it — swapping Bulgarians for Leg Press (gentler    │
│   │ on the hip flexors, still loads the quads):            │
│   │ ...revised workout...                                  │
│   │ [  Log This Today  ]  [  Save as Template  ]           │
│   └────────────────────────────────────────────────────────┘
│
├── ─────────────────────────────────────────────────────────
│   [ ] Let trainer search the web
│   ┌──────────────────────────────────────────── [Send ▶] ┐
│   │ Type anything — e.g. "push day, 45 minutes, no bench" │
│   └────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────
```

### Example Prompts It Handles Well
- `"Heavy leg day, I have dumbbells and a squat rack"`
- `"Full body, I only have 40 minutes"`
- `"My lower back is sore, give me an upper body day"`
- `"I haven't benched in 10 days, let's get back to it"`
- `"Deload week — what should I do?"`
- `"What does my training look like this week? Am I overtraining?"`
- `"Build me a 5/3/1 week 2 squat day based on my TM"`

### Conversation Memory
Each reply includes the full message history so the AI remembers what was said
earlier in the conversation. Conversation is not persisted between page loads
(session only) — keeping it simple and avoiding a whole chat history DB.

---

## Shared Backend

Both modes hit the same endpoint and service. The only difference is the input.

### Endpoint: `POST /api/ai/suggest`

```python
{
  # Mode 1 — "Build My Workout"
  "mode": "auto",
  "allow_web": false

  # Mode 2 — "Ask the Trainer" (single turn or multi-turn)
  "mode": "chat",
  "message": "Give me a heavy leg day with bicep accessories...",
  "history": [                      # previous turns, empty on first message
    { "role": "user",      "content": "..." },
    { "role": "assistant", "content": "..." }
  ],
  "allow_web": true
}
```

### Response Shape (both modes)

```json
{
  "reasoning": "Your last squat was 3 days ago and you hit 85% cleanly...",
  "reply": "Here's your heavy leg day...",       // chat-style text (Mode 2 only)
  "workout": {
    "title": "Heavy Leg Day + Bicep Accessories",
    "exercises": [
      {
        "name": "Back Squat",
        "exercise_library_id": 1,
        "sets": [
          { "set_type": "working", "reps": 5, "percent": 65 },
          { "set_type": "working", "reps": 5, "percent": 75 },
          { "set_type": "working", "reps": 3, "percent": 83 }
        ]
      },
      {
        "name": "Barbell Curl",
        "exercise_library_id": 75,
        "sets": [
          { "set_type": "working", "reps": 8 },
          { "set_type": "working", "reps": 8 }
        ]
      }
    ]
  }
}
```

### Service: `backend/services/ai_trainer_service.py`

```python
def handle_request(user_id, mode, message=None, history=None, allow_web=False):
    # Always build fresh context from DB
    context = build_context(user_id, days=21)

    tools = [web_search_tool] if allow_web else []

    if mode == "auto":
        # No user message — trainer decides everything
        user_content = build_auto_prompt(context)
    else:
        # Chat mode — prepend context to the user's message
        user_content = build_chat_prompt(context, message)

    messages = (history or []) + [{"role": "user", "content": user_content}]

    response = anthropic_client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=tools,
        messages=messages,
    )

    # Handle tool_use loop, then parse JSON from final text block
    return parse_response(response)
```

---

## The Local Context (What Claude Always Sees)

Built fresh on every request — no stale cache.

### 1. Recent Workout History (last 21 days)
Every workout with every set: weight, reps, percent of TM, and whether it was
**completed**. This is how the AI sees missed reps and failed sets.

### 2. Training Maxes
```json
{ "Back Squat": 410, "Bench Press": 275, "Deadlift": 455 }
```

### 3. Muscle Group Recency Map
Built server-side by scanning exercise names against a movement pattern map:
```json
{
  "squat":            1,   // days since last trained
  "hinge":            3,
  "horizontal_push":  2,
  "vertical_pull":    4,
  "horizontal_pull":  2,
  "carry":            7
}
```

### 4. Performance Trends (last 4 sessions per lift)
```json
{
  "Back Squat":  { "trend": "progressing", "missed_reps_last_session": false },
  "Bench Press": { "trend": "stalled",     "missed_reps_last_session": true  }
}
```

### 5. Stats
```json
{ "this_week": 3, "current_streak": 5, "personal_records": [...] }
```

---

## System Prompt (shared by both modes)

```
You are an experienced strength and conditioning coach with full access to
the athlete's recent training history, training maxes, and performance trends.

ALWAYS:
- Read the recency map before programming any lift — never load a pattern
  that was trained within the last 24 hours unless the athlete explicitly requests it
- If an athlete missed reps last session on a lift, do NOT increase the percentage
- If the athlete has trained 5+ days this week, suggest a deload or recovery day
- Match exercise names exactly to the provided exercise library list
- Return a structured JSON workout block in EVERY response so it can be logged

IN CHAT MODE:
- Honor the athlete's stated constraints (equipment, muscle focus, time, injuries)
- If they push back or ask for changes, revise the workout and return a new JSON block
- Keep responses concise — reasoning in 2-3 sentences, then the workout

IN AUTO MODE:
- Decide the workout entirely based on history and recency
- Explain the choice in 2-3 sentences
```

---

## Optional: Web Search Tool

Only fires when the AI needs external programming knowledge.

| Trigger | Example Search |
|---------|---------------|
| User mentions a specific program | `"5/3/1 week 2 squat percentages"` |
| Missed reps on key lift | `"bench press stall fix percentage-based programming"` |
| User asks about deload | `"powerlifting deload week structure"` |
| User mentions equipment | `"dumbbell-only leg day no squat rack"` |
| Injury mentioned | `"lower back tight squat alternative exercises"` |

Recommended: **Tavily Search API** — designed for AI agents, returns clean
structured text, free tier available.

---

## What Makes It Smart

| Signal | How AI Uses It |
|--------|---------------|
| Missed reps last session | Holds or drops % on that lift |
| Trained same pattern yesterday | Steers away unless you ask for it |
| 5+ days trained this week | Suggests deload or active recovery |
| Weight trending up 4+ sessions | May suggest a TM bump |
| Movement gap > 7 days | Prioritizes getting it back in |
| User says "my back is tight" | Avoids loading that area |
| User specifies equipment | Only programs what you have |
| User specifies time | Trims volume to fit the window |

---

## Build Order

### Phase 1 — Core (no web search yet)
1. `build_context()` service — DB queries, recency map, trends
2. `POST /api/ai/suggest` endpoint — handles both modes
3. Claude integration — structured JSON output, system prompt
4. **Mode 1:** "Build My Workout" card on the `/log` page
5. **Mode 2:** `/trainer` chat page with conversation history

### Phase 2 — Web Search
6. Tavily integration as a Claude tool
7. Toggle on both UI surfaces to enable it

### Phase 3 — Polish
8. Skeleton loader on the log page while the AI generates
9. Streaming response on the chat page (text appears as it's typed)
10. Persist conversation history in `sessionStorage` (survives page refresh
    but not browser close — no extra DB needed)

---

## New Files Required

```
backend/
  api/routes/ai_trainer.py        ← single endpoint, both modes
  services/ai_trainer_service.py  ← context builder + Claude call
  services/web_search.py          ← Tavily wrapper (Phase 2)

frontend/templates/
  trainer.html                    ← /trainer chat page

frontend/static/js/
  trainer.js                      ← chat UI logic (or inline in trainer.html)
```

Existing files touched:
- `backend/app.py` — register ai_trainer blueprint
- `frontend/templates/log.html` — add AI Trainer card
- All navbar templates — add "Trainer" nav link
```
