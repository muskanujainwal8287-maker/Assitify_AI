from unittest.mock import patch

from ai_layer.ai_service import AIService


LONG_ENOUGH = (
    "Photosynthesis is the process by which green plants convert sunlight into chemical energy. "
    "Chlorophyll absorbs light and drives the reaction that produces glucose and oxygen. "
    "Cellular respiration then releases energy stored in glucose for growth and repair. "
    "Mitochondria are the organelles where most ATP is generated during respiration. "
    "Water and carbon dioxide are the key inputs for the photosynthetic pathway."
)


def test_summary_sentence_buckets() -> None:
    assert AIService._summary_sentence_count_for_length(100) == 3
    assert AIService._summary_sentence_count_for_length(2000) == 5
    assert AIService._summary_sentence_count_for_length(8000) == 7
    assert AIService._summary_sentence_count_for_length(20000) == 10


def test_key_point_buckets() -> None:
    assert AIService._key_point_count_for_length(100) == 3
    assert AIService._key_point_count_for_length(2000) == 5


def test_pick_balanced_items() -> None:
    items = [f"s{i}" for i in range(10)]
    assert AIService._pick_balanced_items(items, 4) == ["s0", "s1", "s8", "s9"]
    assert AIService._pick_balanced_items(items, 0) == []
    assert AIService._pick_balanced_items(["only"], 3) == ["only"]


def test_prepare_content_truncates_middle() -> None:
    text = "A" * 1000 + "MIDDLE" + "B" * 1000
    prepared = AIService._prepare_content_for_prompt(text, limit=200)
    assert "middle content omitted" in prepared
    assert prepared.startswith("A")
    assert prepared.endswith("B")
    assert len(prepared) < len(text)


def test_fallback_summary_and_keypoints() -> None:
    summary = AIService._fallback_summary(LONG_ENOUGH, sentence_count=2)
    assert isinstance(summary, str) and summary
    points = AIService._fallback_key_points(LONG_ENOUGH, count=3)
    assert len(points) == 3
    topic_points = AIService._fallback_topic_key_points(LONG_ENOUGH, topic="photosynthesis", count=2)
    assert topic_points
    assert any("photosynthesis" in p.lower() or "chlorophyll" in p.lower() for p in topic_points)


def test_fallback_notes_nested_shape() -> None:
    sections = [
        {
            "title": "Chapter 1 Plants",
            "chapter_id": "ch-1",
            "chapter_number": 1,
            "text": LONG_ENOUGH,
        }
    ]
    chapters = AIService._fallback_notes(sections, topic=None)
    assert len(chapters) == 1
    assert chapters[0].chapter_id == "ch-1"
    assert chapters[0].topics
    assert chapters[0].topics[0].notes


def test_fallback_notes_topic_filter() -> None:
    sections = [
        {"title": "Animals", "chapter_number": 1, "text": "Animals move and eat food daily."},
        {"title": "Plants", "chapter_number": 2, "text": LONG_ENOUGH},
    ]
    chapters = AIService._fallback_notes(sections, topic="photosynthesis")
    assert len(chapters) == 1
    assert chapters[0].title == "Plants"


def test_fallback_questions_objective() -> None:
    questions = AIService._fallback_questions(
        LONG_ENOUGH,
        question_type="objective",
        difficulty="easy",
        count=2,
        topic="biology",
    )
    assert len(questions) == 2
    assert questions[0].options
    assert questions[0].topic == "biology"


def test_format_chat_history() -> None:
    block = AIService._format_chat_history(
        [
            {"role": "user", "content": "What is ATP?"},
            {"role": "assistant", "content": "Energy currency."},
        ]
    )
    assert "Student: What is ATP?" in block
    assert "Tutor: Energy currency." in block


def test_fallback_session_opener() -> None:
    opener = AIService._fallback_session_opener(LONG_ENOUGH)
    assert "study" in opener.lower()
    assert "explain" in opener.lower()
    assert "Photosynthesis" in opener


def test_summarize_uses_fallback_when_llm_fails() -> None:
    with patch.object(AIService, "_summarize_with_llm", return_value=(None, "no key")):
        result = AIService.summarize(LONG_ENOUGH)
    assert result.source == "fallback"
    assert result.data


def test_generate_notes_uses_fallback_when_llm_fails() -> None:
    sections = [{"title": "Ch1", "chapter_id": "c1", "chapter_number": 1, "text": LONG_ENOUGH}]
    with patch.object(AIService, "_generate_notes_with_llm", return_value=(None, "boom")):
        result = AIService.generate_notes(sections)
    assert result.source == "fallback"
    assert result.data[0].topics[0].notes


def test_answer_doubt_fallback_on_llm_error() -> None:
    with patch("ai_layer.ai_service.call_llm", return_value=(None, "OPENAI_API_KEY is not set")):
        result = AIService.answer_doubt(LONG_ENOUGH, "Explain chlorophyll")
    assert result.source == "fallback"
    assert "OPENAI_API_KEY" in result.data


def test_start_doubt_session_fallback() -> None:
    with patch("ai_layer.ai_service.call_llm", return_value=(None, "down")):
        result = AIService.start_doubt_session(LONG_ENOUGH)
    assert result.source == "fallback"
    assert "Hi!" in result.data
