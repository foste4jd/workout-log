"""
Workout natural-language interpreter.

Converts free-form text like "squat 3x5 at 225, front squat 5x5 ramp 10%"
into a canonical multi-exercise workout payload that populates the log builder.

Architecture:
- interpret_workout() is the only public entry point.
- The LLM provider is shared with ai_trainer_service via _get_provider().
- Output schema is fixed and versioned here — the LLM is just the parsing engine.
- Voice path: send any transcript text to interpret_workout(); nothing else changes.
- Local LLM path: replace _get_provider().complete_mini() — one line, zero other changes.
"""

import json
import logging
import re

logger = logging.getLogger(__name__)

_INTERPRET_SYSTEM = """\
You are a strength training workout parser. Parse natural-language workout descriptions \
into structured JSON. Return ONLY valid JSON — no prose, no markdown.

OUTPUT SCHEMA:
{
  "confidence": 0.0-1.0,
  "needs_confirmation": false,
  "assumptions": ["list any non-obvious interpretations"],
  "exercises": [
    {
      "name": "Exercise Name",
      "library_match": "exact|fuzzy|none",
      "notes": null,
      "sets": [
        {
          "set_number": 1,
          "set_type": "working|warmup|amrap|failure",
          "reps": integer_or_null,
          "weight_lb": float_or_null,
          "percent": float_or_null
        }
      ]
    }
  ]
}

RULES:
1. SEGMENTATION: Identify each distinct exercise. Common delimiters: commas, "then", "and", \
   "followed by", or a new exercise name starting mid-sentence.
2. EXPAND FULLY: "3x5" = three separate set objects. Never use count shorthand in output.
3. MODIFIER SCOPING: A modifier ("ramp 10%", "add 5 each set", "pyramid up") applies to the \
   exercise it immediately follows, not globally. If ambiguous, scope to the nearest exercise \
   and document in assumptions.
4. RAMP MATH: "135 ramp 10% each set over 5 sets" → 135, 148.5, 163.5, 179.5, 197.5 \
   (compound 10% each set, round to nearest 2.5 lb). "add 10 each set" is additive not multiplicative.
5. SET TYPES: warmup = "warm up"/"wu"; amrap = "amrap"/"max reps"/"as many as possible"/"+"; \
   failure = "to failure"; working = everything else.
6. WEIGHTS: Absolute pounds in weight_lb. Convert kg → lb (multiply by 2.20462, round to 2.5). \
   Only use percent field when user explicitly references % of training max (e.g. "75%", "75% of max").
7. LIBRARY MATCHING: Match exercise names to the provided library. Prefer exact matches. \
   For fuzzy matches (e.g. "squat" → "Back Squat"), document in assumptions if non-obvious.
8. CONFIDENCE: 1.0 = unambiguous; 0.7-0.9 = reasonable assumptions made; \
   <0.7 = needs_confirmation=true. Still return best-effort result even at low confidence.
9. VOICE TOLERANCE: Input may lack punctuation or have spoken numbers ("three by five", \
   "two twenty five"). Interpret these correctly.
"""


def interpret_workout(text: str, library_exercises: list, training_maxes: dict) -> dict:
    """
    Parse natural-language workout text into a canonical multi-exercise dict.

    Args:
        text: raw user input (typed or voice transcript)
        library_exercises: list of {id, name} dicts from ExerciseLibrary
        training_maxes: {exercise_name: weight_lb} for the current user (for context only)

    Returns:
        {confidence, needs_confirmation, assumptions, exercises: [{name, library_id,
         library_match, notes, sets: [{set_number, set_type, reps, weight_lb, percent}]}]}
    """
    from backend.services.ai_provider import get_provider as _get_provider, truncate as _truncate

    text = _truncate((text or "").strip(), 600)
    if not text:
        return _empty()

    lib_names = sorted({e["name"] for e in library_exercises})[:80]
    lib_hint = ", ".join(lib_names)

    tm_lines = []
    if training_maxes:
        for name, w in list(training_maxes.items())[:12]:
            tm_lines.append(f"  {name}: {w} lb")

    user_msg_parts = [
        f"Exercise library (match names to these):\n{lib_hint}",
    ]
    if tm_lines:
        user_msg_parts.append("User training maxes:\n" + "\n".join(tm_lines))
    user_msg_parts.append(f"Workout to interpret:\n{text}")

    messages = [
        {"role": "system", "content": _INTERPRET_SYSTEM},
        {"role": "user",   "content": "\n\n".join(user_msg_parts)},
    ]

    provider = _get_provider()
    try:
        raw    = provider.complete_mini(messages)
        result = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("interpret_service | JSON decode failed; input=%r", text[:80])
        return _error_result(text)
    except Exception as exc:
        logger.error("interpret_service | provider error: %s", exc)
        return _error_result(text)

    return _normalize(result, library_exercises)


# ── Internal helpers ───────────────────────────────────────────────────────────

def _normalize(result: dict, library_exercises: list) -> dict:
    """Validate schema, resolve library IDs, renumber sets."""
    lib_by_name = {e["name"].lower(): e for e in library_exercises}

    normalized = []
    for ex in (result.get("exercises") or []):
        name = (ex.get("name") or "").strip()
        if not name:
            continue

        # Library ID resolution — exact first, then word-subset fuzzy
        lib_entry = lib_by_name.get(name.lower())
        if not lib_entry:
            ex_words = set(re.findall(r"\w+", name.lower()))
            for lib_name, entry in lib_by_name.items():
                lib_words = set(re.findall(r"\w+", lib_name))
                shorter = ex_words if len(ex_words) <= len(lib_words) else lib_words
                longer  = lib_words if len(ex_words) <= len(lib_words) else ex_words
                if len(shorter) >= 2 and shorter.issubset(longer):
                    lib_entry = entry
                    break

        canonical_name = lib_entry["name"] if lib_entry else name

        sets = []
        for i, s in enumerate(ex.get("sets") or []):
            w = s.get("weight_lb")
            sets.append({
                "set_number": i + 1,
                "set_type":   s.get("set_type", "working"),
                "reps":       s.get("reps"),
                "weight_lb":  round(w / 2.5) * 2.5 if w else None,
                "percent":    s.get("percent"),
            })

        if not sets:
            continue

        normalized.append({
            "name":          canonical_name,
            "library_id":    lib_entry["id"] if lib_entry else None,
            "library_match": ex.get("library_match", "none"),
            "notes":         ex.get("notes") or None,
            "sets":          sets,
        })

    confidence = min(1.0, max(0.0, float(result.get("confidence", 0.8))))
    needs_conf = bool(result.get("needs_confirmation", False)) or confidence < 0.7

    return {
        "confidence":        confidence,
        "needs_confirmation": needs_conf,
        "assumptions":       list(result.get("assumptions") or []),
        "exercises":         normalized,
    }


def _empty() -> dict:
    return {
        "confidence": 0.0, "needs_confirmation": True,
        "assumptions": ["No input provided."], "exercises": [],
    }


def _error_result(text: str) -> dict:
    return {
        "confidence": 0.0, "needs_confirmation": True,
        "assumptions": [f"Could not parse input — try rephrasing: \"{text[:60]}\""],
        "exercises": [],
    }
