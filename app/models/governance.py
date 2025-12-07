"""Governance models for the healthcare agent framework."""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field
import uuid

from app.models.base import RiskLevel, AgentType, UserRole


class ApprovalRequest(BaseModel):
    """Request for human approval of an agent action."""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    action_id: str
    agent_type: AgentType
    action_type: str
    patient_id: Optional[str] = None
    risk_level: RiskLevel
    confidence_score: float
    rationale: str
    details: dict[str, Any] = Field(default_factory=dict)
    required_approvers: int = 1
    current_approvals: int = 0
    approved_by: list[str] = Field(default_factory=list)
    rejected_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED, EXPIRED
    expires_at: Optional[datetime] = None
    priority: str = "NORMAL"  # LOW, NORMAL, HIGH, URGENT


class GovernanceRule(BaseModel):
    """Rule definition for governance framework."""
    rule_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    agent_types: list[AgentType] = Field(default_factory=list)
    action_types: list[str] = Field(default_factory=list)
    risk_level: RiskLevel
    confidence_threshold: float = 0.85
    requires_approval: bool = False
    required_approvers: int = 1
    approver_roles: list[UserRole] = Field(default_factory=list)
    auto_escalate: bool = True
    escalation_timeout_seconds: int = 300
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RBACPermission(BaseModel):
    """Permission definition for RBAC."""
    permission_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: UserRole
    agent_type: AgentType
    allowed_actions: list[str] = Field(default_factory=list)
    read_access: bool = False
    write_access: bool = False
    approve_access: bool = False
    admin_access: bool = False


class User(BaseModel):
    """User account for the system."""
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: str
    role: UserRole
    department: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    permissions_override: list[str] = Field(default_factory=list)


class FallbackRule(BaseModel):
    """Rule for fallback/escalation logic."""
    rule_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    trigger_condition: str  # LOW_CONFIDENCE, TIMEOUT, CONFLICT, SAFETY_CONCERN
    confidence_threshold: float = 0.85
    timeout_seconds: int = 300
    escalation_target: str  # SUPERVISOR, CLINICAL_DIRECTOR, SYSTEM_ADMIN
    notification_method: str = "DASHBOARD"  # DASHBOARD, EMAIL, SMS, ALL
    auto_retry: bool = False
    max_retries: int = 3
    enabled: bool = True


class GovernanceConfig(BaseModel):
    """Global governance configuration."""
    config_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    confidence_threshold_default: float = 0.85
    escalation_timeout_default: int = 300
    max_retry_attempts: int = 3
    audit_retention_days: int = 2555  # 7 years for HIPAA
    session_timeout_minutes: int = 30
    require_mfa: bool = True
    encryption_enabled: bool = True
    bias_monitoring_enabled: bool = True
    bias_threshold: float = 0.8  # Disparate impact ratio threshold
    api_rate_limits: dict[str, int] = Field(default_factory=lambda: {
        "elevenlabs": 100,
        "canary_speech": 50,
        "twilio": 200,
        "aws_comprehend": 100,
        "john_snow_labs": 50
    })
    updated_at: datetime = Field(default_factory=datetime.utcnow)
