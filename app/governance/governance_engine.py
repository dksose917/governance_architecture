"""Unified Governance Engine that coordinates all five governance layers."""

import logging
from datetime import datetime
from typing import Optional, Any, Callable

from app.models.base import AgentType, AgentAction, ActionStatus, RiskLevel, AgentResponse
from app.models.governance import GovernanceConfig, ApprovalRequest
from app.governance.risk_gates import RiskGateManager
from app.governance.audit_trail import AuditTrailManager
from app.governance.rbac import RBACManager
from app.governance.fallback import FallbackManager, EscalationTrigger
from app.governance.bias_monitor import BiasMonitor

logger = logging.getLogger(__name__)


class GovernanceEngine:
    """Unified governance engine coordinating all five layers.
    
    Five-Layer Governance Framework:
    1. Risk-Tiered Gates: Classify and gate actions by risk level
    2. Complete Audit Trail: Log all actions for compliance
    3. Role-Based Access Control: Enforce permissions
    4. Fallback Logic: Handle escalations and retries
    5. Bias Monitoring: Detect and report algorithmic bias
    """
    
    def __init__(self, config: Optional[GovernanceConfig] = None):
        self.config = config or GovernanceConfig()
        
        self.risk_gates = RiskGateManager()
        self.audit_trail = AuditTrailManager()
        self.rbac = RBACManager()
        self.fallback = FallbackManager(
            confidence_threshold=self.config.confidence_threshold_default
        )
        self.bias_monitor = BiasMonitor(
            disparate_impact_threshold=self.config.bias_threshold
        )
        
        self._action_handlers: dict[str, Callable] = {}
        self._pre_execution_hooks: list[Callable] = []
        self._post_execution_hooks: list[Callable] = []
        
        self.fallback.register_escalation_callback(self._handle_escalation)
    
    def process_action(
        self,
        action: AgentAction,
        user_id: str,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> AgentResponse:
        """Process an agent action through all governance layers.
        
        Flow:
        1. Check RBAC permissions
        2. Classify risk and evaluate gates
        3. Log to audit trail
        4. Execute if approved, or queue for approval
        5. Record outcome for bias monitoring
        """
        start_time = datetime.utcnow()
        
        has_permission, reason = self.rbac.check_permission(
            user_id=user_id,
            agent_type=action.agent_type,
            action=action.action_type,
            require_write=True
        )
        
        if not has_permission:
            logger.warning(f"Permission denied for {user_id}: {reason}")
            action.status = ActionStatus.REJECTED
            
            self.audit_trail.log_action(
                action=action,
                session_id=session_id,
                user_id=user_id,
                ip_address=ip_address
            )
            
            return AgentResponse(
                success=False,
                action=action,
                error=f"Permission denied: {reason}"
            )
        
        if action.patient_id:
            has_access, access_reason = self.rbac.check_patient_access(
                user_id=user_id,
                patient_id=action.patient_id,
                access_type="WRITE"
            )
            
            if not has_access:
                logger.warning(f"Patient access denied for {user_id}: {access_reason}")
                action.status = ActionStatus.REJECTED
                
                self.audit_trail.log_access(
                    user_id=user_id,
                    user_role=self.rbac.get_user(user_id).role.value if self.rbac.get_user(user_id) else "UNKNOWN",
                    patient_id=action.patient_id,
                    resource_type=action.action_type,
                    action="WRITE",
                    success=False,
                    reason=access_reason,
                    ip_address=ip_address,
                    session_id=session_id
                )
                
                return AgentResponse(
                    success=False,
                    action=action,
                    error=f"Patient access denied: {access_reason}"
                )
        
        action.risk_level = self.risk_gates.classify_risk(action)
        
        should_escalate, trigger, escalation_reason = self.fallback.evaluate_action(action)
        
        if should_escalate and trigger:
            escalation_id = self.fallback.trigger_escalation(
                action=action,
                trigger=trigger,
                reason=escalation_reason or "Automatic escalation"
            )
            
            self.audit_trail.log_escalation(
                source_agent=action.agent_type,
                action_id=action.action_id,
                reason=escalation_reason or "Automatic escalation",
                confidence_score=action.confidence_score,
                risk_level=action.risk_level.value
            )
            
            audit_entry = self.audit_trail.log_action(
                action=action,
                session_id=session_id,
                user_id=user_id,
                ip_address=ip_address
            )
            
            return AgentResponse(
                success=False,
                action=action,
                escalation_required=True,
                escalation_reason=escalation_reason,
                result={"escalation_id": escalation_id}
            )
        
        can_proceed, approval_request = self.risk_gates.evaluate_gate(action)
        
        audit_entry = self.audit_trail.log_action(
            action=action,
            session_id=session_id,
            user_id=user_id,
            ip_address=ip_address
        )
        
        if not can_proceed:
            if approval_request:
                logger.info(f"Action {action.action_id} queued for approval")
                return AgentResponse(
                    success=False,
                    action=action,
                    result={
                        "approval_request_id": approval_request.request_id,
                        "required_approvers": approval_request.required_approvers,
                        "status": "AWAITING_APPROVAL"
                    }
                )
            else:
                return AgentResponse(
                    success=False,
                    action=action,
                    error="Action blocked by risk gate"
                )
        
        for hook in self._pre_execution_hooks:
            try:
                hook(action)
            except Exception as e:
                logger.error(f"Pre-execution hook failed: {e}")
        
        result = self._execute_action(action)
        
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        for hook in self._post_execution_hooks:
            try:
                hook(action, result)
            except Exception as e:
                logger.error(f"Post-execution hook failed: {e}")
        
        if result.get("success", True):
            action.status = ActionStatus.COMPLETED
            self.audit_trail.update_log_outcome(
                log_id=audit_entry.log_id,
                outcome="SUCCESS",
                status=ActionStatus.COMPLETED
            )
        else:
            action.status = ActionStatus.FAILED
            self.audit_trail.update_log_outcome(
                log_id=audit_entry.log_id,
                outcome=result.get("error", "FAILED"),
                status=ActionStatus.FAILED
            )
        
        return AgentResponse(
            success=result.get("success", True),
            action=action,
            result=result
        )
    
    def _execute_action(self, action: AgentAction) -> dict[str, Any]:
        """Execute an action using registered handlers."""
        handler_key = f"{action.agent_type.value}_{action.action_type}"
        
        if handler_key in self._action_handlers:
            try:
                return self._action_handlers[handler_key](action)
            except Exception as e:
                logger.error(f"Action handler failed: {e}")
                return {"success": False, "error": str(e)}
        
        return {"success": True, "message": "Action processed (no specific handler)"}
    
    def register_action_handler(
        self,
        agent_type: AgentType,
        action_type: str,
        handler: Callable[[AgentAction], dict[str, Any]]
    ):
        """Register a handler for a specific action type."""
        key = f"{agent_type.value}_{action_type}"
        self._action_handlers[key] = handler
        logger.info(f"Registered action handler: {key}")
    
    def process_approval(
        self,
        request_id: str,
        approver_id: str,
        approved: bool,
        reason: Optional[str] = None
    ) -> AgentResponse:
        """Process an approval decision."""
        has_permission, perm_reason = self._check_approver_permission(
            approver_id, request_id
        )
        
        if not has_permission:
            return AgentResponse(
                success=False,
                action=AgentAction(
                    agent_type=AgentType.ORCHESTRATOR,
                    action_type="process_approval"
                ),
                error=f"Approver not authorized: {perm_reason}"
            )
        
        result = self.risk_gates.process_approval(
            request_id=request_id,
            approver_id=approver_id,
            approved=approved,
            reason=reason
        )
        
        request = self.risk_gates.pending_approvals.get(request_id)
        
        if request and request.status == "APPROVED":
            original_action = AgentAction(
                action_id=request.action_id,
                agent_type=request.agent_type,
                action_type=request.action_type,
                patient_id=request.patient_id,
                risk_level=request.risk_level,
                confidence_score=request.confidence_score,
                parameters=request.details,
                status=ActionStatus.APPROVED
            )
            
            execution_result = self._execute_action(original_action)
            
            return AgentResponse(
                success=execution_result.get("success", True),
                action=original_action,
                result=execution_result
            )
        
        return AgentResponse(
            success=result,
            action=AgentAction(
                agent_type=AgentType.ORCHESTRATOR,
                action_type="process_approval"
            ),
            result={
                "request_id": request_id,
                "status": request.status if request else "NOT_FOUND",
                "approved": approved
            }
        )
    
    def _check_approver_permission(
        self,
        approver_id: str,
        request_id: str
    ) -> tuple[bool, str]:
        """Check if a user can approve a specific request."""
        request = self.risk_gates.pending_approvals.get(request_id)
        if not request:
            return False, "Request not found"
        
        has_permission, reason = self.rbac.check_permission(
            user_id=approver_id,
            agent_type=request.agent_type,
            action="approve",
            require_approve=True
        )
        
        return has_permission, reason
    
    def _handle_escalation(self, escalation: dict):
        """Handle escalation events."""
        logger.warning(
            f"Escalation received: {escalation['escalation_id']} "
            f"target={escalation['target']}"
        )
    
    def record_for_bias_monitoring(
        self,
        agent_type: AgentType,
        action_type: str,
        patient_demographics: dict[str, str],
        outcome: str,
        outcome_value: Optional[float] = None,
        metadata: Optional[dict] = None
    ):
        """Record an action outcome for bias analysis."""
        self.bias_monitor.record_action_outcome(
            agent_type=agent_type,
            action_type=action_type,
            patient_demographics=patient_demographics,
            outcome=outcome,
            outcome_value=outcome_value,
            metadata=metadata
        )
    
    def get_dashboard_data(self) -> dict[str, Any]:
        """Get comprehensive dashboard data for human oversight."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "pending_approvals": [
                {
                    "request_id": r.request_id,
                    "agent_type": r.agent_type.value,
                    "action_type": r.action_type,
                    "risk_level": r.risk_level.value,
                    "confidence_score": r.confidence_score,
                    "priority": r.priority,
                    "created_at": r.created_at.isoformat(),
                    "required_approvers": r.required_approvers,
                    "current_approvals": r.current_approvals
                }
                for r in self.risk_gates.get_pending_approvals()
            ],
            "pending_escalations": self.fallback.get_pending_escalations(),
            "audit_statistics": self.audit_trail.get_statistics(),
            "escalation_statistics": self.fallback.get_escalation_statistics(),
            "bias_summary": self.bias_monitor.get_bias_summary(),
            "compliance_events": [
                {
                    "event_id": e.event_id,
                    "event_type": e.event_type,
                    "severity": e.severity,
                    "description": e.description,
                    "remediation_status": e.remediation_status,
                    "timestamp": e.timestamp.isoformat()
                }
                for e in self.bias_monitor.get_compliance_events()[:10]
            ]
        }
    
    def human_override(
        self,
        action_id: str,
        override_by: str,
        override_reason: str,
        new_decision: Optional[dict] = None
    ) -> bool:
        """Record and process a human override."""
        for log_id, entry in self.audit_trail.audit_logs.items():
            if action_id in entry.agent_id:
                return self.audit_trail.record_human_override(
                    log_id=log_id,
                    override_by=override_by,
                    override_reason=override_reason
                )
        
        return False
    
    def add_pre_execution_hook(self, hook: Callable[[AgentAction], None]):
        """Add a hook to run before action execution."""
        self._pre_execution_hooks.append(hook)
    
    def add_post_execution_hook(
        self,
        hook: Callable[[AgentAction, dict[str, Any]], None]
    ):
        """Add a hook to run after action execution."""
        self._post_execution_hooks.append(hook)
    
    def get_configuration(self) -> dict[str, Any]:
        """Get current governance configuration."""
        return {
            "confidence_threshold": self.config.confidence_threshold_default,
            "escalation_timeout": self.config.escalation_timeout_default,
            "max_retries": self.config.max_retry_attempts,
            "audit_retention_days": self.config.audit_retention_days,
            "bias_threshold": self.config.bias_threshold,
            "bias_monitoring_enabled": self.config.bias_monitoring_enabled,
            "api_rate_limits": self.config.api_rate_limits
        }
    
    def update_configuration(self, updates: dict[str, Any]) -> bool:
        """Update governance configuration."""
        for key, value in updates.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        if "confidence_threshold_default" in updates:
            self.fallback.update_confidence_threshold(
                updates["confidence_threshold_default"]
            )
        
        if "bias_threshold" in updates:
            self.bias_monitor.disparate_impact_threshold = updates["bias_threshold"]
        
        self.config.updated_at = datetime.utcnow()
        logger.info(f"Governance configuration updated: {list(updates.keys())}")
        return True
