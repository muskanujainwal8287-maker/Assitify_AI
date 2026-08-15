from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.models import Attempt, AttemptAnswer, Document, DoubtMessage, DoubtSession, Question, User
from backend.app.schemas import (
    AnswerReviewOut,
    AttemptDetailResponse,
    AttemptListItem,
    AttemptListResponse,
    ChunkInfo,
    ChapterInfo,
    DocumentChaptersResponse,
    DocumentChunksResponse,
    DocumentDetailResponse,
    DocumentListItem,
    DocumentListResponse,
    DocumentUploadResponse,
    DoubtResponse,
    DoubtSessionDetailResponse,
    DoubtSessionListItem,
    DoubtSessionListResponse,
    ChatMessageOut,
    KeyPointsResponse,
    NotesResponse,
    QuestionGenerationRequest,
    QuestionGenerationResponse,
    QuestionOut,
    ChapterNotes,
    SummaryResponse,
    TestReviewRequest,
    TestReviewResponse,
    TopicKeyPointsResponse,
    WeakTopicOut,
)
from backend.app.services import cache as document_cache
from backend.app.services.ai_client import ai_client


def _ensure_ai_document(document: Document) -> None:
    """Upsert document into AI-layer store so compute works after AI restarts."""
    ai_client.restore_document(
        document_id=str(document.id),
        filename=document.filename,
        detected_type=document.detected_type,
        text=document.text,
    )


def _get_document_or_404(
    db: Session,
    document_id: UUID,
    user: User | None = None,
) -> Document:
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    if user is not None and document.user_id is not None and document.user_id != user.id:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document


def upload_document(
    db: Session,
    *,
    filename: str | None = None,
    content: bytes | None = None,
    content_type: str | None = None,
    text: str | None = None,
    user: User | None = None,
) -> DocumentUploadResponse:
    has_file = bool(filename) and content is not None and len(content) > 0
    has_text = bool(text and text.strip())
    if not has_file and not has_text:
        raise HTTPException(status_code=400, detail="Provide file, text, or both.")

    cleaned_text = text.strip() if text else None

    ai_result = ai_client.upload(
        filename=filename,
        content=content,
        content_type=content_type,
        text=cleaned_text,
    )

    document_id = UUID(ai_result["document_id"])
    full_text = ai_result.get("extracted_text") or ai_result.get("extracted_text_preview") or ""
    if not full_text.strip():
        raise HTTPException(status_code=422, detail="AI layer returned empty document text.")

    document = Document(
        id=document_id,
        user_id=user.id if user else None,
        filename=ai_result.get("filename") or filename or "pasted_text.txt",
        detected_type=ai_result.get("detected_type") or "text/plain",
        text=full_text,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    return DocumentUploadResponse(
        document_id=document.id,
        filename=document.filename,
        detected_type=document.detected_type,
        extracted_text_preview=full_text[:500],
    )


def list_documents(db: Session, user: User | None = None) -> DocumentListResponse:
    query = (
        select(
            Document,
            func.count(Question.id).label("question_count"),
        )
        .outerjoin(Question, Question.document_id == Document.id)
        .group_by(Document.id)
        .order_by(Document.created_at.desc())
    )
    if user is not None:
        query = query.where(Document.user_id == user.id)

    rows = db.execute(query).all()

    items = [
        DocumentListItem(
            document_id=doc.id,
            filename=doc.filename,
            detected_type=doc.detected_type,
            created_at=doc.created_at,
            question_count=int(count or 0),
        )
        for doc, count in rows
    ]
    return DocumentListResponse(documents=items, total=len(items))


def get_document(
    db: Session,
    document_id: UUID,
    user: User | None = None,
) -> DocumentDetailResponse:
    document = _get_document_or_404(db, document_id, user)
    question_attempted_count = db.scalar(
        select(func.count(AttemptAnswer.id))
        .select_from(AttemptAnswer)
        .join(Attempt, AttemptAnswer.attempt_id == Attempt.id)
        .where(Attempt.document_id == document.id)
    )
    attempt_count = db.scalar(
        select(func.count(Attempt.id)).where(Attempt.document_id == document.id)
    )
    return DocumentDetailResponse(
        document_id=document.id,
        filename=document.filename,
        detected_type=document.detected_type,
        created_at=document.created_at,
        text_preview=document.text[:500],
        text_length=len(document.text),
        question_attempted_count=int(question_attempted_count or 0),
        attempt_count=int(attempt_count or 0),
    )


def delete_document(
    db: Session,
    document_id: UUID,
    user: User | None = None,
) -> dict[str, str]:
    document = _get_document_or_404(db, document_id, user)
    db.delete(document)
    db.commit()
    document_cache.delete_document_cache(str(document_id))
    try:
        ai_client.delete_document(str(document_id))
    except HTTPException:
        # AI-layer copy may already be gone after restart; Postgres delete still succeeds.
        pass
    return {"status": "deleted", "document_id": str(document_id)}


def get_summary(
    db: Session,
    document_id: UUID,
    user: User | None = None,
) -> SummaryResponse:
    document = _get_document_or_404(db, document_id, user)
    cache_key = document_cache.summary_key(str(document.id))
    cached = document_cache.get_json(cache_key)
    if isinstance(cached, dict) and cached.get("summary"):
        return SummaryResponse(
            document_id=document.id,
            summary=cached["summary"],
            source=cached.get("source", "fallback"),
            llm_error=cached.get("llm_error"),
            fallback_reason=cached.get("fallback_reason") or "redis_cache",
        )

    _ensure_ai_document(document)
    result = ai_client.summary(str(document.id))
    response = SummaryResponse(
        document_id=document.id,
        summary=result["summary"],
        source=result.get("source", "fallback"),
        llm_error=result.get("llm_error"),
        fallback_reason=result.get("fallback_reason"),
    )
    document_cache.set_json(cache_key, response.model_dump(mode="json"))
    return response


def get_keypoints(
    db: Session,
    document_id: UUID,
    user: User | None = None,
) -> KeyPointsResponse:
    document = _get_document_or_404(db, document_id, user)
    cache_key = document_cache.keypoints_key(str(document.id))
    cached = document_cache.get_json(cache_key)
    if isinstance(cached, dict) and "key_points" in cached:
        return KeyPointsResponse(
            document_id=document.id,
            key_points=cached.get("key_points") or [],
            source=cached.get("source", "fallback"),
            llm_error=cached.get("llm_error"),
            fallback_reason=cached.get("fallback_reason") or "redis_cache",
        )

    _ensure_ai_document(document)
    result = ai_client.keypoints(str(document.id))
    response = KeyPointsResponse(
        document_id=document.id,
        key_points=result.get("key_points") or [],
        source=result.get("source", "fallback"),
        llm_error=result.get("llm_error"),
        fallback_reason=result.get("fallback_reason"),
    )
    document_cache.set_json(cache_key, response.model_dump(mode="json"))
    return response


def get_topic_keypoints(
    db: Session,
    document_id: UUID,
    *,
    topic: str,
    user: User | None = None,
) -> TopicKeyPointsResponse:
    document = _get_document_or_404(db, document_id, user)
    chosen_topic = topic.strip()
    cache_key = document_cache.topic_keypoints_key(str(document.id), topic=chosen_topic)
    cached = document_cache.get_json(cache_key)
    if isinstance(cached, dict) and "key_points" in cached:
        return TopicKeyPointsResponse(
            document_id=document.id,
            topic=cached.get("topic") or chosen_topic,
            key_points=cached.get("key_points") or [],
            source=cached.get("source", "fallback"),
            llm_error=cached.get("llm_error"),
            fallback_reason=cached.get("fallback_reason") or "redis_cache",
        )

    _ensure_ai_document(document)
    result = ai_client.topic_keypoints(str(document.id), topic=chosen_topic)
    response = TopicKeyPointsResponse(
        document_id=document.id,
        topic=result.get("topic") or chosen_topic,
        key_points=result.get("key_points") or [],
        source=result.get("source", "fallback"),
        llm_error=result.get("llm_error"),
        fallback_reason=result.get("fallback_reason"),
    )
    document_cache.set_json(cache_key, response.model_dump(mode="json"))
    return response


def get_notes(
    db: Session,
    document_id: UUID,
    *,
    chapter_id: str,
    topic: str | None = None,
    user: User | None = None,
) -> NotesResponse:
    document = _get_document_or_404(db, document_id, user)
    cache_key = document_cache.notes_key(
        str(document.id),
        chapter_id=chapter_id,
        topic=topic,
    )
    cached = document_cache.get_json(cache_key)
    if isinstance(cached, dict) and cached.get("chapters"):
        return NotesResponse(
            document_id=document.id,
            chapters=[ChapterNotes(**item) for item in cached.get("chapters") or []],
            source=cached.get("source", "fallback"),
            llm_error=cached.get("llm_error"),
            fallback_reason=cached.get("fallback_reason") or "redis_cache",
        )

    _ensure_ai_document(document)
    result = ai_client.notes(
        str(document.id),
        chapter_id=chapter_id,
        topic=topic,
    )
    response = NotesResponse(
        document_id=document.id,
        chapters=[ChapterNotes(**item) for item in (result.get("chapters") or [])],
        source=result.get("source", "fallback"),
        llm_error=result.get("llm_error"),
        fallback_reason=result.get("fallback_reason"),
    )
    document_cache.set_json(cache_key, response.model_dump(mode="json"))
    return response


def generate_questions(
    db: Session,
    document_id: UUID,
    payload: QuestionGenerationRequest,
    user: User | None = None,
) -> QuestionGenerationResponse:
    document = _get_document_or_404(db, document_id, user)
    cache_key = document_cache.questions_key(
        str(document.id),
        question_type=payload.question_type,
        difficulty=payload.difficulty,
        count=payload.count,
        topic=payload.topic,
    )
    cached = document_cache.get_json(cache_key)
    if isinstance(cached, dict) and cached.get("questions"):
        # Still refresh Postgres quiz set from cache so review works.
        existing = db.scalars(select(Question).where(Question.document_id == document.id)).all()
        for item in existing:
            db.delete(item)
        questions_out = [QuestionOut(**item) for item in cached["questions"]]
        for item in questions_out:
            db.add(
                Question(
                    document_id=document.id,
                    external_id=item.id,
                    prompt=item.prompt,
                    question_type=item.question_type,
                    options=item.options or [],
                    answer=item.answer,
                    difficulty=item.difficulty,
                    topic=item.topic or "General",
                )
            )
        db.commit()
        return QuestionGenerationResponse(
            document_id=document.id,
            questions=questions_out,
            source=cached.get("source", "fallback"),
            llm_error=cached.get("llm_error"),
            fallback_reason=cached.get("fallback_reason") or "redis_cache",
        )

    _ensure_ai_document(document)

    result = ai_client.questions(
        {
            "document_id": str(document.id),
            "topic": payload.topic,
            "question_type": payload.question_type,
            "difficulty": payload.difficulty,
            "count": payload.count,
        }
    )

    existing = db.scalars(select(Question).where(Question.document_id == document.id)).all()
    for item in existing:
        db.delete(item)

    questions_out: list[QuestionOut] = []
    for item in result.get("questions") or []:
        external_id = item["id"]
        db.add(
            Question(
                document_id=document.id,
                external_id=external_id,
                prompt=item["prompt"],
                question_type=item["question_type"],
                options=item.get("options") or [],
                answer=item["answer"],
                difficulty=item["difficulty"],
                topic=item.get("topic") or "General",
            )
        )
        questions_out.append(
            QuestionOut(
                id=external_id,
                prompt=item["prompt"],
                question_type=item["question_type"],
                options=item.get("options") or [],
                answer=item["answer"],
                difficulty=item["difficulty"],
                topic=item.get("topic") or "General",
            )
        )

    db.commit()
    response = QuestionGenerationResponse(
        document_id=document.id,
        questions=questions_out,
        source=result.get("source", "fallback"),
        llm_error=result.get("llm_error"),
        fallback_reason=result.get("fallback_reason"),
    )
    document_cache.set_json(cache_key, response.model_dump(mode="json"))
    return response


def review_test(
    db: Session,
    document_id: UUID,
    payload: TestReviewRequest,
    user: User | None = None,
) -> TestReviewResponse:
    document = _get_document_or_404(db, document_id, user)
    questions = db.scalars(select(Question).where(Question.document_id == document.id)).all()
    if not questions:
        raise HTTPException(status_code=404, detail="No generated questions found for this document.")

    _ensure_ai_document(document)

    ai_questions = [
        {
            "id": q.external_id,
            "prompt": q.prompt,
            "question_type": q.question_type,
            "options": q.options or [],
            "answer": q.answer,
            "difficulty": q.difficulty,
            "topic": q.topic,
        }
        for q in questions
    ]

    result = ai_client.review(
        {
            "document_id": str(document.id),
            "answers": [item.model_dump() for item in payload.answers],
            "questions": ai_questions,
        }
    )

    weak_topics = result.get("weak_topics") or []
    attempt = Attempt(
        document_id=document.id,
        total_score=float(result.get("total_score") or 0),
        recommended_difficulty=result.get("recommended_difficulty") or "hard",
        source=result.get("source") or "fallback",
        scoring_source=result.get("scoring_source") or "fallback",
        weak_topics=weak_topics,
    )
    db.add(attempt)
    db.flush()

    reviews_out: list[AnswerReviewOut] = []
    for item in result.get("reviews") or []:
        db.add(
            AttemptAnswer(
                attempt_id=attempt.id,
                question_external_id=item["question_id"],
                user_answer=item["user_answer"],
                expected_answer=item["expected_answer"],
                is_correct=bool(item["is_correct"]),
                score=float(item["score"]),
                explanation=item.get("explanation") or "",
                topic=item.get("topic") or "General",
            )
        )
        reviews_out.append(AnswerReviewOut(**item))

    db.commit()
    db.refresh(attempt)

    return TestReviewResponse(
        document_id=document.id,
        attempt_id=attempt.id,
        total_score=attempt.total_score,
        reviews=reviews_out,
        weak_topics=[WeakTopicOut(**topic) for topic in weak_topics if isinstance(topic, dict)],
        recommended_difficulty=attempt.recommended_difficulty,
        source=result.get("source") or "fallback",
        scoring_source=result.get("scoring_source") or "fallback",
        weak_topics_source=result.get("weak_topics_source") or "fallback",
        llm_error=result.get("llm_error"),
        fallback_reason=result.get("fallback_reason"),
    )


def resolve_doubt(
    db: Session,
    document_id: UUID,
    question: str,
    user: User | None = None,
    session_id: UUID | None = None,
) -> DoubtResponse:
    document = _get_document_or_404(db, document_id, user)
    session = _get_or_create_doubt_session(db, document, user, session_id)
    history_rows = db.scalars(
        select(DoubtMessage)
        .where(DoubtMessage.session_id == session.id)
        .order_by(DoubtMessage.created_at.asc())
    ).all()
    history = [{"role": row.role, "content": row.content} for row in history_rows[-10:]]

    _ensure_ai_document(document)
    result = ai_client.doubt(
        {
            "document_id": str(document.id),
            "question": question,
            "history": history,
        }
    )
    answer = result["answer"]

    db.add(DoubtMessage(session_id=session.id, role="user", content=question))
    db.add(DoubtMessage(session_id=session.id, role="assistant", content=answer))
    if session.title == "Doubt chat":
        session.title = question[:80]
    session.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)

    messages = db.scalars(
        select(DoubtMessage)
        .where(DoubtMessage.session_id == session.id)
        .order_by(DoubtMessage.created_at.asc())
    ).all()
    return DoubtResponse(
        document_id=document.id,
        session_id=session.id,
        question=question,
        answer=answer,
        messages=[
            ChatMessageOut(role=item.role, content=item.content, created_at=item.created_at)
            for item in messages
        ],
        source=result.get("source", "fallback"),
        llm_error=result.get("llm_error"),
        fallback_reason=result.get("fallback_reason"),
    )


def _get_or_create_doubt_session(
    db: Session,
    document: Document,
    user: User | None,
    session_id: UUID | None,
) -> DoubtSession:
    if session_id is not None:
        session = db.get(DoubtSession, session_id)
        if (
            not session
            or session.document_id != document.id
            or (user is not None and session.user_id is not None and session.user_id != user.id)
        ):
            raise HTTPException(status_code=404, detail="Doubt session not found.")
        return session

    session = DoubtSession(
        document_id=document.id,
        user_id=user.id if user else None,
        title="Doubt chat",
    )
    db.add(session)
    db.flush()
    return session


def create_doubt_session(
    db: Session,
    document_id: UUID,
    user: User | None = None,
    *,
    title: str | None = None,
) -> DoubtSessionDetailResponse:
    document = _get_document_or_404(db, document_id, user)
    _ensure_ai_document(document)
    opener = ai_client.start_doubt(str(document.id))
    opening_message = (opener.get("message") or "").strip() or (
        "Hi! Let's study this material together. What would you like to start with?"
    )

    session = DoubtSession(
        document_id=document.id,
        user_id=user.id if user else None,
        title=(title or "").strip() or "Question session",
    )
    db.add(session)
    db.flush()
    db.add(DoubtMessage(session_id=session.id, role="assistant", content=opening_message))
    session.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)

    return get_doubt_session(db, document_id, session.id, user)


def list_doubt_sessions(
    db: Session,
    document_id: UUID,
    user: User | None = None,
) -> DoubtSessionListResponse:
    document = _get_document_or_404(db, document_id, user)
    items = _list_doubt_session_items(db, document, user)
    if not items:
        created = create_doubt_session(db, document_id, user)
        items = [
            DoubtSessionListItem(
                session_id=created.session_id,
                document_id=created.document_id,
                title=created.title,
                message_count=0,
                created_at=created.created_at,
                updated_at=created.updated_at,
            )
        ]
    return DoubtSessionListResponse(document_id=document.id, sessions=items, total=len(items))


def _list_doubt_session_items(
    db: Session,
    document: Document,
    user: User | None,
) -> list[DoubtSessionListItem]:
    query = (
        select(
            DoubtSession,
            func.count(DoubtMessage.id).label("message_count"),
        )
        .outerjoin(DoubtMessage, DoubtMessage.session_id == DoubtSession.id)
        .where(DoubtSession.document_id == document.id)
        .group_by(DoubtSession.id)
        .order_by(DoubtSession.updated_at.desc())
    )
    if user is not None:
        query = query.where(DoubtSession.user_id == user.id)
    rows = db.execute(query).all()
    return [
        DoubtSessionListItem(
            session_id=session.id,
            document_id=session.document_id,
            title=session.title,
            message_count=int(count or 0),
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
        for session, count in rows
    ]


def get_doubt_session(
    db: Session,
    document_id: UUID,
    session_id: UUID,
    user: User | None = None,
) -> DoubtSessionDetailResponse:
    document = _get_document_or_404(db, document_id, user)
    session = db.get(DoubtSession, session_id)
    if (
        not session
        or session.document_id != document.id
        or (user is not None and session.user_id is not None and session.user_id != user.id)
    ):
        raise HTTPException(status_code=404, detail="Doubt session not found.")

    messages = db.scalars(
        select(DoubtMessage)
        .where(DoubtMessage.session_id == session.id)
        .order_by(DoubtMessage.created_at.asc())
    ).all()
    return DoubtSessionDetailResponse(
        session_id=session.id,
        document_id=session.document_id,
        title=session.title,
        messages=[
            ChatMessageOut(role=item.role, content=item.content, created_at=item.created_at)
            for item in messages
        ],
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def delete_doubt_session(
    db: Session,
    document_id: UUID,
    session_id: UUID,
    user: User | None = None,
) -> dict[str, str]:
    document = _get_document_or_404(db, document_id, user)
    session = db.get(DoubtSession, session_id)
    if (
        not session
        or session.document_id != document.id
        or (user is not None and session.user_id is not None and session.user_id != user.id)
    ):
        raise HTTPException(status_code=404, detail="Doubt session not found.")
    db.delete(session)
    db.commit()
    return {"status": "deleted", "session_id": str(session_id)}


def get_chapters(
    db: Session,
    document_id: UUID,
    user: User | None = None,
) -> DocumentChaptersResponse:
    document = _get_document_or_404(db, document_id, user)
    _ensure_ai_document(document)
    result = ai_client.chapters(str(document.id))
    return DocumentChaptersResponse(
        document_id=document.id,
        total_chapters=int(result.get("total_chapters") or 0),
        chapters=[ChapterInfo(**item) for item in (result.get("chapters") or [])],
    )


def get_chunks(
    db: Session,
    document_id: UUID,
    *,
    chapter_id: str | None = None,
    limit: int = 50,
    user: User | None = None,
) -> DocumentChunksResponse:
    document = _get_document_or_404(db, document_id, user)
    _ensure_ai_document(document)
    result = ai_client.chunks(str(document.id), chapter_id=chapter_id, limit=limit)
    return DocumentChunksResponse(
        document_id=document.id,
        total_chunks=int(result.get("total_chunks") or 0),
        chunks=[ChunkInfo(**item) for item in (result.get("chunks") or [])],
    )


def list_attempts(
    db: Session,
    document_id: UUID,
    user: User | None = None,
) -> AttemptListResponse:
    document = _get_document_or_404(db, document_id, user)
    rows = db.execute(
        select(
            Attempt,
            func.count(AttemptAnswer.id).label("answer_count"),
        )
        .outerjoin(AttemptAnswer, AttemptAnswer.attempt_id == Attempt.id)
        .where(Attempt.document_id == document.id)
        .group_by(Attempt.id)
        .order_by(Attempt.created_at.desc())
    ).all()

    items = [
        AttemptListItem(
            attempt_id=attempt.id,
            document_id=attempt.document_id,
            total_score=attempt.total_score,
            recommended_difficulty=attempt.recommended_difficulty,
            source=attempt.source,
            scoring_source=attempt.scoring_source,
            weak_topics=attempt.weak_topics or [],
            created_at=attempt.created_at,
            answer_count=int(count or 0),
        )
        for attempt, count in rows
    ]
    return AttemptListResponse(document_id=document.id, attempts=items, total=len(items))


def get_attempt(
    db: Session,
    document_id: UUID,
    attempt_id: UUID,
    user: User | None = None,
) -> AttemptDetailResponse:
    document = _get_document_or_404(db, document_id, user)
    attempt = db.get(Attempt, attempt_id)
    if not attempt or attempt.document_id != document.id:
        raise HTTPException(status_code=404, detail="Attempt not found.")

    answers = db.scalars(
        select(AttemptAnswer)
        .where(AttemptAnswer.attempt_id == attempt.id)
        .order_by(AttemptAnswer.id.asc())
    ).all()

    reviews = [
        AnswerReviewOut(
            question_id=answer.question_external_id,
            expected_answer=answer.expected_answer,
            user_answer=answer.user_answer,
            is_correct=answer.is_correct,
            score=answer.score,
            explanation=answer.explanation,
            topic=answer.topic,
        )
        for answer in answers
    ]
    return AttemptDetailResponse(
        attempt_id=attempt.id,
        document_id=attempt.document_id,
        total_score=attempt.total_score,
        recommended_difficulty=attempt.recommended_difficulty,
        source=attempt.source,
        scoring_source=attempt.scoring_source,
        weak_topics=attempt.weak_topics or [],
        created_at=attempt.created_at,
        reviews=reviews,
    )


def get_attempt_by_id(
    db: Session,
    attempt_id: UUID,
    user: User | None = None,
) -> AttemptDetailResponse:
    attempt = db.get(Attempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found.")
    return get_attempt(db, attempt.document_id, attempt_id, user)
