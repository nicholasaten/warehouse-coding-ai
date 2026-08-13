from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine
from app.routers import (
    auth,
    config,
    dashboard,
    locations,
    merge_suggestions,
    raw_import,
    recommendations,
    revisions,
    uploads,
    users,
    warehouses,
)

app = FastAPI(title="AI Warehouse Layout & Coding Management System API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(config.router)
app.include_router(warehouses.router)
app.include_router(locations.router)
app.include_router(uploads.router)
app.include_router(merge_suggestions.router)
app.include_router(dashboard.router)
app.include_router(recommendations.router)
app.include_router(users.router)
app.include_router(revisions.router)
app.include_router(raw_import.router)


@app.get("/health")
def health() -> dict:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
