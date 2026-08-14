from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.api.routes import documents as documents_routes
from backend.app.schemas import (
    ChapterNotes,
    ChatMessageOut,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentUploadResponse,
    DoubtResponse,
    DoubtSessionDetailResponse,
    DoubtSessionListItem,
    DoubtSessionListResponse,
    KeyPointsResponse,
    NotesResponse,
    TopicKeyPointsResponse,
    TopicNotes,
)


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock()
    monkeypatch.setattr(documents_routes, "document_service", mock)
    return mock


def test_list_documents(documents_client: TestClient, service: MagicMock) -> None:
    service.list_documents.return_value = DocumentListResponse(documents=[], total=0)
    response = documents_client.get("/api/documents")
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_get_document(documents_client: TestClient, service: MagicMock) -> None:
    doc_id = uuid4()
    service.get_document.return_value = DocumentDetailResponse(
        document_id=doc_id,
        filename="notes.txt",
        detected_type="text/plain",
        created_at=datetime.now(timezone.utc),
        text_preview="hello",
        text_length=5,
    )
    response = documents_client.get(f"/api/documents/{doc_id}")
    assert response.status_code == 200
    assert response.json()["filename"] == "notes.txt"


def test_notes_requires_chapter_id(documents_client: TestClient, service: MagicMock) -> None:
    doc_id = uuid4()
    response = documents_client.get(f"/api/documents/{doc_id}/notes")
    assert response.status_code == 422
    service.get_notes.assert_not_called()


def test_notes_with_chapter_id(documents_client: TestClient, service: MagicMock) -> None:
    doc_id = uuid4()
    service.get_notes.return_value = NotesResponse(
        document_id=doc_id,
        chapters=[
            ChapterNotes(
                title="Chapter 1",
                chapter_id="ch-1",
                chapter_number=1,
                topics=[TopicNotes(topic="Overview", notes=["Point A"])],
            )
        ],
        source="fallback",
    )
    response = documents_client.get(f"/api/documents/{doc_id}/notes", params={"chapter_id": "1"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["chapters"][0]["topics"][0]["notes"] == ["Point A"]
    service.get_notes.assert_called_once()
    kwargs = service.get_notes.call_args.kwargs
    assert kwargs["chapter_id"] == "1"


def test_topic_keypoints_requires_topic(documents_client: TestClient, service: MagicMock) -> None:
    doc_id = uuid4()
    response = documents_client.get(f"/api/documents/{doc_id}/topic-keypoints")
    assert response.status_code == 422


def test_topic_keypoints_ok(documents_client: TestClient, service: MagicMock) -> None:
    doc_id = uuid4()
    service.get_topic_keypoints.return_value = TopicKeyPointsResponse(
        document_id=doc_id,
        topic="photosynthesis",
        key_points=["Light reaction happens in thylakoids."],
        source="fallback",
    )
    response = documents_client.get(
        f"/api/documents/{doc_id}/topic-keypoints",
        params={"topic": "photosynthesis"},
    )
    assert response.status_code == 200
    assert response.json()["topic"] == "photosynthesis"


def test_keypoints(documents_client: TestClient, service: MagicMock) -> None:
    doc_id = uuid4()
    service.get_keypoints.return_value = KeyPointsResponse(
        document_id=doc_id,
        key_points=["A useful study point here."],
        source="fallback",
    )
    response = documents_client.get(f"/api/documents/{doc_id}/keypoints")
    assert response.status_code == 200
    assert len(response.json()["key_points"]) == 1


def test_doubt_ask(documents_client: TestClient, service: MagicMock) -> None:
    doc_id = uuid4()
    session_id = uuid4()
    now = datetime.now(timezone.utc)
    service.resolve_doubt.return_value = DoubtResponse(
        document_id=doc_id,
        session_id=session_id,
        question="What is chlorophyll?",
        answer="A pigment. What role does it play?",
        messages=[
            ChatMessageOut(role="user", content="What is chlorophyll?", created_at=now),
            ChatMessageOut(role="assistant", content="A pigment. What role does it play?", created_at=now),
        ],
        source="fallback",
    )
    response = documents_client.post(
        f"/api/documents/{doc_id}/doubt",
        json={"question": "What is chlorophyll?"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["session_id"] == str(session_id)


def test_doubt_sessions_list(documents_client: TestClient, service: MagicMock) -> None:
    doc_id = uuid4()
    now = datetime.now(timezone.utc)
    service.list_doubt_sessions.return_value = DoubtSessionListResponse(
        document_id=doc_id,
        sessions=[
            DoubtSessionListItem(
                session_id=uuid4(),
                document_id=doc_id,
                title="Session 1",
                message_count=1,
                created_at=now,
                updated_at=now,
            )
        ],
        total=1,
    )
    response = documents_client.get(f"/api/documents/{doc_id}/doubt/sessions")
    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_doubt_session_detail(documents_client: TestClient, service: MagicMock) -> None:
    doc_id = uuid4()
    session_id = uuid4()
    now = datetime.now(timezone.utc)
    service.get_doubt_session.return_value = DoubtSessionDetailResponse(
        session_id=session_id,
        document_id=doc_id,
        title="Session 1",
        messages=[ChatMessageOut(role="assistant", content="Hi?", created_at=now)],
        created_at=now,
        updated_at=now,
    )
    response = documents_client.get(f"/api/documents/{doc_id}/doubt/sessions/{session_id}")
    assert response.status_code == 200
    assert response.json()["messages"][0]["role"] == "assistant"


def test_upload_text_only(documents_client: TestClient, service: MagicMock) -> None:
    doc_id = uuid4()
    service.upload_document.return_value = DocumentUploadResponse(
        document_id=doc_id,
        filename="pasted.txt",
        detected_type="text/plain",
        extracted_text_preview="hello world",
    )
    response = documents_client.post(
        "/api/documents/upload",
        data={"text": "hello world"},
    )
    assert response.status_code == 200, response.text
    service.upload_document.assert_called_once()
