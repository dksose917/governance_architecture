"""Base models and enums for the healthcare agent framework."""

from enum import Enum
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field
import uuid


class RiskLevel(str, Enum):
    """Risk classification levels for agent actions."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AgentType(str, Enum):
    """Types of agents in the 8+1 architecture."""
    ORCHESTRATOR = "ORCHESTRATOR"
    INTAKE = "INTAKE"
    CARE_PLANNING = "CARE_PLANNING"
    MEDICATION = "MEDICATION"
    DOCUMENTATION = "DOCUMENTATION"
    BILLING = "BILLING"
    COMPLIANCE = "COMPLIANCE"
    FAMILY_COMMUNICATION = "FAMILY_COMMUNICATION"
    SCHEDULING = "SCHEDULING"


class ActionStatus(str, Enum):
    """Status of an agent action."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"


class UserRole(str, Enum):
    """User roles for RBAC."""
    SYSTEM_ADMIN = "SYSTEM_ADMIN"
    CLINICAL_DIRECTOR = "CLINICAL_DIRECTOR"
    NURSE_MANAGER = "NURSE_MANAGER"
    CARE_COORDINATOR = "CARE_COORDINATOR"
    BILLING_STAFF = "BILLING_STAFF"
    FAMILY_PORTAL = "FAMILY_PORTAL"


class BaseEntity(BaseModel):
    """Base entity with common fields."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class AgentAction(BaseModel):
    """Represents an action taken by an agent."""
    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_type: AgentType
    action_type: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    patient_id: Optional[str] = None
    risk_level: RiskLevel = RiskLevel.LOW
    confidence_score: float = Field(ge=0.0, le=1.0, default=1.0)
    rationale: str = ""
    status: ActionStatus = ActionStatus.PENDING
    requires_approval: bool = False
    approved_by: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentResponse(BaseModel):
    """Standard response from an agent."""
    success: bool
    action: AgentAction
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    escalation_required: bool = False
    escalation_reason: Optional[str] = None


class APICallLog(BaseModel):
    """Log entry for external API calls."""
    call_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    service_name: str
    endpoint: str
    method: str = "POST"
    request_payload: dict[str, Any] = Field(default_factory=dict)
    response_payload: Optional[dict[str, Any]] = None
    status_code: int = 200
    latency_ms: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error: Optional[str] = None
