import logging
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy import inspect
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import analysis, auth, claims, dashboard, documents, projects, reports
from app.config import get_settings
from app.database import Base, engine
from app.logging_config import setup_logging
from app.models import (  # noqa: F401 — register models with Base.metadata
    AnalysisRun,
    Assessment,
    Claim,
    Document,
    Evidence,
    Project,
    ReviewFeedback,
    User,
)

setup_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


def _ensure_sqlite_audit_columns(connection) -> None:
    additions = {
        "claims": {
            "source_pages": "JSON",
            "claim_basis": "VARCHAR(32)",
            "claim_kind": "VARCHAR(32)",
        },
        "assessments": {
            "evidence_relevance": "FLOAT",
            "evidence_sufficiency": "FLOAT",
            "evidence_pages": "JSON",
            "source_page_verified": "BOOLEAN",
            "verification_status": "VARCHAR(32)",
        },
    }
    inspector = inspect(connection)
    for table, columns in additions.items():
        existing = {column["name"] for column in inspector.get_columns(table)}
        for name, column_type in columns.items():
            if name not in existing:
                connection.exec_driver_sql(
                    f"ALTER TABLE {table} ADD COLUMN {name} {column_type}"
                )
    connection.exec_driver_sql(
        "UPDATE assessments SET evidence_relevance = 0 WHERE evidence_relevance IS NULL"
    )
    connection.exec_driver_sql(
        "UPDATE assessments SET evidence_sufficiency = 0 WHERE evidence_sufficiency IS NULL"
    )
    connection.exec_driver_sql(
        "UPDATE assessments SET source_page_verified = 0 WHERE source_page_verified IS NULL"
    )
    connection.exec_driver_sql(
        "UPDATE assessments SET verification_status = 'deck_only' WHERE verification_status IS NULL"
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    if settings.uses_sqlite:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(_ensure_sqlite_audit_columns)
        logger.info("SQLite database initialized at ./evidencelens.db")
    logger.info(
        "EvidenceLens AI started (db=sqlite, llm=%s)" if settings.uses_sqlite
        else "EvidenceLens AI started (db=postgres, llm=%s)",
        settings.llm_enabled,
    )
    yield


app = FastAPI(
    title="EvidenceLens AI",
    description="AI-powered startup technical due diligence platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(auth.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(claims.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "llm_enabled": settings.llm_enabled,
    }
