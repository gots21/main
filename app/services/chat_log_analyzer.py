"""
Chat Log Analyzer — 6-stage pipeline that extracts personality signals from raw chat logs.

Supports KakaoTalk, WhatsApp, iMessage export formats (auto-detected).
Output is a `speech_patterns` dict that can be stored in Person.speech_patterns.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

# ---------------------------------------------------------------------------
# Format parsers
# ---------------------------------------------------------------------------

_KAKAO_RE = re.compile(
    r"^\d{4}년 \d{1,2}월 \d{1,2}일.+\n?"  # date header (optional)
    r"|^(?P<time>\[.+?\]) (?P<name>.+?) : (?P<msg>.+)$",
    re.MULTILINE,
)
_KAKAO_MSG_RE = re.compile(r"^\[.+?\] (?P<name>.+?) : (?P<msg>.+)$")

_WHATSAPP_RE = re.compile(
    r"^\d{1,2}/\d{1,2}/\d{2,4},? \d{1,2}:\d{2}(?::\d{2})?(?: [AP]M)? - (?P<name>.+?): (?P<msg>.+)$",
    re.MULTILINE,
)

_IMESSAGE_RE = re.compile(
    r"^(?P<name>.+?)\t(?:\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\t(?P<msg>.+)$",
    re.MULTILINE,
)

_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002500-\U00002BEF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE,
)


def _parse_lines(raw_text: str, format_hint: str = "auto") -> list[tuple[str, str]]:
    """Return list of (sender_name, message) tuples."""
    pairs: list[tuple[str, str]] = []

    if format_hint == "kakao" or (format_hint == "auto" and _KAKAO_MSG_RE.search(raw_text)):
        for m in _KAKAO_MSG_RE.finditer(raw_text):
            pairs.append((m.group("name").strip(), m.group("msg").strip()))
        return pairs

    if format_hint == "whatsapp" or (format_hint == "auto" and _WHATSAPP_RE.search(raw_text)):
        for m in _WHATSAPP_RE.finditer(raw_text):
            pairs.append((m.group("name").strip(), m.group("msg").strip()))
        return pairs

    if format_hint == "imessage" or (format_hint == "auto" and _IMESSAGE_RE.search(raw_text)):
        for m in _IMESSAGE_RE.finditer(raw_text):
            pairs.append((m.group("name").strip(), m.group("msg").strip()))
        return pairs

    # Fallback: treat every non-empty line as a message from an unknown sender
    for line in raw_text.splitlines():
        line = line.strip()
        if line:
            pairs.append(("unknown", line))
    return pairs


# ---------------------------------------------------------------------------
# Stage implementations
# ---------------------------------------------------------------------------

_KOREAN_LAUGH_RE = re.compile(r"[ㅋㅎ]{2,}")
_FORMAL_WORD_RE = re.compile(r"습니다|입니다|합니다|드립니다|드립니다")
_WARMTH_RE = re.compile(r"친구|고마워|감사|사랑|ㅠ|ㅜ|ㅋ|ㅎ|:D|😊|❤")


def _stage1_vocabulary(messages: list[str]) -> dict[str, Any]:
    tokens: list[str] = []
    for msg in messages:
        # Strip emojis and punctuation, keep Korean/Latin chars
        cleaned = _EMOJI_RE.sub("", msg)
        tokens.extend(re.findall(r"[\w가-힣]+", cleaned))

    freq = Counter(tokens)
    total = sum(freq.values()) or 1
    top_words = [w for w, _ in freq.most_common(50) if len(w) > 1]
    # Slang: words appearing ≥5 times that are short (≤3 chars) and Korean
    slang = [w for w, c in freq.items() if c >= 5 and 1 < len(w) <= 3 and re.match(r"[가-힣]+", w)]

    return {"top_words": top_words, "rare_words": [], "slang": slang[:20], "_freq": dict(freq.most_common(200))}


def _stage2_tone(messages: list[str]) -> dict[str, Any]:
    lengths = [len(m) for m in messages]
    avg_len = sum(lengths) / len(lengths) if lengths else 0

    formal_count = sum(1 for m in messages if _FORMAL_WORD_RE.search(m))
    warmth_count = sum(1 for m in messages if _WARMTH_RE.search(m))
    question_count = sum(1 for m in messages if "?" in m or "？" in m)
    list_count = sum(1 for m in messages if re.search(r"^\d+\.", m, re.MULTILINE))

    n = len(messages) or 1
    return {
        "formality": round(formal_count / n, 3),
        "warmth": round(min(warmth_count / n, 1.0), 3),
        "directness": round(1 - question_count / n, 3),
        "avg_message_length": round(avg_len),
        "uses_lists": list_count > 2,
        "uses_questions": question_count / n > 0.15,
    }


def _stage3_humor(messages: list[str]) -> dict[str, Any]:
    laugh_count = sum(1 for m in messages if _KOREAN_LAUGH_RE.search(m))
    self_deprec = sum(1 for m in messages if re.search(r"나도 모르겠|나 바보|내가 왜|어쩌지", m))
    sarcasm = sum(1 for m in messages if re.search(r"진짜|물론|당연하지|그렇겠지", m))

    n = len(messages) or 1
    freq = round(laugh_count / n, 3)

    if freq > 0.3:
        style = "warm"
    elif sarcasm / n > 0.1:
        style = "sarcastic"
    elif self_deprec > 2:
        style = "self-deprecating"
    elif freq > 0.05:
        style = "dry"
    else:
        style = "none"

    return {"style": style, "frequency": freq}


def _stage4_emojis_topics(messages: list[str]) -> dict[str, Any]:
    all_emojis: list[str] = []
    for m in messages:
        all_emojis.extend(_EMOJI_RE.findall(m))

    emoji_freq = Counter(all_emojis)
    top_emojis = [e for e, _ in emoji_freq.most_common(10)]

    # Simple keyword extraction for topics
    topic_words: list[str] = []
    for m in messages:
        cleaned = _EMOJI_RE.sub("", m)
        words = re.findall(r"[가-힣]{2,}", cleaned)
        topic_words.extend(w for w in words if len(w) >= 2)

    topic_freq = Counter(topic_words)
    preferred = [w for w, _ in topic_freq.most_common(20)]

    return {
        "uses_emojis": len(all_emojis) > 0,
        "favorites": top_emojis,
        "preferred": preferred[:15],
        "avoided": [],
    }


def _stage5_few_shot(
    all_pairs: list[tuple[str, str]], target_name: str, max_examples: int = 15
) -> list[dict[str, str]]:
    """Extract Q&A pairs where a non-target message is followed by the target's response."""
    examples: list[dict[str, str]] = []
    for i in range(1, len(all_pairs)):
        prev_name, prev_msg = all_pairs[i - 1]
        curr_name, curr_msg = all_pairs[i]
        if curr_name == target_name and prev_name != target_name:
            if 5 < len(curr_msg) < 300 and 3 < len(prev_msg) < 200:
                examples.append({"user": prev_msg, "person": curr_msg})
    # Prefer mid-length responses (more representative)
    examples.sort(key=lambda x: abs(len(x["person"]) - 50))
    return examples[:max_examples]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_chat_log(
    raw_text: str,
    target_name: str,
    format_hint: str = "auto",
    existing_patterns: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Run all 6 stages and return a `speech_patterns` dict.

    If `existing_patterns` is provided, new signals are merged using a
    weighted average (existing weight=0.6, new weight=0.4).
    """
    all_pairs = _parse_lines(raw_text, format_hint)
    target_messages = [msg for name, msg in all_pairs if name == target_name]

    if not target_messages:
        raise ValueError(
            f"No messages found for '{target_name}'. "
            "Check target_name matches the sender name in the log."
        )

    vocab = _stage1_vocabulary(target_messages)
    tone = _stage2_tone(target_messages)
    humor = _stage3_humor(target_messages)
    emoji_topics = _stage4_emojis_topics(target_messages)
    few_shots = _stage5_few_shot(all_pairs, target_name)

    new_patterns: dict[str, Any] = {
        "vocabulary": {
            "top_words": vocab["top_words"],
            "rare_words": vocab["rare_words"],
            "slang": vocab["slang"],
        },
        "tone": {
            "formality": tone["formality"],
            "warmth": tone["warmth"],
            "directness": tone["directness"],
        },
        "structure": {
            "avg_message_length": tone["avg_message_length"],
            "uses_lists": tone["uses_lists"],
            "uses_questions": tone["uses_questions"],
        },
        "humor": humor,
        "emojis": {
            "uses_emojis": emoji_topics["uses_emojis"],
            "favorites": emoji_topics["favorites"],
        },
        "topics": {
            "preferred": emoji_topics["preferred"],
            "avoided": emoji_topics["avoided"],
        },
        "few_shot_examples": few_shots,
    }

    if not existing_patterns:
        return new_patterns

    return _merge_patterns(existing_patterns, new_patterns)


def _merge_patterns(
    existing: dict[str, Any], new: dict[str, Any], w_old: float = 0.6, w_new: float = 0.4
) -> dict[str, Any]:
    """Weighted merge of two speech_patterns dicts."""

    def _merge_float(a: float, b: float) -> float:
        return round(a * w_old + b * w_new, 3)

    def _merge_lists(a: list, b: list, limit: int = 30) -> list:
        seen = set()
        merged = []
        for item in list(a) + list(b):
            if item not in seen:
                seen.add(item)
                merged.append(item)
        return merged[:limit]

    return {
        "vocabulary": {
            "top_words": _merge_lists(
                existing.get("vocabulary", {}).get("top_words", []),
                new["vocabulary"]["top_words"],
            ),
            "rare_words": _merge_lists(
                existing.get("vocabulary", {}).get("rare_words", []),
                new["vocabulary"]["rare_words"],
            ),
            "slang": _merge_lists(
                existing.get("vocabulary", {}).get("slang", []),
                new["vocabulary"]["slang"],
            ),
        },
        "tone": {
            "formality": _merge_float(
                existing.get("tone", {}).get("formality", new["tone"]["formality"]),
                new["tone"]["formality"],
            ),
            "warmth": _merge_float(
                existing.get("tone", {}).get("warmth", new["tone"]["warmth"]),
                new["tone"]["warmth"],
            ),
            "directness": _merge_float(
                existing.get("tone", {}).get("directness", new["tone"]["directness"]),
                new["tone"]["directness"],
            ),
        },
        "structure": {
            "avg_message_length": int(
                _merge_float(
                    existing.get("structure", {}).get("avg_message_length", new["structure"]["avg_message_length"]),
                    new["structure"]["avg_message_length"],
                )
            ),
            "uses_lists": new["structure"]["uses_lists"],
            "uses_questions": new["structure"]["uses_questions"],
        },
        "humor": {
            "style": new["humor"]["style"],
            "frequency": _merge_float(
                existing.get("humor", {}).get("frequency", new["humor"]["frequency"]),
                new["humor"]["frequency"],
            ),
        },
        "emojis": {
            "uses_emojis": new["emojis"]["uses_emojis"] or existing.get("emojis", {}).get("uses_emojis", False),
            "favorites": _merge_lists(
                existing.get("emojis", {}).get("favorites", []),
                new["emojis"]["favorites"],
                limit=10,
            ),
        },
        "topics": {
            "preferred": _merge_lists(
                existing.get("topics", {}).get("preferred", []),
                new["topics"]["preferred"],
            ),
            "avoided": _merge_lists(
                existing.get("topics", {}).get("avoided", []),
                new["topics"]["avoided"],
            ),
        },
        "few_shot_examples": (
            existing.get("few_shot_examples", []) + new["few_shot_examples"]
        )[:20],
    }
