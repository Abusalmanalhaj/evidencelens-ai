from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    sector: str | None = None
    stage: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    sector: str | None = None
    stage: str | None = None


class ProjectOut(BaseModel):
    id: int
    name: str
    description: str | None
    sector: str | None
    stage: str | None
    analysis_status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectList(BaseModel):
    items: list[ProjectOut]
    total: int
