from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_owned_project
from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.report_service import generate_report_pdf

router = APIRouter(prefix="/projects/{project_id}/reports", tags=["reports"])


@router.get("/download")
async def download_report(
    project_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_owned_project(db, project_id, user)
    try:
        pdf_bytes = await generate_report_pdf(db, project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="evidencelens-report-{project_id}.pdf"'},
    )
