# AI Layer

This repository README describes the `ai_layer` only.

The AI layer provides three core services:

- document parsing (`PDF`, `DOCX`, `TXT`, and images)
- summary and question generation
- answer review, weak-topic detection, and difficulty recommendation

## Folder Structure

- `ai_layer/parser_service.py`
  - Parses supported file formats into plain text.
- `ai_layer/ai_service.py`
  - Generates summaries and objective/subjective questions.
- `ai_layer/evaluation_service.py`
  - Scores answers and returns feedback with weak-topic insights.
- `ai_layer/__init__.py`
  - Package exports.

## Features

- Parse documents from:
  - `application/pdf` and `.pdf`
  - `.docx` and `.doc`
  - image files (`.png`, `.jpg`, `.jpeg`, `.webp`) via OCR
  - plain text files
- Generate summaries in three modes:
  - `short`
  - `standard`
  - `detailed`
- Generate:
  - objective questions with options
  - subjective questions with free-text expected answers
- Review submitted answers:
  - per-question score and feedback
  - weak-topic list
  - recommended next difficulty (`easy`, `medium`, `hard`)

## Dependencies

Install the Python dependencies used by the AI layer:

```bash
pip install python-docx PyMuPDF Pillow pytesseract
```

### OCR Requirement

Install the Tesseract OCR engine and ensure `tesseract` is available in your system `PATH`.

## Service Overview

### `ParserService`

- `parse(file_path, content_type) -> (text, doc_type)`
- Detects file type from content type or extension.
- Routes parsing to:
  - `_parse_pdf`
  - `_parse_docx`
  - `_parse_image`
  - plain text reader fallback

### `AIService`

- `summarize(text, mode) -> (summary, key_points)`
  - sentence-based summary selection by mode
  - key points from frequent terms
- `generate_questions(text, question_type, difficulty, count, topic=None) -> list[Question]`
  - supports `objective` and `subjective` generation
  - attaches metadata (`id`, `difficulty`, `topic`)

### `EvaluationService`

- `review_answers(answers, expected) -> (reviews, total_score, weak_topics, recommended_difficulty)`
- Internal behavior:
  - token-overlap scoring
  - correctness threshold at `0.6`
  - weak-topic accuracy sorting
  - difficulty recommendation from total score

## Typical AI Layer Flow

1. Parse uploaded file into text.
2. Generate summary and key points.
3. Generate questions from parsed text.
4. Review user answers against expected answers.
5. Return scores, weak topics, and next difficulty.
