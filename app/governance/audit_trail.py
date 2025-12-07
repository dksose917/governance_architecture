"""Layer 2: Complete Audit Trail for the governance framework."""

import logging
import json
from datetime import datetime
from typing import Optional, Any
from collections import defaultdict

from app.models.base import AgentType, AgentAction, ActionStatus, APICallLog
from app.models.audit import AuditLogEntry, AccessLog, EscalationLog

logger = logging.getLogger(__name__)


class AuditTrailManager:
    """Manages complete audit trails for regulatory compliance.
    
    Every agent action is logged with:
    - Timestamp (ISO 8601 format)
    - Agent identifier
    - Action type and parameters
    - Decision rationale
    - Confidence score
    - API call details
    - Human override capability
    - Outcome and modifications
    """
    
    def __init__(self):
        self.audit_logs: dict[str, AuditLogEntry] = {}
        self.access_logs: dict[str, AccessLog] = {}
        self.escalation_logs: dict[str, EscalationLog] = {}
        self.api_call_logs: dict[str, APICallLog] = {}
        self._log_index_by_patient: dict[str, list[str]] = defaultdict(list)
        self._log_index_by_agent: dict[AgentType, list[str]] = defaultdict(list)
        self._log_index_by_session: dict[str, list[str]] = defaultdict(list)
    
    def log_action(
        self,
        action: AgentAction,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> AuditLogEntry:
        """Log an agent action to the audit trail."""
        entry = AuditLogEntry(
            agent_id=f"{action.agent_type.value}_{action.action_id[:8]}",
            agent_type=action.agent_type,
            action_type=action.action_type,
            patient_id=action.patient_id,
            parameters=action.parameters,
            rationale=action.rationale,
            confidence_score=action.confidence_score,
            risk_level=action.risk_level,
            status=action.status,
            session_id=session_id,
            user_id=user_id,
            ip_address=ip_address
        )
        
        self.audit_logs[entry.log_id] = entry
        
        if action.patient_id:
            self._log_index_by_patient[action.patient_id].append(entry.log_id)
        self._log_index_by_agent[action.agent_type].append(entry.log_id)
        if session_id:
            self._log_index_by_session[session_id].append(entry.log_id)
        
        logger.info(
            f"Audit log created: {entry.log_id} for action {action.action_type} "
            f"by {action.agent_type.value}"
        )
        
        return entry
    
    def log_api_call(self, api_call: APICallLog, action_id: str) -> str:
        """Log an external API call and associate it with an action."""
        self.api_call_logs[api_call.call_id] = api_call
        
        for entry in self.audit_logs.values():
            if action_id in entry.agent_id or entry.log_id == action_id:
                entry.api_calls.append({
                    "call_id": api_call.call_id,
                    "service": api_call.service_name,
                    "endpoint": api_call.endpoint,
                    "status_code": api_call.status_code,
                    "latency_ms": api_call.latency_ms,
                    "timestamp": api_call.timestamp.isoformat()
                })
                break
        
        logger.debug(
            f"API call logged: {api_call.service_name} {api_call.endpoint} "
            f"status={api_call.status_code}"
        )
        
        return api_call.call_id
    
    def log_access(
        self,
        user_id: str,
        user_role: str,
        patient_id: str,
        resource_type: str,
        action: str,
        success: bool = True,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> AccessLog:
        """Log PHI access for HIPAA compliance."""
        log = AccessLog(
            user_id=user_id,
            user_role=user_role,
            patient_id=patient_id,
            resource_type=resource_type,
            action=action,
            success=success,
            reason=reason,
            ip_address=ip_address,
            session_id=session_id
        )
        
        self.access_logs[log.access_id] = log
        
        logger.info(
            f"Access log: {user_id} ({user_role}) {action} {resource_type} "
            f"for patient {patient_id[:8]}... success={success}"
        )
        
        return log
    
    def log_escalation(
        self,
        source_agent: AgentType,
        action_id: str,
        reason: str,
        confidence_score: float,
        risk_level: str,
        assigned_to: Optional[str] = None
    ) -> EscalationLog:
        """Log an escalation event."""
        from app.models.base import RiskLevel
        
        log = EscalationLog(
            source_agent=source_agent,
            action_id=action_id,
            escalation_reason=reason,
            confidence_score=confidence_score,
            risk_level=RiskLevel(risk_level) if isinstance(risk_level, str) else risk_level,
            assigned_to=assigned_to
        )
        
        self.escalation_logs[log.escalation_id] = log
        
        logger.warning(
            f"Escalation logged: {source_agent.value} action {action_id[:8]}... "
            f"reason={reason}"
        )
        
        return log
    
    def update_log_outcome(
        self,
        log_id: str,
        outcome: str,
        status: ActionStatus,
        modifications: Optional[list[dict]] = None
    ) -> bool:
        """Update the outcome of an audit log entry."""
        if log_id not in self.audit_logs:
            logger.error(f"Audit log {log_id} not found")
            return False
        
        entry = self.audit_logs[log_id]
        entry.outcome = outcome
        entry.status = status
        if modifications:
            entry.modifications.extend(modifications)
        
        logger.info(f"Audit log {log_id} updated: status={status.value}")
        return True
    
    def record_human_override(
        self,
        log_id: str,
        override_by: str,
        override_reason: str
    ) -> bool:
        """Record a human override on an action."""
        if log_id not in self.audit_logs:
            logger.error(f"Audit log {log_id} not found")
            return False
        
        entry = self.audit_logs[log_id]
        entry.human_override = True
        entry.override_by = override_by
        entry.override_reason = override_reason
        entry.modifications.append({
            "type": "HUMAN_OVERRIDE",
            "timestamp": datetime.utcnow().isoformat(),
            "by": override_by,
            "reason": override_reason
        })
        
        logger.info(f"Human override recorded on {log_id} by {override_by}")
        return True
    
    def resolve_escalation(
        self,
        escalation_id: str,
        resolved_by: str,
        resolution_action: str
    ) -> bool:
        """Mark an escalation as resolved."""
        if escalation_id not in self.escalation_logs:
            logger.error(f"Escalation {escalation_id} not found")
            return False
        
        log = self.escalation_logs[escalation_id]
        log.resolved = True
        log.resolution_timestamp = datetime.utcnow()
        log.resolution_action = resolution_action
        log.resolved_by = resolved_by
        
        logger.info(f"Escalation {escalation_id} resolved by {resolved_by}")
        return True
    
    def get_patient_audit_trail(self, patient_id: str) -> list[AuditLogEntry]:
        """Get all audit logs for a specific patient."""
        log_ids = self._log_index_by_patient.get(patient_id, [])
        logs = [self.audit_logs[lid] for lid in log_ids if lid in self.audit_logs]
        return sorted(logs, key=lambda x: x.timestamp, reverse=True)
    
    def get_agent_audit_trail(self, agent_type: AgentType) -> list[AuditLogEntry]:
        """Get all audit logs for a specific agent type."""
        log_ids = self._log_index_by_agent.get(agent_type, [])
        logs = [self.audit_logs[lid] for lid in log_ids if lid in self.audit_logs]
        return sorted(logs, key=lambda x: x.timestamp, reverse=True)
    
    def get_session_audit_trail(self, session_id: str) -> list[AuditLogEntry]:
        """Get all audit logs for a specific session."""
        log_ids = self._log_index_by_session.get(session_id, [])
        logs = [self.audit_logs[lid] for lid in log_ids if lid in self.audit_logs]
        return sorted(logs, key=lambda x: x.timestamp)
    
    def get_access_logs_for_patient(self, patient_id: str) -> list[AccessLog]:
        """Get all access logs for a specific patient."""
        logs = [log for log in self.access_logs.values() if log.patient_id == patient_id]
        return sorted(logs, key=lambda x: x.timestamp, reverse=True)
    
    def get_pending_escalations(self) -> list[EscalationLog]:
        """Get all unresolved escalations."""
        return [log for log in self.escalation_logs.values() if not log.resolved]
    
    def export_audit_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        patient_id: Optional[str] = None,
        agent_type: Optional[AgentType] = None
    ) -> dict[str, Any]:
        """Export audit logs for compliance reporting."""
        logs = list(self.audit_logs.values())
        
        if start_date:
            logs = [l for l in logs if l.timestamp >= start_date]
        if end_date:
            logs = [l for l in logs if l.timestamp <= end_date]
        if patient_id:
            logs = [l for l in logs if l.patient_id == patient_id]
        if agent_type:
            logs = [l for l in logs if l.agent_type == agent_type]
        
        return {
            "report_generated": datetime.utcnow().isoformat(),
            "total_entries": len(logs),
            "date_range": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            },
            "filters": {
                "patient_id": patient_id,
                "agent_type": agent_type.value if agent_type else None
            },
            "entries": [
                {
                    "log_id": l.log_id,
                    "timestamp": l.timestamp.isoformat(),
                    "agent_type": l.agent_type.value,
                    "action_type": l.action_type,
                    "patient_id": l.patient_id,
                    "risk_level": l.risk_level.value,
                    "confidence_score": l.confidence_score,
                    "status": l.status.value,
                    "human_override": l.human_override,
                    "api_calls_count": len(l.api_calls)
                }
                for l in sorted(logs, key=lambda x: x.timestamp)
            ]
        }
    
    def get_statistics(self) -> dict[str, Any]:
        """Get audit trail statistics."""
        total_logs = len(self.audit_logs)
        
        by_agent = defaultdict(int)
        by_risk = defaultdict(int)
        by_status = defaultdict(int)
        overrides = 0
        
        for log in self.audit_logs.values():
            by_agent[log.agent_type.value] += 1
            by_risk[log.risk_level.value] += 1
            by_status[log.status.value] += 1
            if log.human_override:
                overrides += 1
        
        return {
            "total_audit_logs": total_logs,
            "total_access_logs": len(self.access_logs),
            "total_escalations": len(self.escalation_logs),
            "pending_escalations": len(self.get_pending_escalations()),
            "total_api_calls": len(self.api_call_logs),
            "human_overrides": overrides,
            "by_agent_type": dict(by_agent),
            "by_risk_level": dict(by_risk),
            "by_status": dict(by_status)
        }
