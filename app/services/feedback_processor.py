"""
Feedback Processor — translates FeedbackSurvey results into profile updates.

Low scores (≤2) trigger new correction rules in Person.feedback_deltas.
High scores (≥4) confirm existing behaviour (no change needed).
"""

from __future__ import annotations

from typing import Any

from app.models.feedback import FeedbackSurvey
from app.models.person import Person

_DIMENSION_LABELS = {
    "realism_score": "전반적 현실감",
    "personality_accuracy": "성격 정확도",
    "communication_style_accuracy": "말투/커뮤니케이션 스타일",
    "humor_accuracy": "유머 스타일",
    "knowledge_accuracy": "지식/경험 정확도",
}


def process_feedback(person: Person, survey: FeedbackSurvey) -> list[Any]:
    """
    Compute a list of feedback delta dicts and return them.
    The caller is responsible for appending these to person.feedback_deltas
    and committing the change.
    """
    new_deltas: list[dict[str, Any]] = []

    # --- Dimension-level corrections for low scores ---
    for field, label in _DIMENSION_LABELS.items():
        score = getattr(survey, field, 3)
        if score <= 2:
            new_deltas.append({
                "source": "auto_low_score",
                "aspect": field,
                "label": label,
                "score": score,
                "desired_behavior": f"{label}이 낮게 평가됨 (점수 {score}/5). 더 자연스럽게 개선 필요.",
            })

    # --- Explicit corrections from the evaluator ---
    for correction in (survey.corrections or []):
        if isinstance(correction, dict):
            new_deltas.append({
                "source": "explicit_correction",
                "aspect": correction.get("aspect", "general"),
                "desired_behavior": correction.get("desired_behavior", ""),
                "replaced": correction.get("current_behavior", ""),
            })

    # --- Missing traits ---
    for trait in (survey.missing_traits or []):
        new_deltas.append({
            "source": "missing_trait",
            "aspect": "missing_trait",
            "desired_behavior": f"다음 특성을 더 표현하세요: {trait}",
        })

    # --- Extra traits (things that felt wrong) ---
    for trait in (survey.extra_traits or []):
        new_deltas.append({
            "source": "extra_trait",
            "aspect": "extra_trait",
            "desired_behavior": f"다음 특성은 해당 인물답지 않으니 줄이세요: {trait}",
        })

    return new_deltas


def apply_feedback_to_person(person: Person, survey: FeedbackSurvey) -> None:
    """
    Mutate person.feedback_deltas in-place with new corrections.
    Keeps at most 50 most-recent deltas to avoid prompt bloat.
    """
    new_deltas = process_feedback(person, survey)
    existing = list(person.feedback_deltas or [])
    merged = existing + new_deltas
    # Keep the most recent 50 deltas
    person.feedback_deltas = merged[-50:]
