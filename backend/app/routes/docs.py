import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import settings
from app.schemas.docs import DocumentUploadResponse
from app.services.storage import StoredDocument, store
from ai_layer.parser_service import ParserService

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)) -> DocumentUploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    upload_directory = Path(settings.upload_dir)
    upload_directory.mkdir(parents=True, exist_ok=True)
    document_id = str(uuid.uuid4())
    file_path = upload_directory / f"{document_id}_{file.filename}"

    content = await file.read()
    file_path.write_bytes(content)

    parsed_text, detected_type = ParserService.parse(file_path=file_path, content_type=file.content_type or "")
    if not parsed_text:
        raise HTTPException(status_code=422, detail="Could not extract text from the uploaded file.")

    store.documents[document_id] = StoredDocument(
        id=document_id, filename=file.filename, detected_type=detected_type, text=parsed_text
    )
    return DocumentUploadResponse(
        document_id=document_id,
        filename=file.filename,
        detected_type=detected_type,
        extracted_text_preview=parsed_text[:500],
    )
