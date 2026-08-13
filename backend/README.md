# Assitify Backend (BFF)

Product API that owns Postgres data, caches AI responses in Redis, and proxies compute to `ai_layer`.

## Run

1. Start infra: `docker compose up -d`
2. Install backend deps (same venv is fine):

```bash
pip install -r backend/requirements.txt
```

3. (Optional) apply migrations:

```bash
alembic upgrade head
```

4. Start services:

```bash
python start.py            # AI (:8000) + Backend (:8001)
python start.py ai         # AI only
python start.py backend    # Backend only
```

## Auth

- `POST /api/auth/register` — `{ "email", "mobile_number", "password", "full_name?" }`
- `POST /api/auth/login` — `{ "email" }` or `{ "mobile_number" }` plus `"password"`
- `GET /api/auth/me` — requires `Authorization: Bearer <token>`

Set `AUTH_REQUIRED=true` in `.env` to force login for document APIs.
When a user is logged in, documents are scoped to that user.

## Main endpoints

- `GET /health`
- `POST /api/documents/upload`
- `GET /api/documents`
- `GET /api/documents/{document_id}`
- `DELETE /api/documents/{document_id}`
- `GET /api/documents/{document_id}/summary`
- `GET /api/documents/{document_id}/keypoints`
- `POST /api/documents/{document_id}/questions`
- `POST /api/documents/{document_id}/review`
- `POST /api/documents/{document_id}/doubt`
- `GET /api/documents/{document_id}/chapters`
- `GET /api/documents/{document_id}/chunks`
- `GET /api/documents/{document_id}/attempts`
- `GET /api/documents/{document_id}/attempts/{attempt_id}`
- `GET /api/attempts/{attempt_id}`

Docs: http://127.0.0.1:8001/docs
