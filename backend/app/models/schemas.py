"""
Candor — Pydantic schemas for API request / response models
and shared internal data structures.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ----------------------------------------------------------------
# Inbound request bodies
# ----------------------------------------------------------------

class ThresholdUpdate(BaseModel):
    value: float = Field(..., ge=0.0, le=1.0, description="Confidence threshold 0–1")


class ExceptionResolution(BaseModel):
    resolution: str = Field(..., pattern="^(accepted|rejected|unmatched)$")
    resolved_by: Optional[str] = None


# ----------------------------------------------------------------
# Outbound response models
# ----------------------------------------------------------------

class UploadResponse(BaseModel):
    batch_id: str
    status: str


class BatchStatus(BaseModel):
    id: UUID
    filename: str
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class MatchRecord(BaseModel):
    id: UUID
    batch_id: UUID
    settlement_id: Optional[UUID] = None
    bank_row_id: Optional[UUID] = None
    order_id: Optional[UUID] = None
    match_type: str                      # 'exact' | 'agent_accepted'
    confidence: Optional[float] = None
    reasoning: Optional[str] = None
    created_at: datetime


class ExceptionRecord(BaseModel):
    id: UUID
    batch_id: UUID
    settlement_id: Optional[UUID] = None
    bank_row_id: Optional[UUID] = None
    order_id: Optional[UUID] = None
    reason_code: str
    reason: str
    agent_candidate_settlement_id: Optional[UUID] = None
    agent_candidate_order_id: Optional[UUID] = None
    agent_confidence: Optional[float] = None
    agent_reasoning: Optional[str] = None
    resolution: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime


class ReportStats(BaseModel):
    total_bank_rows: int
    exact_matches: int
    agent_accepted_matches: int
    exceptions: int
    match_rate_pct: float
    processing_time_seconds: float


class ThresholdResponse(BaseModel):
    value: float
    description: str


# ----------------------------------------------------------------
# Internal models (not exposed directly via API)
# ----------------------------------------------------------------

class AgentMatchResult(BaseModel):
    """Structured output returned by the Gemini agent."""
    settlement_id: Optional[UUID] = None
    order_id: Optional[UUID] = None
    confidence: float
    reasoning: str


class VerificationResult(BaseModel):
    """Result of the deterministic verification gate."""
    accepted: bool
    failure_reason: Optional[str] = None
