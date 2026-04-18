"""
AI cost-control configuration.

All values can be overridden via environment variables.
Defaults target < $0.002 per request on gpt-4o-mini with a typical
21-day workout history.

Rough per-request cost at defaults:
  Input  ~900 tokens  × $0.00015/1K = $0.000135
  Output ~600 tokens  × $0.00060/1K = $0.000360
  Total  ≈ $0.0005  (vs. ~$0.013 on gpt-4o at same volume)
"""
import os

# ── Model selection ────────────────────────────────────────────────────────────
# gpt-4o-mini is the default — adequate for structured workout JSON.
# Set AI_MODEL=gpt-4o in .env only if higher reasoning quality is needed.
AI_MODEL      = os.getenv("AI_MODEL",      "gpt-4o-mini")
AI_MINI_MODEL = os.getenv("AI_MINI_MODEL", "gpt-4o-mini")

# ── Context window limits ──────────────────────────────────────────────────────
# Recent workouts sent with full per-set detail.
MAX_RECENT_WORKOUTS = int(os.getenv("AI_MAX_RECENT_WORKOUTS", "4"))
# Older workouts collapsed into a compact weekly summary (no per-set detail).
MAX_OLDER_WORKOUTS  = int(os.getenv("AI_MAX_OLDER_WORKOUTS",  "6"))
# Active memories injected into the prompt.
MAX_MEMORIES        = int(os.getenv("AI_MAX_MEMORIES",        "8"))
# Hard char cap on any single text field (notes, titles, memory text).
MAX_NOTE_CHARS      = int(os.getenv("AI_MAX_NOTE_CHARS",      "120"))
# Hard char cap on the user's free-text prompt.
MAX_PROMPT_CHARS    = int(os.getenv("AI_MAX_PROMPT_CHARS",    "400"))

# ── Output token cap ───────────────────────────────────────────────────────────
# A full workout JSON with 6 exercises and blocks + summary fits in ~600 tokens.
# 900 gives comfortable headroom without allowing runaway output.
MAX_OUTPUT_TOKENS = int(os.getenv("AI_MAX_OUTPUT_TOKENS", "900"))

# ── Regeneration throttling ────────────────────────────────────────────────────
# Per-user, per-calendar-day limit across ALL /api/ai/suggest calls.
# Resets at midnight UTC. Enforced server-side; frontend shows a softer UI limit.
MAX_DAILY_REQUESTS = int(os.getenv("AI_MAX_DAILY_REQUESTS", "20"))
# UI-side session regen limit (regenerate button only, not first suggest).
UI_MAX_REGENS = int(os.getenv("AI_UI_MAX_REGENS", "5"))

# ── Feature flags ──────────────────────────────────────────────────────────────
# Web search (Phase 2). Disabled by default — set AI_ALLOW_WEB_SEARCH=true to enable.
# Requires TAVILY_API_KEY to be set; app degrades gracefully if the key is absent.
# Never used for workout generation — only for educational/answer-mode questions.
ALLOW_WEB_SEARCH = os.getenv("AI_ALLOW_WEB_SEARCH", "false").lower() == "true"

# ── Web search limits ──────────────────────────────────────────────────────────
# Max Tavily results fetched per query.
MAX_SEARCH_RESULTS   = int(os.getenv("AI_MAX_SEARCH_RESULTS",    "3"))
# Hard char cap on raw content per result before distillation.
MAX_SEARCH_CHARS     = int(os.getenv("AI_MAX_SEARCH_CHARS",      "600"))
# Hard char cap on the final distilled search summary injected into the prompt.
SEARCH_DISTILL_CHARS = int(os.getenv("AI_SEARCH_DISTILL_CHARS",  "300"))
