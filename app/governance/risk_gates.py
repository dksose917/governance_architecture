"""Layer 1: Risk-Tiered Gates for the governance framework."""

import logging
from datetime import datetime
from typing import Optional

from app.models.base import RiskLevel, AgentType, AgentAction, ActionStatus
from app.models.governance import ApprovalRequest, GovernanceRule

logger = logging.getLogger(__name__)


class RiskGateManager:
    """Manages risk-tiered gates for agent actions.
    
    Risk Categories:
    - LOW: Routine administrative tasks - auto-execute
    - MEDIUM: Standard clinical operations - supervisor notification
    - HIGH: Clinical decisions with patient impact - human approval required
    - CRITICAL: High-stakes clinical decisions - multi-person approval
    """
    
    def __init__(self):
        self.rules: dict[str, GovernanceRule] = {}
        self.pending_approvals: dict[str, ApprovalRequest] = {}
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default governance rules for each risk level."""
        default_rules = [
            GovernanceRule(
                name="low_risk_auto_execute",
                description="Auto-execute low-risk administrative tasks",
                risk_level=RiskLevel.LOW,
                confidence_threshold=0.7,
                requires_approval=False,
                auto_escalate=False
            ),
            GovernanceRule(
                name="medium_risk_notify",
                description="Execute with supervisor notification",
                risk_level=RiskLevel.MEDIUM,
                confidence_threshold=0.85,
                requires_approval=False,
                auto_escalate=True
            ),
            GovernanceRule(
                name="high_risk_approval",
                description="Require human approval for high-risk actions",
                risk_level=RiskLevel.HIGH,
                confidence_threshold=0.90,
                requires_approval=True,
                required_approvers=1
            ),
            GovernanceRule(
                name="critical_multi_approval",
                description="Require multi-person approval for critical actions",
                risk_level=RiskLevel.CRITICAL,
                confidence_threshold=0.95,
                requires_approval=True,
                required_approvers=2
            )
        ]
        for rule in default_rules:
            self.rules[rule.rule_id] = rule
    
    def classify_risk(self, action: AgentAction) -> RiskLevel:
        """Classify the risk level of an action based on type and context."""
        high_risk_actions = {
            "medication_change", "treatment_modification", "discharge_decision",
            "emergency_intervention", "biomarker_alert", "adverse_event_report"
        }
        
        medium_risk_actions = {
            "care_plan_update", "documentation_update", "assessment_completion",
            "referral_creation", "order_entry"
        }
        
        critical_actions = {
            "critical_biomarker_alert", "emergency_escalation", 
            "life_threatening_condition", "code_blue_activation"
        }
        
        if action.action_type in critical_actions:
            return RiskLevel.CRITICAL
        elif action.action_type in high_risk_actions:
            return RiskLevel.HIGH
        elif action.action_type in medium_risk_actions:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def evaluate_gate(self, action: AgentAction) -> tuple[bool, Optional[ApprovalRequest]]:
        """Evaluate if an action can proceed through the risk gate.
        
        Returns:
            tuple: (can_proceed, approval_request if needed)
        """
        risk_level = action.risk_level or self.classify_risk(action)
        action.risk_level = risk_level
        
        rule = self._get_rule_for_risk_level(risk_level)
        
        if action.confidence_score < rule.confidence_threshold:
            logger.warning(
                f"Action {action.action_id} confidence {action.confidence_score} "
                f"below threshold {rule.confidence_threshold}"
            )
            return False, self._create_approval_request(action, rule, "LOW_CONFIDENCE")
        
        if rule.requires_approval:
            approval_request = self._create_approval_request(action, rule, "RISK_LEVEL")
            return False, approval_request
        
        if risk_level == RiskLevel.LOW:
            action.status = ActionStatus.APPROVED
            return True, None
        
        if risk_level == RiskLevel.MEDIUM:
            action.status = ActionStatus.APPROVED
            logger.info(f"Medium-risk action {action.action_id} approved with notification")
            return True, None
        
        return False, self._create_approval_request(action, rule, "RISK_LEVEL")
    
    def _get_rule_for_risk_level(self, risk_level: RiskLevel) -> GovernanceRule:
        """Get the governance rule for a specific risk level."""
        for rule in self.rules.values():
            if rule.risk_level == risk_level:
                return rule
        return list(self.rules.values())[0]
    
    def _create_approval_request(
        self, 
        action: AgentAction, 
        rule: GovernanceRule,
        reason: str
    ) -> ApprovalRequest:
        """Create an approval request for an action."""
        priority = "URGENT" if action.risk_level == RiskLevel.CRITICAL else "HIGH"
        
        request = ApprovalRequest(
            action_id=action.action_id,
            agent_type=action.agent_type,
            action_type=action.action_type,
            patient_id=action.patient_id,
            risk_level=action.risk_level,
            confidence_score=action.confidence_score,
            rationale=f"{reason}: {action.rationale}",
            details=action.parameters,
            required_approvers=rule.required_approvers,
            priority=priority
        )
        
        self.pending_approvals[request.request_id] = request
        action.status = ActionStatus.AWAITING_APPROVAL
        
        logger.info(
            f"Created approval request {request.request_id} for action {action.action_id}"
        )
        
        return request
    
    def process_approval(
        self, 
        request_id: str, 
        approver_id: str, 
        approved: bool,
        reason: Optional[str] = None
    ) -> bool:
        """Process an approval decision."""
        if request_id not in self.pending_approvals:
            logger.error(f"Approval request {request_id} not found")
            return False
        
        request = self.pending_approvals[request_id]
        
        if approved:
            request.approved_by.append(approver_id)
            request.current_approvals += 1
            
            if request.current_approvals >= request.required_approvers:
                request.status = "APPROVED"
                logger.info(f"Approval request {request_id} fully approved")
                return True
            else:
                logger.info(
                    f"Approval request {request_id} has {request.current_approvals}/"
                    f"{request.required_approvers} approvals"
                )
                return False
        else:
            request.status = "REJECTED"
            request.rejected_by = approver_id
            request.rejection_reason = reason
            logger.info(f"Approval request {request_id} rejected by {approver_id}")
            return False
    
    def get_pending_approvals(self, agent_type: Optional[AgentType] = None) -> list[ApprovalRequest]:
        """Get all pending approval requests, optionally filtered by agent type."""
        pending = [r for r in self.pending_approvals.values() if r.status == "PENDING"]
        if agent_type:
            pending = [r for r in pending if r.agent_type == agent_type]
        return sorted(pending, key=lambda x: x.created_at, reverse=True)
    
    def add_rule(self, rule: GovernanceRule):
        """Add a custom governance rule."""
        self.rules[rule.rule_id] = rule
        logger.info(f"Added governance rule: {rule.name}")
    
    def update_rule(self, rule_id: str, updates: dict) -> bool:
        """Update an existing governance rule."""
        if rule_id not in self.rules:
            return False
        
        rule = self.rules[rule_id]
        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        rule.updated_at = datetime.utcnow()
        return True
