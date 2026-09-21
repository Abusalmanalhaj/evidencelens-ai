from datetime import datetime

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: int
    project_id: int
    filename: str
    file_size: int
    mime_type: str
    page_count: int | None
    status: str
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
