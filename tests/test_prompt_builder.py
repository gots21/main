"""Unit tests for the system prompt builder."""

from unittest.mock import MagicMock

import pytest

from app.services.prompt_builder import build_system_prompt, _describe_tone, _describe_mbti


def _make_person(**kwargs) -> MagicMock:
    """Create a mock Person with sensible defaults."""
    defaults = {
        "name": "김민준",
        "birth_year": 1990,
        "residence": "서울",
        "career_history": [{"role": "개발자", "org": "Kakao", "years": "2018-2022"}],
        "education": [{"degree": "컴공학사", "institution": "서울대학교", "year": 2014}],
        "interests": ["축구", "독서", "여행"],
        "mbti_type": "INTJ",
        "mbti_raw": {
            "open_answers": {
                "self_description": "분석적이고 조용한 편",
                "values": "효율과 정직",
                "stress_response": "혼자만의 시간이 필요함",
            }
        },
        "speech_patterns": {
            "tone": {"formality": 0.2, "warmth": 0.6, "directness": 0.7},
            "structure": {"avg_message_length": 35, "uses_lists": False, "uses_questions": True},
            "humor": {"style": "warm", "frequency": 0.25},
            "emojis": {"uses_emojis": True, "favorites": ["ㅋ", "😊"]},
            "vocabulary": {"top_words": ["그냥", "진짜", "좋아"], "rare_words": [], "slang": ["ㅋㅋ"]},
            "topics": {"preferred": ["기술", "축구"], "avoided": []},
            "few_shot_examples": [{"user": "오늘 뭐 해?", "person": "그냥 집에 있어 ㅋㅋ"}],
        },
        "feedback_deltas": [],
        "custom_directions": ["말투는 항상 반말로"],
    }
    defaults.update(kwargs)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


def test_build_system_prompt_contains_name():
    person = _make_person()
    prompt = build_system_prompt(person)
    assert "김민준" in prompt


def test_build_system_prompt_contains_career():
    person = _make_person()
    prompt = build_system_prompt(person)
    assert "Kakao" in prompt
    assert "개발자" in prompt


def test_build_system_prompt_contains_mbti():
    person = _make_person()
    prompt = build_system_prompt(person)
    assert "INTJ" in prompt


def test_build_system_prompt_contains_custom_direction():
    person = _make_person()
    prompt = build_system_prompt(person)
    assert "반말" in prompt


def test_build_system_prompt_contains_few_shot():
    person = _make_person()
    prompt = build_system_prompt(person)
    assert "오늘 뭐 해?" in prompt


def test_build_system_prompt_dynamic_examples_override():
    person = _make_person()
    dynamic = [{"user": "취미가 뭐야?", "person": "축구 좋아해"}]
    prompt = build_system_prompt(person, few_shot_examples=dynamic)
    assert "취미가 뭐야?" in prompt


def test_describe_tone_low_formality():
    sp = {
        "tone": {"formality": 0.1, "warmth": 0.8, "directness": 0.7},
        "structure": {"avg_message_length": 30, "uses_lists": False, "uses_questions": False},
        "humor": {"style": "warm", "frequency": 0.4},
        "emojis": {"uses_emojis": True, "favorites": ["😊"]},
    }
    desc = _describe_tone(sp)
    assert "비격식체" in desc


def test_describe_mbti_no_type():
    result = _describe_mbti(None, {})
    assert result == ""


def test_describe_mbti_with_type():
    result = _describe_mbti("ENFP", {})
    assert "ENFP" in result
