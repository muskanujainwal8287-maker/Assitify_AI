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
python start.py            # AI (:8000) + Backend (:8001) + Vite (:5173)
python start.py ai         # AI only
python start.py backend    # Backend only
python start.py frontend   # Vite frontend only
```

Open the student app at http://localhost:5173 (needs Node.js 20+).

## Auth

- `POST /api/auth/register` — `{ "email", "mobile_number", "password", "full_name?" }`
- `POST /api/auth/login` — `{ "email" }` or `{ "mobile_number" }` plus `"password"`
- `POST /api/auth/forgot-password` — `{ "email" }` sends a reset link; `{ "mobile_number" }` sends an OTP. Response includes `channel` (`email` | `sms`).
- `POST /api/auth/reset-password` — `{ "token", "new_password" }` for email links, or `{ "mobile_number", "otp", "new_password" }` for SMS OTP
- `GET /api/auth/me` — requires `Authorization: Bearer <token>`
- `PATCH /api/auth/me` — update `{ "email", "mobile_number", "full_name?" }`

Password reset emails are sent when `SMTP_HOST` is set. Without SMTP, the backend logs the reset link (useful for local development).

SMS OTP is sent when `SMS_PROVIDER` is set (`fast2sms` or `twilio`).
For Twilio **trial** accounts, set `TWILIO_VERIFY_SERVICE_SID` (Verify API) — free-form SMS bodies are blocked (error 572006).
Without a provider, the backend logs the OTP. Tokens/OTPs expire after `PASSWORD_RESET_EXPIRE_MINUTES` (default 15) and are single-use.

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
- `GET /api/documents/{document_id}/topic-keypoints` — requires `topic`
- `GET /api/documents/{document_id}/notes` — requires `chapter_id` (from GET .../chapters); optional `topic`
- `POST /api/documents/{document_id}/questions`
- `POST /api/documents/{document_id}/review`
- `POST /api/documents/{document_id}/doubt` — chatbot turn (`question`, optional `session_id` to continue)
- `POST /api/documents/{document_id}/doubt/sessions` — start a question-asking chat (tutor asks first)
- `GET /api/documents/{document_id}/doubt/sessions` — list chats (creates one if none exist)
- `GET /api/documents/{document_id}/doubt/sessions/{session_id}`
- `DELETE /api/documents/{document_id}/doubt/sessions/{session_id}`
- `GET /api/documents/{document_id}/chapters`
- `GET /api/documents/{document_id}/chunks`
- `GET /api/documents/{document_id}/attempts`
- `GET /api/documents/{document_id}/attempts/{attempt_id}`
- `GET /api/attempts/{attempt_id}`

Docs: http://127.0.0.1:8001/docs
