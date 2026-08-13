"""Explains whatever optimization_service already found deterministically --
this module never decides WHAT to recommend, only writes the reasoning for
recommendations that already exist. Exactly ONE Groq call per
`generate_recommendations()` run, regardless of how many candidates were
found -- every candidate is described in one prompt and the model returns
one explanation per candidate in a single structured JSON response, not
one call per candidate. If no Groq key is configured, or the call fails
for any reason, deterministic template explanations are used instead --
this feature can never fail to produce recommendations just because the
AI layer is unavailable.
"""
import json
import logging
import uuid

from groq import Groq
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.recommendation import Recommendation
from app.services.dashboard_service import warehouse_capacity_detail
from app.services.optimization_service import (
    find_merge_candidates,
    find_overloaded_warehouses,
    find_redundant_warehouses,
    find_underutilized_warehouses,
)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You write short, plain-English explanations for warehouse \
optimization recommendations, for an operations team deciding what to act \
on. You're given a numbered list of already-decided recommendations -- \
your only job is to explain each one in 1-3 sentences, using ONLY the \
numbers given. Never invent a warehouse name, a number, or a person -- if \
the data doesn't support a claim, don't make it.

Respond with ONLY a JSON object of this exact shape, one explanation per \
item, in the same order as given:
{"explanations": ["...", "...", ...]}"""


def _fallback_explanation(category: str, context: dict) -> str:
    """Deterministic, no-AI-needed text -- used when Groq is unavailable so
    the feature still works, just without the more natural phrasing."""
    if category == "merge_opportunity":
        return (
            f"{context['name_a']} ({context['code_a']}) and {context['name_b']} ({context['code_b']}) are both "
            f"underutilized ({context['count_a']}/{context['capacity_a'] or '?'} and "
            f"{context['count_b']}/{context['capacity_b'] or '?'} locations used) and share the same warehouse "
            f"type -- consolidating one into the other could free up a warehouse."
        )
    if category == "redundant_warehouse":
        return f"{context['name']} ({context['code']}) has zero locations recorded -- consider removing or repurposing it."
    if category == "underutilized":
        return (
            f"{context['name']} ({context['code']}) is using only {context['count']} of {context['capacity']} "
            f"configured locations -- well below typical utilization."
        )
    return (
        f"{context['name']} ({context['code']}) has {context['count']} locations against a capacity of "
        f"{context['capacity']} -- more locations are defined than the warehouse is sized for."
    )


def generate_recommendations(db: Session) -> list[Recommendation]:
    merge_candidates = find_merge_candidates(db)
    redundant = find_redundant_warehouses(db)
    underutilized = find_underutilized_warehouses(db)
    overloaded = find_overloaded_warehouses(db)

    # A warehouse already named in a merge opportunity doesn't also need its
    # own standalone "underutilized"/"redundant" entry -- that would just
    # repeat the same underlying fact twice with less context than the
    # merge recommendation already gives.
    covered_by_merge = {w.id for c in merge_candidates for w in (c.warehouse_a, c.warehouse_b)}
    redundant = [w for w in redundant if w.id not in covered_by_merge]
    underutilized = [w for w in underutilized if w.id not in covered_by_merge]

    # Each entry: (category, warehouse_ids, title, context_for_fallback)
    items: list[tuple[str, list[uuid.UUID], str, dict]] = []

    for c in merge_candidates:
        items.append(
            (
                "merge_opportunity",
                [c.warehouse_a.id, c.warehouse_b.id],
                f"Merge opportunity: {c.warehouse_a.name} + {c.warehouse_b.name}",
                {
                    "name_a": c.warehouse_a.name, "code_a": c.warehouse_a.generated_code, "count_a": c.location_count_a,
                    "capacity_a": c.warehouse_a.capacity,
                    "name_b": c.warehouse_b.name, "code_b": c.warehouse_b.generated_code, "count_b": c.location_count_b,
                    "capacity_b": c.warehouse_b.capacity,
                },
            )
        )
    for w in redundant:
        items.append(
            ("redundant_warehouse", [w.id], f"Redundant warehouse: {w.name}", {"name": w.name, "code": w.generated_code})
        )
    for w in underutilized:
        detail = warehouse_capacity_detail(db, w)
        items.append(
            (
                "underutilized", [w.id], f"Underutilized: {w.name}",
                {"name": w.name, "code": w.generated_code, "count": detail["location_count"], "capacity": w.capacity},
            )
        )
    for w in overloaded:
        detail = warehouse_capacity_detail(db, w)
        items.append(
            (
                "overloaded", [w.id], f"Overloaded: {w.name}",
                {"name": w.name, "code": w.generated_code, "count": detail["location_count"], "capacity": w.capacity},
            )
        )

    # Clear the previous generation's results -- this is a fresh snapshot,
    # not a history table (see Recommendation's docstring).
    db.query(Recommendation).delete()

    if not items:
        db.commit()
        return []

    explanations = _get_explanations(items)

    recommendations = [
        Recommendation(category=category, warehouse_ids=[str(i) for i in ids], title=title, explanation=explanation)
        for (category, ids, title, _ctx), explanation in zip(items, explanations)
    ]
    db.add_all(recommendations)
    db.commit()
    for r in recommendations:
        db.refresh(r)
    return recommendations


def _get_explanations(items: list[tuple[str, list[uuid.UUID], str, dict]]) -> list[str]:
    fallback = [_fallback_explanation(category, ctx) for category, _ids, _title, ctx in items]

    if not settings.groq_api_key:
        return fallback

    numbered = "\n".join(f"{i + 1}. {title}: {json.dumps(ctx)}" for i, (_c, _ids, title, ctx) in enumerate(items))

    try:
        client = Groq(api_key=settings.groq_api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": numbered},
            ],
            max_completion_tokens=1500,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        parsed = json.loads(response.choices[0].message.content or "{}")
        explanations = parsed.get("explanations")
        if not isinstance(explanations, list) or len(explanations) != len(items):
            raise ValueError("Model response didn't match the expected shape")
        return [str(e) for e in explanations]
    except Exception:
        logger.exception("AI recommendation explanation request failed -- using deterministic fallback text")
        return fallback
