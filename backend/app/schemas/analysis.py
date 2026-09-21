from datetime import datetime

from pydantic import BaseModel, Field, SecretStr


class AnalysisStart(BaseModel):
    document_id: int = Field(description="Extracted document to analyze")
    api_key: SecretStr | None = Field(
        default=None,
        min_length=20,
        max_length=512,
        description="Optional per-analysis OpenAI API key; never stored",
    )


class AnalysisRunOut(BaseModel):
    id: int
    project_id: int
    status: str
    model_name: str | None
    prompt_version: str | None
    claims_extracted: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisStatusOut(BaseModel):
    project_id: int
    analysis_status: str
    current_run: AnalysisRunOut | None
    llm_enabled: bool
