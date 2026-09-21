from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_owned_project
from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectList, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = Project(owner_id=user.id, **payload.model_dump())
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


@router.get("", response_model=ProjectList)
async def list_projects(
    skip: int = 0,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count_result = await db.execute(
        select(func.count()).select_from(Project).where(Project.owner_id == user.id)
    )
    total = count_result.scalar() or 0
    result = await db.execute(
        select(Project)
        .where(Project.owner_id == user.id)
        .order_by(Project.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    items = result.scalars().all()
    return ProjectList(items=items, total=total)


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_owned_project(db, project_id, user)


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: int,
    payload: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await get_owned_project(db, project_id, user)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    await db.flush()
    await db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await get_owned_project(db, project_id, user)
    await db.delete(project)
