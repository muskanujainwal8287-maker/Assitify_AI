from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai_layer.api_router import router as ai_router
from ai_layer.config import settings

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai_router, prefix="/api/ai", tags=["ai-layer"])


@app.get("/")
def health_check() -> dict:
    return {"status": "ok", "message": f"{settings.app_name} running"}
