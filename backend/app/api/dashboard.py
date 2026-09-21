from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_owned_project
from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardMetrics
from app.services.dashboard_service import get_dashboard_metrics

router = APIRouter(prefix="/projects/{project_id}/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardMetrics)
async def dashboard(
    project_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_owned_project(db, project_id, user)
    return await get_dashboard_metrics(db, project_id)
