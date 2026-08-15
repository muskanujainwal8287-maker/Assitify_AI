# Assitify frontend

React + TypeScript + Vite student app. It talks to the FastAPI backend on `http://127.0.0.1:8001`.

## Run

Install [Node.js 20+](https://nodejs.org/) if needed.

**Recommended** — from the repo root (starts AI, backend, and Vite):

```bash
docker compose up -d
python start.py
```

Open http://localhost:5173

**Frontend only:**

```bash
python start.py frontend
# or
cd frontend
npm install
npm run dev
```

Vite proxies `/api` to port 8001.

## Scripts

- `npm run dev` — local app
- `npm run build` — production bundle
- `npm run preview` — serve the production bundle
