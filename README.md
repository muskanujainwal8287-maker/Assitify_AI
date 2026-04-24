# AI Exam Prep Platform

End-to-end project for exam preparation with 3 layers:

- AI layer: summary + question generation + answer evaluation
- Backend layer (FastAPI): upload, parsing, generation, scoring APIs
- Frontend layer (React + Vite): student workflow UI

## Features

- Upload and parse `PDF`, `DOCX`, `TXT`, and images (`PNG`, `JPG`, `WEBP`)
- OCR for image notes (via `pytesseract`)
- Summary generation (`short`, `standard`, `detailed`)
- Objective and subjective test creation
- Answer review with score and AI feedback
- Weak topic detection + recommended next difficulty

## Project Structure

- `ai_layer/`
  - `parser_service.py`, `ai_service.py`, `evaluation_service.py`
- `backend/`
  - `app/routes/` API routers (`docs`, `generate`, `test`)
  - `app/services/` backend storage/service glue
  - `app/schemas/` request/response models
- `frontend/`
  - `src/App.jsx` complete exam prep workflow UI
  - `src/services/api.js` API integration layer

## Backend Setup

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend runs on `http://127.0.0.1:8000`.

### OCR requirement

Install Tesseract OCR engine on your machine and ensure it is available in PATH.

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`.

## API Flow

1. `POST /api/docs/upload` -> parse file and create `document_id`
2. `POST /api/generate/summary` -> generate summary and key points
3. `POST /api/generate/questions` -> generate objective/subjective questions
4. `POST /api/test/review` -> evaluate answers, score, weak topics

## Next Improvements

- Replace local generation with OpenAI/Gemini/Llama models
- Add PostgreSQL persistence for users/tests history
- Add adaptive test engine based on previous attempts
