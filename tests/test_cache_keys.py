from backend.app.services import cache as document_cache


def test_cache_key_helpers() -> None:
    assert document_cache.summary_key("d1") == "assitify:bff:summary:d1"
    assert document_cache.keypoints_key("d1") == "assitify:bff:keypoints:d1"
    assert document_cache.topic_keypoints_key("d1", topic=" Photosynthesis ") == (
        "assitify:bff:topic-keypoints:d1:photosynthesis"
    )
    assert document_cache.notes_key("d1", chapter_id=" ch-1 ", topic=None) == (
        "assitify:bff:notes:d1:ch-1:_"
    )
    assert document_cache.notes_key("d1", chapter_id="ch-1", topic="Roots") == (
        "assitify:bff:notes:d1:ch-1:roots"
    )
