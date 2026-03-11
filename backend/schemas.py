from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, description="Minimum 8 characters")


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------


class TaskCreate(BaseModel):
    description: str = Field(
        min_length=1,
        max_length=2000,
        description="Task description (max 2000 characters)",
    )


class TaskRunRequest(BaseModel):
    budget_cap: float = Field(
        ge=0.10,
        le=20.00,
        description="Budget cap in USD (0.10 – 20.00)",
    )
    openai_key: str = Field(
        min_length=20,
        description="User-provided OpenAI API key (never stored)",
    )

    @field_validator("openai_key")
    @classmethod
    def key_must_look_valid(cls, v: str) -> str:
        if not v.startswith("sk-"):
            raise ValueError("openai_key must start with 'sk-'")
        return v


class EstimationResponse(BaseModel):
    steps: int
    duration_min: int
    duration_max: int
    cost_estimate_usd: float


class TaskStepResponse(BaseModel):
    id: str
    task_id: str
    tool: str
    description: Optional[str]
    status: str
    cost_usd: float
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskResponse(BaseModel):
    id: str
    user_id: str
    description: str
    status: str
    budget_cap: Optional[float]
    cost_actual: float
    estimation: Optional[dict[str, Any]]
    result_summary: Optional[str]
    result_file_path: Optional[str]
    sandbox_id: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    steps: list[TaskStepResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Generic error
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    detail: str
