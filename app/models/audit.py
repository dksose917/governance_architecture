"""Audit trail models for the healthcare agent framework."""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field
import uuid

from app.models.base import RiskLevel, AgentType, ActionStatus


class AuditLogEntry(BaseModel):
    """Complete audit log entry for regulatory compliance."""
    log_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    agent_id: str
    agent_type: AgentType
    action_type: str
    patient_id: Optional[str] = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""
    confidence_score: float = Field(ge=0.0, le=1.0, default=1.0)
    risk_level: RiskLevel = RiskLevel.LOW
    api_calls: list[dict[str, Any]] = Field(default_factory=list)
    human_override: bool = False
    override_by: Optional[str] = None
    override_reason: Optional[str] = None
    outcome: str = ""
    status: ActionStatus = ActionStatus.PENDING
    modifications: list[dict[str, Any]] = Field(default_factory=list)
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    
    class Config:
        from_attributes = True


class AccessLog(BaseModel):
    """Log entry for PHI access tracking."""
    access_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: str
    user_role: str
    patient_id: str
    resource_type: str
    action: str  # VIEW, CREATE, UPDATE, DELETE
    success: bool = True
    reason: Optional[str] = None
    ip_address: Optional[str] = None
    session_id: Optional[str] = None


class EscalationLog(BaseModel):
    """Log entry for escalation events."""
    escalation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_agent: AgentType
    action_id: str
    escalation_reason: str
    confidence_score: float
    risk_level: RiskLevel
    assigned_to: Optional[str] = None
    resolved: bool = False
    resolution_timestamp: Optional[datetime] = None
    resolution_action: Optional[str] = None
    resolved_by: Optional[str] = None


class ComplianceEvent(BaseModel):
    """Compliance-related event tracking."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: str  # POLICY_VIOLATION, AUDIT_FINDING, BIAS_DETECTED, etc.
    severity: str  # INFO, WARNING, ERROR, CRITICAL
    description: str
    affected_patients: list[str] = Field(default_factory=list)
    affected_agents: list[AgentType] = Field(default_factory=list)
    remediation_required: bool = False
    remediation_status: Optional[str] = None
    remediation_deadline: Optional[datetime] = None
    assigned_to: Optional[str] = None


class BiasMetric(BaseModel):
    """Bias monitoring metric."""
    metric_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metric_type: str  # DEMOGRAPHIC_PARITY, DISPARATE_IMPACT, etc.
    dimension: str  # age, gender, race, etc.
    agent_type: AgentType
    action_type: str
    baseline_rate: float
    observed_rate: float
    disparity_ratio: float
    threshold_exceeded: bool = False
    sample_size: int
    confidence_interval: tuple[float, float] = (0.0, 0.0)
    details: dict[str, Any] = Field(default_factory=dict)
