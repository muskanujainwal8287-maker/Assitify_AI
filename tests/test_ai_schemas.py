from ai_layer.schemas import ChapterNotes, TopicNotes


def test_chapter_notes_model_nested() -> None:
    chapter = ChapterNotes(
        title="Ch1",
        chapter_id="abc",
        chapter_number=1,
        topics=[TopicNotes(topic="Intro", notes=["Point one", "Point two"])],
    )
    dumped = chapter.model_dump()
    assert dumped["topics"][0]["notes"] == ["Point one", "Point two"]
