"""Layer 4: Fallback Logic Engine for the governance framework."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Callable, Any
from enum import Enum

from app.models.base import AgentType, AgentAction, ActionStatus, RiskLevel
from app.models.governance import FallbackRule

logger = logging.getLogger(__name__)


class EscalationTrigger(str, Enum):
    """Types of escalation triggers."""
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    TIMEOUT = "TIMEOUT"
    CONFLICT = "CONFLICT"
    SAFETY_CONCERN = "SAFETY_CONCERN"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    AMBIGUOUS_RESULT = "AMBIGUOUS_RESULT"
    REPEATED_FAILURE = "REPEATED_FAILURE"


class EscalationTarget(str, Enum):
    """Escalation targets."""
    SUPERVISOR = "SUPERVISOR"
    CLINICAL_DIRECTOR = "CLINICAL_DIRECTOR"
    SYSTEM_ADMIN = "SYSTEM_ADMIN"
    ON_CALL_PHYSICIAN = "ON_CALL_PHYSICIAN"


class FallbackManager:
    """Manages fallback logic and automatic escalation.
    
    Escalation Triggers:
    - AI confidence score below threshold
    - Ambiguous NLP extraction results
    - Conflicting information detected
    - System timeout or service unavailability
    - Patient safety concerns identified
    """
    
    def __init__(self, confidence_threshold: float = 0.85):
        self.confidence_threshold = confidence_threshold
        self.rules: dict[str, FallbackRule] = {}
        self.pending_escalations: dict[str, dict] = {}
        self.retry_counts: dict[str, int] = {}
        self.escalation_callbacks: list[Callable] = []
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default fallback rules."""
        default_rules = [
            FallbackRule(
                name="low_confidence_escalation",
                trigger_condition=EscalationTrigger.LOW_CONFIDENCE.value,
                confidence_threshold=0.85,
                escalation_target=EscalationTarget.SUPERVISOR.value,
                notification_method="DASHBOARD",
                auto_retry=False
            ),
            FallbackRule(
                name="timeout_escalation",
                trigger_condition=EscalationTrigger.TIMEOUT.value,
                timeout_seconds=300,
                escalation_target=EscalationTarget.SUPERVISOR.value,
                notification_method="ALL",
                auto_retry=True,
                max_retries=3
            ),
            FallbackRule(
                name="safety_concern_escalation",
                trigger_condition=EscalationTrigger.SAFETY_CONCERN.value,
                escalation_target=EscalationTarget.CLINICAL_DIRECTOR.value,
                notification_method="ALL",
                auto_retry=False
            ),
            FallbackRule(
                name="service_unavailable_escalation",
                trigger_condition=EscalationTrigger.SERVICE_UNAVAILABLE.value,
                escalation_target=EscalationTarget.SYSTEM_ADMIN.value,
                notification_method="DASHBOARD",
                auto_retry=True,
                max_retries=5
            ),
            FallbackRule(
                name="ambiguous_result_escalation",
                trigger_condition=EscalationTrigger.AMBIGUOUS_RESULT.value,
                confidence_threshold=0.70,
                escalation_target=EscalationTarget.SUPERVISOR.value,
                notification_method="DASHBOARD",
                auto_retry=False
            )
        ]
        
        for rule in default_rules:
            self.rules[rule.rule_id] = rule
    
    def evaluate_action(
        self,
        action: AgentAction,
        execution_time_ms: Optional[float] = None
    ) -> tuple[bool, Optional[EscalationTrigger], Optional[str]]:
        """Evaluate if an action should trigger fallback/escalation.
        
        Returns:
            tuple: (should_escalate, trigger_type, reason)
        """
        if action.confidence_score < self.confidence_threshold:
            return True, EscalationTrigger.LOW_CONFIDENCE, (
                f"Confidence score {action.confidence_score:.2f} below "
                f"threshold {self.confidence_threshold}"
            )
        
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            
            if rule.trigger_condition == EscalationTrigger.TIMEOUT.value:
                if execution_time_ms and execution_time_ms > rule.timeout_seconds * 1000:
                    return True, EscalationTrigger.TIMEOUT, (
                        f"Execution time {execution_time_ms}ms exceeded "
                        f"timeout {rule.timeout_seconds}s"
                    )
        
        return False, None, None
    
    def check_confidence_threshold(
        self,
        confidence_score: float,
        action_type: str
    ) -> tuple[bool, str]:
        """Check if confidence score meets threshold for action type."""
        threshold = self.confidence_threshold
        
        high_stakes_actions = {
            "medication_change": 0.95,
            "biomarker_alert": 0.90,
            "emergency_intervention": 0.95,
            "discharge_decision": 0.92
        }
        
        if action_type in high_stakes_actions:
            threshold = high_stakes_actions[action_type]
        
        if confidence_score >= threshold:
            return True, f"Confidence {confidence_score:.2f} meets threshold {threshold}"
        else:
            return False, f"Confidence {confidence_score:.2f} below threshold {threshold}"
    
    def trigger_escalation(
        self,
        action: AgentAction,
        trigger: EscalationTrigger,
        reason: str,
        additional_context: Optional[dict] = None
    ) -> str:
        """Trigger an escalation for an action."""
        rule = self._get_rule_for_trigger(trigger)
        
        escalation_id = f"esc_{action.action_id[:8]}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        escalation = {
            "escalation_id": escalation_id,
            "action_id": action.action_id,
            "agent_type": action.agent_type.value,
            "trigger": trigger.value,
            "reason": reason,
            "target": rule.escalation_target if rule else EscalationTarget.SUPERVISOR.value,
            "notification_method": rule.notification_method if rule else "DASHBOARD",
            "created_at": datetime.utcnow().isoformat(),
            "status": "PENDING",
            "context": additional_context or {},
            "patient_id": action.patient_id,
            "risk_level": action.risk_level.value,
            "confidence_score": action.confidence_score
        }
        
        self.pending_escalations[escalation_id] = escalation
        action.status = ActionStatus.ESCALATED
        
        for callback in self.escalation_callbacks:
            try:
                callback(escalation)
            except Exception as e:
                logger.error(f"Escalation callback failed: {e}")
        
        logger.warning(
            f"Escalation triggered: {escalation_id} for action {action.action_id} "
            f"trigger={trigger.value} target={escalation['target']}"
        )
        
        return escalation_id
    
    def _get_rule_for_trigger(self, trigger: EscalationTrigger) -> Optional[FallbackRule]:
        """Get the fallback rule for a specific trigger."""
        for rule in self.rules.values():
            if rule.trigger_condition == trigger.value and rule.enabled:
                return rule
        return None
    
    def should_retry(self, action_id: str) -> tuple[bool, int]:
        """Check if an action should be retried.
        
        Returns:
            tuple: (should_retry, remaining_retries)
        """
        current_retries = self.retry_counts.get(action_id, 0)
        max_retries = 3
        
        if current_retries < max_retries:
            self.retry_counts[action_id] = current_retries + 1
            return True, max_retries - current_retries - 1
        
        return False, 0
    
    def resolve_escalation(
        self,
        escalation_id: str,
        resolved_by: str,
        resolution: str,
        action_taken: str
    ) -> bool:
        """Resolve an escalation."""
        if escalation_id not in self.pending_escalations:
            logger.error(f"Escalation {escalation_id} not found")
            return False
        
        escalation = self.pending_escalations[escalation_id]
        escalation["status"] = "RESOLVED"
        escalation["resolved_at"] = datetime.utcnow().isoformat()
        escalation["resolved_by"] = resolved_by
        escalation["resolution"] = resolution
        escalation["action_taken"] = action_taken
        
        logger.info(f"Escalation {escalation_id} resolved by {resolved_by}")
        return True
    
    def get_pending_escalations(
        self,
        target: Optional[EscalationTarget] = None
    ) -> list[dict]:
        """Get all pending escalations, optionally filtered by target."""
        pending = [
            e for e in self.pending_escalations.values()
            if e["status"] == "PENDING"
        ]
        
        if target:
            pending = [e for e in pending if e["target"] == target.value]
        
        return sorted(pending, key=lambda x: x["created_at"], reverse=True)
    
    def get_escalation_statistics(self) -> dict:
        """Get escalation statistics."""
        total = len(self.pending_escalations)
        pending = len([e for e in self.pending_escalations.values() if e["status"] == "PENDING"])
        resolved = len([e for e in self.pending_escalations.values() if e["status"] == "RESOLVED"])
        
        by_trigger = {}
        by_target = {}
        by_agent = {}
        
        for e in self.pending_escalations.values():
            trigger = e["trigger"]
            target = e["target"]
            agent = e["agent_type"]
            
            by_trigger[trigger] = by_trigger.get(trigger, 0) + 1
            by_target[target] = by_target.get(target, 0) + 1
            by_agent[agent] = by_agent.get(agent, 0) + 1
        
        return {
            "total_escalations": total,
            "pending": pending,
            "resolved": resolved,
            "by_trigger": by_trigger,
            "by_target": by_target,
            "by_agent": by_agent
        }
    
    def register_escalation_callback(self, callback: Callable):
        """Register a callback to be called when escalations are triggered."""
        self.escalation_callbacks.append(callback)
    
    def add_rule(self, rule: FallbackRule):
        """Add a custom fallback rule."""
        self.rules[rule.rule_id] = rule
        logger.info(f"Added fallback rule: {rule.name}")
    
    def update_confidence_threshold(self, threshold: float):
        """Update the global confidence threshold."""
        if 0.0 <= threshold <= 1.0:
            self.confidence_threshold = threshold
            logger.info(f"Confidence threshold updated to {threshold}")
        else:
            raise ValueError("Threshold must be between 0.0 and 1.0")
    
    def check_service_health(self, service_name: str, response_time_ms: float) -> bool:
        """Check if a service response indicates health issues."""
        thresholds = {
            "elevenlabs": 5000,
            "canary_speech": 10000,
            "twilio": 3000,
            "aws_comprehend": 5000,
            "john_snow_labs": 15000
        }
        
        threshold = thresholds.get(service_name, 5000)
        return response_time_ms <= threshold
