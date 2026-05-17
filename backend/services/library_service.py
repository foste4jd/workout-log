"""
Exercise library search and alias resolution.

Index is built lazily on first call and cached in-process.
Call invalidate() after any write to exercise_library.
"""
import re
import difflib
from typing import Optional

from backend.models.exercise_library import ExerciseLibrary


# ── Normalization ─────────────────────────────────────────────────────────────

_ABBREV = {
    "barbell": "bb",
    "dumbbell": "db",
    "kettlebell": "kb",
    "single arm": "sa",
    "overhead": "oh",
    "romanian": "rdl",
    "bulgarian": "bss",
}

_STRIP = re.compile(r"[^a-z0-9\s]")
_WS = re.compile(r"\s+")


def _token_overlap(query: str, target: str) -> float:
    """Fraction of query tokens that appear in target. Range [0, 1]."""
    q_tokens = set(query.split())
    t_tokens = set(target.split())
    if not q_tokens:
        return 0.0
    return len(q_tokens & t_tokens) / len(q_tokens)


def _normalize(text: str) -> str:
    t = text.lower().strip()
    t = _STRIP.sub(" ", t)
    t = _WS.sub(" ", t).strip()
    for long, short in _ABBREV.items():
        t = t.replace(long, short)
    return t


# ── In-process index ─────────────────────────────────────────────────────────

class _Index:
    def __init__(self):
        exercises = (
            ExerciseLibrary.query
            .filter_by(is_active=True)
            .order_by(ExerciseLibrary.sort_order)
            .all()
        )
        self.exercises: list[ExerciseLibrary] = exercises
        self.name_map: dict[str, ExerciseLibrary] = {}
        self.alias_map: dict[str, ExerciseLibrary] = {}
        # (normalized_term, exercise) — ordered by sort_order for tiebreaking
        self.terms: list[tuple[str, ExerciseLibrary]] = []

        for ex in exercises:
            norm = _normalize(ex.name)
            self.name_map[norm] = ex
            self.terms.append((norm, ex))
            for alias in (ex.aliases or []):
                norm_alias = _normalize(alias)
                if norm_alias not in self.alias_map:
                    self.alias_map[norm_alias] = ex
                if not any(t == norm_alias for t, _ in self.terms if _ is ex):
                    self.terms.append((norm_alias, ex))

    @property
    def all_terms(self) -> list[str]:
        return [t for t, _ in self.terms]


_cache: Optional[_Index] = None


def _get_index() -> _Index:
    global _cache
    if _cache is None:
        _cache = _Index()
    return _cache


def invalidate() -> None:
    """Drop the in-process cache. Call after any write to exercise_library."""
    global _cache
    _cache = None


# ── Public API ────────────────────────────────────────────────────────────────

def resolve(query: str) -> Optional[ExerciseLibrary]:
    """
    Resolve free-text user input to a single canonical exercise.

    Resolution order:
      1. Exact canonical name (normalized)
      2. Exact alias (normalized)
      3. Fuzzy match across all names + aliases (cutoff 0.6)

    Returns None when no confident match is found.
    """
    idx = _get_index()
    norm = _normalize(query)

    if norm in idx.name_map:
        return idx.name_map[norm]

    if norm in idx.alias_map:
        return idx.alias_map[norm]

    matches = difflib.get_close_matches(norm, idx.all_terms, n=1, cutoff=0.6)
    if matches:
        matched = matches[0]
        for term, ex in idx.terms:
            if term == matched:
                return ex

    return None


def _has_equipment(ex: "ExerciseLibrary", equipment: str) -> bool:
    """equipment is now a JSON array; support single-string queries."""
    eq = ex.equipment or []
    if isinstance(eq, str):
        return eq == equipment
    return equipment in eq


def search(
    query: str,
    limit: int = 20,
    equipment: Optional[str] = None,
    movement_pattern: Optional[str] = None,
    muscle: Optional[str] = None,
    category: Optional[str] = None,
    tier: Optional[str] = None,
) -> list[ExerciseLibrary]:
    """
    Ranked exercise search with optional filters.

    Scoring:
      1.0  — exact canonical name match
      0.95 — exact alias match
      0.4+ — difflib ratio for fuzzy hits

    Ties broken by sort_order (lower = higher priority).
    Filters (equipment, movement_pattern, muscle, category, tier) narrow the
    candidate pool.
    """
    idx = _get_index()
    norm = _normalize(query)

    candidates = idx.exercises
    if equipment:
        candidates = [e for e in candidates if _has_equipment(e, equipment)]
    if movement_pattern:
        candidates = [e for e in candidates if e.movement_pattern == movement_pattern]
    if muscle:
        candidates = [
            e for e in candidates
            if e.primary_muscle == muscle or muscle in (e.secondary_muscles or [])
        ]
    if category:
        candidates = [e for e in candidates if e.category == category]
    if tier:
        candidates = [e for e in candidates if e.tier == tier]

    candidate_ids = {e.id for e in candidates}
    filtered_terms = [(t, ex) for t, ex in idx.terms if ex.id in candidate_ids]
    filtered_term_strings = [t for t, _ in filtered_terms]

    scored: list[tuple[float, ExerciseLibrary]] = []
    seen: set[int] = set()

    # Exact name
    if norm in idx.name_map and idx.name_map[norm].id in candidate_ids:
        ex = idx.name_map[norm]
        scored.append((1.0, ex))
        seen.add(ex.id)

    # Exact alias
    if norm in idx.alias_map and idx.alias_map[norm].id in candidate_ids:
        ex = idx.alias_map[norm]
        if ex.id not in seen:
            scored.append((0.95, ex))
            seen.add(ex.id)

    # Fuzzy across filtered terms — combine char ratio with token overlap
    # to prevent short shared suffixes (e.g. " curl") from hijacking results.
    close = difflib.get_close_matches(norm, filtered_term_strings, n=limit * 3, cutoff=0.4)
    for matched_term in close:
        for term, ex in filtered_terms:
            if term == matched_term and ex.id not in seen:
                char_ratio = difflib.SequenceMatcher(None, norm, term).ratio()
                token_ratio = _token_overlap(norm, term)
                combined = char_ratio * 0.6 + token_ratio * 0.4
                scored.append((combined, ex))
                seen.add(ex.id)
                break

    # Blend fuzzy score (70%) with inverse sort_order (30%) so common exercises
    # surface first when fuzzy scores are close.
    _max_order = 500.0
    blended = [
        (score * 0.7 + (1.0 - ex.sort_order / _max_order) * 0.3, ex)
        for score, ex in scored
    ]
    blended.sort(key=lambda x: -x[0])
    return [ex for _, ex in blended[:limit]]


def list_all(
    equipment: Optional[str] = None,
    movement_pattern: Optional[str] = None,
    muscle: Optional[str] = None,
    category: Optional[str] = None,
    tier: Optional[str] = None,
) -> list[ExerciseLibrary]:
    """Return all active exercises, optionally filtered, ordered by sort_order."""
    idx = _get_index()
    results = idx.exercises
    if equipment:
        results = [e for e in results if _has_equipment(e, equipment)]
    if movement_pattern:
        results = [e for e in results if e.movement_pattern == movement_pattern]
    if muscle:
        results = [
            e for e in results
            if e.primary_muscle == muscle or muscle in (e.secondary_muscles or [])
        ]
    if category:
        results = [e for e in results if e.category == category]
    if tier:
        results = [e for e in results if e.tier == tier]
    return results


def add_custom(
    name: str,
    primary_muscle: str,
    equipment: "str | list[str]",
    movement_pattern: str,
    aliases: Optional[list[str]] = None,
    secondary_muscles: Optional[list[str]] = None,
    unilateral: bool = False,
    category: Optional[str] = None,
) -> ExerciseLibrary:
    """
    Persist a user-defined exercise and refresh the index.
    Raises ValueError if an exercise with the same name already exists.
    equipment may be a single string or a list.
    """
    from backend.db.database import db

    if ExerciseLibrary.query.filter_by(name=name).first():
        raise ValueError(f"Exercise '{name}' already exists.")

    eq = [equipment] if isinstance(equipment, str) else (equipment or [])
    ex = ExerciseLibrary(
        name=name,
        aliases=aliases or [],
        primary_muscle=primary_muscle,
        secondary_muscles=secondary_muscles or [],
        equipment=eq,
        movement_pattern=movement_pattern,
        unilateral=unilateral,
        is_custom=True,
        sort_order=500,
        category=category or "accessory",
        tier="optional",
    )
    db.session.add(ex)
    db.session.commit()
    invalidate()
    return ex