"""
Prompt Builder — converts a Person record into a structured Claude system prompt.

The prompt has 5 sections:
  1. Identity Anchor  (stable, good for cache_control)
  2. Personality Core
  3. Communication Style
  4. Behavioral Rules (custom_directions + feedback_deltas)
  5. Few-Shot Examples (dynamically injected at chat time)
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.person import Person

_MBTI_DESCRIPTIONS: dict[str, str] = {
    "E": "extraversion — you draw energy from being around people, you are expressive and sociable",
    "I": "introversion — you prefer deeper one-on-one interactions and need solitude to recharge",
    "S": "sensing — you focus on concrete facts, practical details, and present realities",
    "N": "intuition — you think in patterns, possibilities, and future concepts",
    "T": "thinking — you make decisions based on logic and objective analysis",
    "F": "feeling — you consider emotions, values, and the impact on people when deciding",
    "J": "judging — you prefer structure, plans, and clear conclusions",
    "P": "perceiving — you are flexible, spontaneous, and open to new information",
}


def _describe_mbti(mbti_type: str | None, mbti_raw: dict[str, Any]) -> str:
    if not mbti_type:
        return ""
    traits = [_MBTI_DESCRIPTIONS.get(c, "") for c in mbti_type if c in _MBTI_DESCRIPTIONS]
    base = f"Your MBTI type is **{mbti_type}**. Core traits: {', '.join(t for t in traits if t)}."

    open_answers = mbti_raw.get("open_answers", {})
    if open_answers.get("self_description"):
        base += f"\n자기소개: {open_answers['self_description']}"
    if open_answers.get("values"):
        base += f"\n핵심 가치관: {open_answers['values']}"
    if open_answers.get("stress_response"):
        base += f"\n스트레스 상황에서의 반응: {open_answers['stress_response']}"
    return base


def _describe_tone(sp: dict[str, Any]) -> str:
    tone = sp.get("tone", {})
    struct = sp.get("structure", {})
    humor = sp.get("humor", {})
    emojis = sp.get("emojis", {})

    formality = tone.get("formality", 0.5)
    warmth = tone.get("warmth", 0.5)
    directness = tone.get("directness", 0.5)

    formality_desc = "격식체(합니다/습니다)를 자주 씀" if formality > 0.5 else "비격식체(해/해요)를 선호함"
    warmth_desc = "따뜻하고 친근한 톤" if warmth > 0.5 else "차분하고 담백한 톤"
    directness_desc = "직접적이고 단호하게 말함" if directness > 0.6 else "질문을 많이 하며 대화를 열어둠"

    avg_len = struct.get("avg_message_length", 50)
    length_desc = (
        "짧고 간결하게 답변 (보통 한두 문장)" if avg_len < 40
        else "중간 길이로 답변 (2-4문장)" if avg_len < 120
        else "상세하게 길게 답변하는 편"
    )

    humor_style = humor.get("style", "none")
    humor_freq = humor.get("frequency", 0)
    if humor_style == "none" or humor_freq < 0.05:
        humor_desc = "유머를 거의 사용하지 않음"
    elif humor_style == "warm":
        humor_desc = f"따뜻하고 친근한 유머를 자주 사용 (빈도 {humor_freq:.0%})"
    elif humor_style == "sarcastic":
        humor_desc = "가끔 풍자적인 유머를 사용"
    elif humor_style == "self-deprecating":
        humor_desc = "자기 비하 유머를 사용하기도 함"
    else:
        humor_desc = f"건조하고 위트 있는 유머 (빈도 {humor_freq:.0%})"

    emoji_uses = emojis.get("uses_emojis", False)
    fav_emojis = emojis.get("favorites", [])
    emoji_desc = (
        f"이모지를 자주 사용 (자주 쓰는 이모지: {''.join(fav_emojis[:5])})" if emoji_uses and fav_emojis
        else "이모지를 가끔 사용" if emoji_uses
        else "이모지를 사용하지 않음"
    )

    return "\n".join([formality_desc, warmth_desc, directness_desc, length_desc, humor_desc, emoji_desc])


def _describe_vocabulary(sp: dict[str, Any]) -> str:
    vocab = sp.get("vocabulary", {})
    top = vocab.get("top_words", [])[:20]
    slang = vocab.get("slang", [])[:10]
    parts = []
    if top:
        parts.append(f"자주 쓰는 단어/표현: {', '.join(top)}")
    if slang:
        parts.append(f"자주 쓰는 슬랭/줄임말: {', '.join(slang)}")
    return "\n".join(parts)


def _describe_topics(sp: dict[str, Any]) -> str:
    topics = sp.get("topics", {})
    preferred = topics.get("preferred", [])[:10]
    avoided = topics.get("avoided", [])[:5]
    parts = []
    if preferred:
        parts.append(f"좋아하는 주제: {', '.join(preferred)}")
    if avoided:
        parts.append(f"잘 다루지 않는 주제: {', '.join(avoided)}")
    return "\n".join(parts)


def _feedback_rules(feedback_deltas: list[Any]) -> list[str]:
    """Convert accumulated feedback corrections into instruction lines."""
    rules = []
    for delta in feedback_deltas:
        if isinstance(delta, dict):
            aspect = delta.get("aspect", "")
            desired = delta.get("desired_behavior", "")
            if aspect and desired:
                rules.append(f"[피드백 교정 — {aspect}] {desired}")
    return rules


def build_system_prompt(person: "Person", few_shot_examples: list[dict[str, str]] | None = None) -> str:
    """
    Build the full 5-section system prompt for a person.

    `few_shot_examples` are injected as Section 5; if None, the examples
    stored in person.speech_patterns are used.
    """
    sp = person.speech_patterns or {}
    examples = few_shot_examples or sp.get("few_shot_examples", [])

    # --- Section 1: Identity Anchor ---
    career_lines = []
    for entry in (person.career_history or []):
        if isinstance(entry, dict):
            career_lines.append(
                f"  - {entry.get('role', '')} @ {entry.get('org', '')} ({entry.get('years', '')})"
            )
    career_str = "\n".join(career_lines) if career_lines else "  - (경력 정보 없음)"

    edu_lines = []
    for entry in (person.education or []):
        if isinstance(entry, dict):
            edu_lines.append(
                f"  - {entry.get('degree', '')} ({entry.get('institution', '')}, {entry.get('year', '')})"
            )
    edu_str = "\n".join(edu_lines) if edu_lines else "  - (학력 정보 없음)"

    interests_str = ", ".join(person.interests or []) or "(없음)"

    birth_info = f"{person.birth_year}년생" if person.birth_year else ""
    location_info = f"현재 {person.residence} 거주" if person.residence else ""
    identity_line = " | ".join(filter(None, [person.name, birth_info, location_info]))

    section1 = f"""## [1] 정체성 (Identity)
당신은 **{person.name}**입니다. {birth_info} {location_info}

### 경력
{career_str}

### 학력
{edu_str}

### 관심사
{interests_str}"""

    # --- Section 2: Personality Core ---
    mbti_desc = _describe_mbti(person.mbti_type, person.mbti_raw or {})
    section2 = f"""## [2] 성격 (Personality)
{mbti_desc if mbti_desc else "(성격 설문 미완료)"}"""

    # --- Section 3: Communication Style ---
    tone_desc = _describe_tone(sp)
    vocab_desc = _describe_vocabulary(sp)
    topics_desc = _describe_topics(sp)
    section3_parts = ["## [3] 커뮤니케이션 스타일 (Communication Style)"]
    if tone_desc:
        section3_parts.append(tone_desc)
    if vocab_desc:
        section3_parts.append(vocab_desc)
    if topics_desc:
        section3_parts.append(topics_desc)
    section3 = "\n".join(section3_parts)

    # --- Section 4: Behavioral Rules ---
    base_rules = [
        f"당신은 항상 **{person.name}**으로서 대화합니다. 절대 캐릭터를 벗어나지 마세요.",
        "AI임을 직접적으로 물어보지 않는 한 스스로를 AI라고 밝히지 마세요.",
        "상대방의 말투와 분위기에 맞게 자연스럽게 반응하세요.",
        "모르는 정보는 솔직하게 모른다고 하거나, 해당 인물이 알 법한 방식으로 추측하세요.",
    ]

    custom = [d for d in (person.custom_directions or []) if isinstance(d, str)]
    for d in custom:
        base_rules.append(f"[사용자 지정] {d}")

    fb_rules = _feedback_rules(person.feedback_deltas or [])
    all_rules = base_rules + fb_rules
    rules_str = "\n".join(f"- {r}" for r in all_rules)
    section4 = f"## [4] 행동 규칙 (Behavioral Rules)\n{rules_str}"

    # --- Section 5: Few-Shot Examples ---
    if examples:
        example_lines = ["## [5] 실제 대화 예시 (Few-Shot Examples)"]
        for ex in examples[:15]:
            example_lines.append(f'상대: {ex.get("user", "")}')
            example_lines.append(f'{person.name}: {ex.get("person", "")}')
            example_lines.append("")
        section5 = "\n".join(example_lines)
    else:
        section5 = f"## [5] 실제 대화 예시\n(채팅 로그를 업로드하면 실제 대화 예시가 여기에 추가됩니다)"

    header = (
        f"# AI 인격 클론 — {person.name}\n\n"
        "아래의 모든 정보를 바탕으로 해당 인물처럼 자연스럽게 대화하세요.\n"
        "존댓말/반말은 상황과 상대방에 맞게 자동으로 판단하세요.\n"
    )

    return "\n\n".join([header, section1, section2, section3, section4, section5])
