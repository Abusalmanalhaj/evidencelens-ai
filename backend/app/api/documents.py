import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_owned_project
from app.auth.dependencies import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.document import Document, DocumentStatus
from app.models.project import AnalysisStatus
from app.models.user import User
from app.schemas.document import DocumentOut
from app.services.analysis_service import process_document_extraction

router = APIRouter(prefix="/projects/{project_id}/documents", tags=["documents"])
settings = get_settings()


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    project_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await get_owned_project(db, project_id, user)

    if file.content_type != "application/pdf" and not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are accepted")

    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.max_upload_size_mb}MB limit",
        )
    if len(content) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    upload_dir = Path(settings.upload_dir) / str(project_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = upload_dir / safe_name
    file_path.write_bytes(content)

    document = Document(
        project_id=project_id,
        filename=file.filename or safe_name,
        file_path=str(file_path),
        file_size=len(content),
        mime_type="application/pdf",
        status=DocumentStatus.UPLOADED.value,
    )
    db.add(document)
    project.analysis_status = AnalysisStatus.EXTRACTING.value
    await db.flush()

    await process_document_extraction(db, document)
    if document.status == DocumentStatus.FAILED.value:
        project.analysis_status = AnalysisStatus.FAILED.value
        project.error_message = document.error_message
    elif document.status == DocumentStatus.EXTRACTED.value:
        project.analysis_status = AnalysisStatus.PENDING.value
    await db.flush()
    return document


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    project_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_owned_project(db, project_id, user)
    result = await db.execute(
        select(Document).where(Document.project_id == project_id).order_by(Document.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    project_id: int,
    document_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_owned_project(db, project_id, user)
    doc = await db.get(Document, document_id)
    if not doc or doc.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc


@router.post("/{document_id}/retry-extraction", response_model=DocumentOut)
async def retry_extraction(
    project_id: int,
    document_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-run extraction for documents stuck in processing or failed state."""
    project = await get_owned_project(db, project_id, user)
    doc = await db.get(Document, document_id)
    if not doc or doc.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    project.analysis_status = AnalysisStatus.EXTRACTING.value
    await process_document_extraction(db, doc)
    if doc.status == DocumentStatus.FAILED.value:
        project.analysis_status = AnalysisStatus.FAILED.value
        project.error_message = doc.error_message
    elif doc.status == DocumentStatus.EXTRACTED.value:
        project.analysis_status = AnalysisStatus.PENDING.value
        project.error_message = None
    await db.flush()
    return doc
