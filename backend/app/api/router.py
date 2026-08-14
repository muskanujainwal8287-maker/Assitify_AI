from fastapi import APIRouter

from backend.app.api.routes import auth, documents

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(documents.attempts_router)
