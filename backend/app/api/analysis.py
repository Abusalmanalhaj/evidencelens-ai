from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_owned_project
from app.auth.dependencies import get_current_user
from app.config import get_settings
from app.database import async_session_factory, get_db
from app.models.analysis_run import AnalysisRun
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.schemas.analysis import AnalysisRunOut, AnalysisStart, AnalysisStatusOut
from app.services.analysis_service import run_project_analysis

router = APIRouter(prefix="/projects/{project_id}/analysis", tags=["analysis"])
settings = get_settings()


async def _run_analysis_background(project_id: int, document_id: int, api_key: str | None = None) -> None:
    async with async_session_factory() as db:
        try:
            await run_project_analysis(db, project_id, document_id, api_key=api_key)
            await db.commit()
        except Exception:
            await db.rollback()
            raise


@router.post("/run", response_model=AnalysisRunOut, status_code=status.HTTP_202_ACCEPTED)
async def start_analysis(
    project_id: int,
    payload: AnalysisStart,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_owned_project(db, project_id, user)
    document = await db.get(Document, payload.document_id)
    if (
        not document
        or document.project_id != project_id
        or document.status != DocumentStatus.EXTRACTED.value
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Choose an extracted document before starting analysis",
        )
    api_key = payload.api_key.get_secret_value() if payload.api_key else None
    background_tasks.add_task(_run_analysis_background, project_id, payload.document_id, api_key)
    run = AnalysisRun(project_id=project_id, status="pending")
    db.add(run)
    await db.flush()
    await db.refresh(run)
    return run


@router.get("/status", response_model=AnalysisStatusOut)
async def analysis_status(
    project_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await get_owned_project(db, project_id, user)
    result = await db.execute(
        select(AnalysisRun)
        .where(AnalysisRun.project_id == project_id)
        .order_by(AnalysisRun.created_at.desc())
        .limit(1)
    )
    current_run = result.scalar_one_or_none()
    return AnalysisStatusOut(
        project_id=project_id,
        analysis_status=project.analysis_status,
        current_run=current_run,
        llm_enabled=settings.llm_enabled,
    )


@router.get("/runs", response_model=list[AnalysisRunOut])
async def list_runs(
    project_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_owned_project(db, project_id, user)
    result = await db.execute(
        select(AnalysisRun)
        .where(AnalysisRun.project_id == project_id)
        .order_by(AnalysisRun.created_at.desc())
    )
    return result.scalars().all()
