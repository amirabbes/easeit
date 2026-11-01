from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class UserRole(str):
    pass


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    user: dict[str, Any]


class MessageSummary(BaseModel):
    id: str
    sender: str
    subject: str
    priority: str
    category: str
    intent: str
    destination: str
    confidence: float
    received_at: datetime | None = None


class CandidateSummary(BaseModel):
    id: str
    full_name: str
    email: str
    source: str


class ApprovalDraft(BaseModel):
    id: int
    action: str
    status: str
    required_role: str
    payload: dict[str, Any]
    expires_at: datetime | None = None


class DigestEntry(BaseModel):
    period: str
    html: str


class AuditCheck(BaseModel):
    valid: bool
    count: int | None = None
    broken_at: int | None = None


class SupportQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class SupportAnswer(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)
    answerable: bool
    escalated: bool = False
    ticket_id: int | None = None


class TicketStatusUpdate(BaseModel):
    status: Literal['IN_PROGRESS', 'RESOLVED']


class WorkflowIntakeRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=20000)
    cv_text: str = Field(default='', max_length=12000)
    candidate_name: str | None = Field(default=None, max_length=60)
    candidate_id: str | None = Field(default=None, max_length=20)
    job_id: str = Field(default='JOB-001', min_length=1, max_length=20)


class WorkflowClassification(BaseModel):
    category: Literal['RECRUITMENT', 'EMPLOYEE', 'EMPLOYEE_SUPPORT', 'TRAINING', 'DEPARTMENT_REQUEST', 'OTHER']
    intent: Literal['NEW_APPLICATION', 'INTERVIEW_CHANGE', 'FOLLOW_UP_REPLY', 'POLICY_QUESTION', 'PERSONAL_DATA_REQUEST', 'TRAINING_REQUEST', 'IT_ACCESS_REQUEST', 'OTHER']
    priority: Literal['URGENT', 'MEDIUM', 'LOW', 'INFORMATION']
    destination: Literal['ATS_AGENT', 'URGENT_AGENT', 'EMPLOYEE_AGENT', 'HUMAN_REVIEW']
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(default='', max_length=500)
    source: Literal['RULES', 'LLM'] = 'RULES'
    department: Literal['HR', 'IT', 'FINANCE', 'MARKETING', 'SALES', 'OTHER'] | None = None


class WorkflowIntakeResponse(BaseModel):
    request_id: str
    execution_id: str | None = None
    message_id: str
    status: str
    classification: WorkflowClassification
    duplicate: bool = False
