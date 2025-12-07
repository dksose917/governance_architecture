"""Base agent class for all healthcare agents."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Any

from app.models.base import AgentType, AgentAction, AgentResponse, ActionStatus, RiskLevel

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all healthcare agents in the 8+1 architecture.
    
    Each agent handles specific workflow domains while maintaining
    unified compliance oversight through the governance framework.
    """
    
    def __init__(self, agent_type: AgentType):
        self.agent_type = agent_type
        self.is_active = True
        self.action_history: list[AgentAction] = []
        self.created_at = datetime.utcnow()
        self._confidence_threshold = 0.85
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the agent's display name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Return the agent's description."""
        pass
    
    @property
    def supported_actions(self) -> list[str]:
        """Return list of actions this agent supports."""
        return []
    
    def create_action(
        self,
        action_type: str,
        parameters: dict[str, Any],
        patient_id: Optional[str] = None,
        confidence_score: float = 1.0,
        rationale: str = ""
    ) -> AgentAction:
        """Create a new agent action."""
        risk_level = self._assess_risk(action_type, parameters)
        
        action = AgentAction(
            agent_type=self.agent_type,
            action_type=action_type,
            parameters=parameters,
            patient_id=patient_id,
            risk_level=risk_level,
            confidence_score=confidence_score,
            rationale=rationale,
            requires_approval=risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        )
        
        self.action_history.append(action)
        return action
    
    def _assess_risk(self, action_type: str, parameters: dict) -> RiskLevel:
        """Assess the risk level of an action."""
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
        
        if action_type in critical_actions:
            return RiskLevel.CRITICAL
        elif action_type in high_risk_actions:
            return RiskLevel.HIGH
        elif action_type in medium_risk_actions:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    @abstractmethod
    async def process(
        self,
        action_type: str,
        parameters: dict[str, Any],
        patient_id: Optional[str] = None
    ) -> AgentResponse:
        """Process an action request.
        
        Args:
            action_type: Type of action to perform
            parameters: Action parameters
            patient_id: Optional patient identifier
            
        Returns:
            AgentResponse with results
        """
        pass
    
    def validate_parameters(
        self,
        action_type: str,
        parameters: dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """Validate action parameters.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        return True, None
    
    def get_status(self) -> dict[str, Any]:
        """Get agent status information."""
        return {
            "agent_type": self.agent_type.value,
            "name": self.name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "total_actions": len(self.action_history),
            "supported_actions": self.supported_actions
        }
    
    def get_action_history(
        self,
        limit: int = 100,
        status: Optional[ActionStatus] = None
    ) -> list[AgentAction]:
        """Get action history, optionally filtered by status."""
        history = self.action_history
        
        if status:
            history = [a for a in history if a.status == status]
        
        return sorted(history, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    def set_confidence_threshold(self, threshold: float):
        """Set the confidence threshold for this agent."""
        if 0.0 <= threshold <= 1.0:
            self._confidence_threshold = threshold
        else:
            raise ValueError("Threshold must be between 0.0 and 1.0")
    
    def deactivate(self):
        """Deactivate the agent."""
        self.is_active = False
        logger.info(f"Agent {self.name} deactivated")
    
    def activate(self):
        """Activate the agent."""
        self.is_active = True
        logger.info(f"Agent {self.name} activated")
