# AI Layer

This README documents the current `ai_layer` implementation in this repository.

## Python Version

Use `Python 3.12.x` for this project.
`PyMuPDF` may fail to install on Windows with `Python 3.14` because pip may fall back to source builds.

## What It Provides

The AI layer supports:

- document upload and parsing (`PDF`, `DOCX`, `TXT`, image OCR)
- chapter/chunk ingestion for phase-1 retrieval readiness
- summary generation (`short`, `standard`, `detailed`)
- key-point recommendation
- objective/subjective question generation
- answer review with weak-topic detection and next difficulty recommendation
- doubt answering grounded in provided document/text

## Folder Structure

- `ai_layer/main.py`
  - FastAPI app setup and router registration.
- `ai_layer/api_router.py`
  - REST endpoints for upload, summary, keypoints, questions, review, doubt, chapters, and chunks.
- `ai_layer/parser_service.py`
  - Parses supported file formats into plain text.
- `ai_layer/ingestion_service.py`
  - Splits documents into chapter-like segments and overlapping chunks.
- `ai_layer/ai_service.py`
  - LLM-backed summary, key-point, question, and doubt logic with local fallbacks.
- `ai_layer/evaluation_service.py`
  - LLM-backed answer scoring/weak-topic analysis with heuristic fallback.
- `ai_layer/storage.py`
  - In-memory storage models (`StoredDocument`, chapters, chunks, generated questions).
- `ai_layer/schemas.py`
  - Request/response models used by API routes.
- `ai_layer/config.py`
  - Environment-backed settings (upload dir, OpenAI key, model, etc.).
- `start.py`
  - Convenience launcher for `uvicorn ai_layer.main:app --reload`.

## Dependencies

Create and activate a virtual environment with Python 3.12, then install dependencies:

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### OCR Requirement

Install the Tesseract OCR engine and ensure `tesseract` is available in system `PATH`.

## Configuration

The app reads settings from environment variables (via `.env`):

- `OPENAI_API_KEY` - enables LLM features.
- `LLM_MODEL` - model passed to OpenAI responses API.
- `UPLOAD_DIR` - upload storage directory (default: `uploads`).
- `ALLOW_ORIGINS` - CORS origin list.

If `OPENAI_API_KEY` is missing, services use local fallback logic where implemented.

## API Endpoints

All routes below are exposed from the AI router:

- `POST /upload`
  - Uploads a file, parses text, stores the document, and runs ingestion.
- `POST /summary`
  - Input: `document_id` or raw `text` + `mode`.
  - Output: generated summary.
- `POST /keypoints`
  - Input: `document_id` or raw `text` + `count`.
  - Output: recommended key points.
- `POST /questions`
  - Input: `document_id` or raw `text`, `question_type`, `difficulty`, `count`, optional `topic`.
  - Output: generated question set.
- `POST /review`
  - Input: `document_id` + submitted answers.
  - Output: per-question review, total score, weak topics, recommended difficulty.
- `POST /doubt`
  - Input: `document_id` or raw `text` + user `question`.
  - Output: AI-generated doubt response.
- `GET /documents/{document_id}/chapters`
  - Output: chapter boundaries and chunk counts.
- `GET /documents/{document_id}/chunks?chapter_id=<id>&limit=50`
  - Output: chunk metadata and text preview (optionally filtered by chapter).

## Request Pattern

Most content-generation endpoints accept either:

- a previously uploaded `document_id`, or
- direct `text` input (min length `20`, max length `50000`).

If direct text is provided, a temporary in-memory document is created and ingested.

## Service Notes

### `ParserService`

- Detects input type from MIME type/extension.
- Supports:
  - PDF via `fitz` (PyMuPDF)
  - DOCX via `python-docx`
  - image OCR via `Pillow` + `pytesseract`
  - plain text fallback

### `IngestionService`

- Detects chapter-like headings using regex.
- Creates `StoredChapter` entries with start/end character spans.
- Builds overlapping chunks (`chunk_size=1200`, `overlap=200` by default).

### `AIService`

- Uses OpenAI Responses API when configured.
- Includes fallback behavior for:
  - summary generation
  - key-point extraction
  - question generation
- Doubt answering currently requires OpenAI key for meaningful responses.

### `EvaluationService`

- Uses LLM scoring when available, otherwise token-overlap heuristic.
- Correctness threshold is `0.6` score.
- Computes weak-topic suggestions and recommended next difficulty (`easy`, `medium`, `hard`).

## Typical Flow

1. Upload document via `/upload`.
2. Use `document_id` for `/summary`, `/keypoints`, and `/questions`.
3. Submit answers to `/review`.
4. Use `/doubt` for targeted follow-up explanations.
5. Inspect chapter/chunk structure via `/documents/{id}/chapters` and `/documents/{id}/chunks`.
