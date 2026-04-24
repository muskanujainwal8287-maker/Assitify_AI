import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure top-level ai_layer is importable when running from backend/.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.routes import docs, generate, test
from app.core.config import settings

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(docs.router, prefix="/api/docs", tags=["docs"])
app.include_router(generate.router, prefix="/api/generate", tags=["generate"])
app.include_router(test.router, prefix="/api/test", tags=["test"])


@app.get("/")
def health_check() -> dict:
    return {"status": "ok", "message": f"{settings.app_name} running"}
