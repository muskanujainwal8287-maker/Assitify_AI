import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from backend.app.api.router import api_router
from backend.app.core.config import settings
from backend.app.db.session import init_db
from backend.app.services.ai_client import ai_client

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

_PUBLIC_PATHS = {
    "/",
    "/health",
    "/api/auth/login",
    "/api/auth/register",
}

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    swagger_ui_parameters={"persistAuthorization": True},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


def custom_openapi() -> dict:
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )
    components = openapi_schema.setdefault("components", {})
    schemes = components.setdefault("securitySchemes", {})
    schemes["JWT"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Paste access_token from /api/auth/login or /register. Do not type Bearer.",
    }
    for path, operations in openapi_schema.get("paths", {}).items():
        if path in _PUBLIC_PATHS:
            continue
        for operation in operations.values():
            if isinstance(operation, dict):
                operation["security"] = [{"JWT": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/")
def health_check() -> dict:
    return {"status": "ok", "service": "backend", "message": f"{settings.app_name} running"}


@app.get("/health")
def health() -> dict:
    ai_status: dict = {"reachable": False}
    try:
        ai_status = {"reachable": True, **ai_client.health()}
    except Exception as exc:  # noqa: BLE001
        ai_status = {"reachable": False, "error": str(exc)}

    return {
        "status": "ok",
        "database_configured": bool(settings.database_url),
        "ai_layer_url": settings.ai_layer_url,
        "ai": ai_status,
    }
