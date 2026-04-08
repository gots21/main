"""Unit tests for the chat log analyzer."""

import pytest
from app.services.chat_log_analyzer import analyze_chat_log, _parse_lines, _stage2_tone


KAKAO_SAMPLE = """
2024년 1월 5일 금요일
[오전 10:00] 지수 : 오늘 뭐 해?
[오전 10:01] 민준 : 그냥 집에 있어 ㅋㅋ
[오전 10:02] 지수 : 나도 심심한데 같이 카페 갈까?
[오전 10:03] 민준 : 좋아! 어디로?
[오전 10:04] 지수 : 강남역 근처 어때요
[오전 10:05] 민준 : 오케이 ㅋㅋ 1시 어때?
[오전 10:06] 지수 : 완전 좋아요 고마워!
[오전 10:07] 민준 : 그럼 이따 봐요 ㅋ
""".strip()


def test_parse_lines_kakao():
    pairs = _parse_lines(KAKAO_SAMPLE, format_hint="kakao")
    assert len(pairs) > 0
    senders = {name for name, _ in pairs}
    assert "민준" in senders
    assert "지수" in senders


def test_analyze_chat_log_returns_speech_patterns():
    result = analyze_chat_log(
        raw_text=KAKAO_SAMPLE,
        target_name="민준",
        format_hint="kakao",
    )
    assert "vocabulary" in result
    assert "tone" in result
    assert "structure" in result
    assert "humor" in result
    assert "emojis" in result
    assert "topics" in result
    assert "few_shot_examples" in result


def test_analyze_chat_log_unknown_target_raises():
    with pytest.raises(ValueError, match="No messages found"):
        analyze_chat_log(
            raw_text=KAKAO_SAMPLE,
            target_name="없는사람",
            format_hint="kakao",
        )


def test_tone_avg_message_length():
    messages = ["안녕하세요", "잘 지내셨나요?", "오늘 날씨가 참 좋네요"]
    tone = _stage2_tone(messages)
    assert "avg_message_length" in tone
    assert tone["avg_message_length"] > 0


def test_merge_with_existing_patterns():
    first = analyze_chat_log(KAKAO_SAMPLE, target_name="민준", format_hint="kakao")
    # Re-analyze with existing patterns — should merge without error
    second = analyze_chat_log(
        KAKAO_SAMPLE,
        target_name="민준",
        format_hint="kakao",
        existing_patterns=first,
    )
    assert "vocabulary" in second
    assert isinstance(second["few_shot_examples"], list)
