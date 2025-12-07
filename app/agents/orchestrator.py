"""Orchestrator Agent (+1) - Central coordination hub for all agent activities."""

import logging
from datetime import datetime
from typing import Optional, Any

from app.models.base import AgentType, AgentAction, AgentResponse, ActionStatus, RiskLevel
from app.agents.base_agent import BaseAgent
from app.governance.governance_engine import GovernanceEngine

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """+1 Orchestrator Agent - Central coordination hub.
    
    Responsibilities:
    - Route incoming requests to appropriate domain agents
    - Enforce governance policies across all operations
    - Maintain unified logging and audit trails
    - Coordinate multi-agent workflows
    - Apply confidence thresholds and escalation rules
    """
    
    def __init__(self, governance_engine: Optional[GovernanceEngine] = None):
        super().__init__(AgentType.ORCHESTRATOR)
        self.governance = governance_engine or GovernanceEngine()
        self.registered_agents: dict[AgentType, BaseAgent] = {}
        self.workflow_states: dict[str, dict] = {}
        self.active_workflows: dict[str, list[str]] = {}
    
    @property
    def name(self) -> str:
        return "Orchestrator Agent"
    
    @property
    def description(self) -> str:
        return (
            "Central coordination hub for all agent activities with unified "
            "compliance oversight. Routes requests, enforces governance, and "
            "coordinates multi-agent workflows."
        )
    
    @property
    def supported_actions(self) -> list[str]:
        return [
            "route_request", "coordinate_workflow", "enforce_governance",
            "escalate_action", "approve_action", "reject_action",
            "get_dashboard_data", "update_configuration"
        ]
    
    def register_agent(self, agent: BaseAgent):
        """Register a domain agent with the orchestrator."""
        self.registered_agents[agent.agent_type] = agent
        logger.info(f"Registered agent: {agent.name} ({agent.agent_type.value})")
    
    def get_agent(self, agent_type: AgentType) -> Optional[BaseAgent]:
        """Get a registered agent by type."""
        return self.registered_agents.get(agent_type)
    
    async def process(
        self,
        action_type: str,
        parameters: dict[str, Any],
        patient_id: Optional[str] = None
    ) -> AgentResponse:
        """Process an orchestrator action."""
        action = self.create_action(
            action_type=action_type,
            parameters=parameters,
            patient_id=patient_id,
            confidence_score=1.0,
            rationale=f"Orchestrator processing {action_type}"
        )
        
        try:
            if action_type == "route_request":
                result = await self._route_request(parameters, patient_id)
            elif action_type == "coordinate_workflow":
                result = await self._coordinate_workflow(parameters, patient_id)
            elif action_type == "enforce_governance":
                result = self._enforce_governance(parameters)
            elif action_type == "escalate_action":
                result = self._escalate_action(parameters)
            elif action_type == "approve_action":
                result = self._approve_action(parameters)
            elif action_type == "reject_action":
                result = self._reject_action(parameters)
            elif action_type == "get_dashboard_data":
                result = self._get_dashboard_data()
            elif action_type == "update_configuration":
                result = self._update_configuration(parameters)
            else:
                result = {"success": False, "error": f"Unknown action: {action_type}"}
            
            action.status = ActionStatus.COMPLETED if result.get("success", True) else ActionStatus.FAILED
            
            return AgentResponse(
                success=result.get("success", True),
                action=action,
                result=result
            )
            
        except Exception as e:
            logger.error(f"Orchestrator error processing {action_type}: {e}")
            action.status = ActionStatus.FAILED
            return AgentResponse(
                success=False,
                action=action,
                error=str(e)
            )
    
    async def _route_request(
        self,
        parameters: dict[str, Any],
        patient_id: Optional[str]
    ) -> dict[str, Any]:
        """Route a request to the appropriate domain agent."""
        target_agent_type = parameters.get("target_agent")
        target_action = parameters.get("action")
        action_params = parameters.get("parameters", {})
        user_id = parameters.get("user_id", "system")
        
        if not target_agent_type or not target_action:
            return {"success": False, "error": "Missing target_agent or action"}
        
        try:
            agent_type = AgentType(target_agent_type)
        except ValueError:
            return {"success": False, "error": f"Invalid agent type: {target_agent_type}"}
        
        agent = self.registered_agents.get(agent_type)
        if not agent:
            return {"success": False, "error": f"Agent not registered: {agent_type.value}"}
        
        if not agent.is_active:
            return {"success": False, "error": f"Agent is inactive: {agent_type.value}"}
        
        logger.info(f"Routing {target_action} to {agent_type.value}")
        
        response = await agent.process(
            action_type=target_action,
            parameters=action_params,
            patient_id=patient_id
        )
        
        return {
            "success": response.success,
            "routed_to": agent_type.value,
            "action": target_action,
            "response": response.result,
            "action_id": response.action.action_id
        }
    
    async def _coordinate_workflow(
        self,
        parameters: dict[str, Any],
        patient_id: Optional[str]
    ) -> dict[str, Any]:
        """Coordinate a multi-agent workflow."""
        workflow_name = parameters.get("workflow_name")
        workflow_steps = parameters.get("steps", [])
        
        if not workflow_name or not workflow_steps:
            return {"success": False, "error": "Missing workflow_name or steps"}
        
        workflow_id = f"wf_{workflow_name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        self.workflow_states[workflow_id] = {
            "name": workflow_name,
            "patient_id": patient_id,
            "status": "IN_PROGRESS",
            "started_at": datetime.utcnow().isoformat(),
            "steps": workflow_steps,
            "completed_steps": [],
            "current_step": 0,
            "results": []
        }
        
        self.active_workflows[workflow_id] = []
        
        for i, step in enumerate(workflow_steps):
            step_agent = step.get("agent")
            step_action = step.get("action")
            step_params = step.get("parameters", {})
            
            logger.info(f"Workflow {workflow_id} executing step {i+1}: {step_agent}.{step_action}")
            
            route_result = await self._route_request(
                parameters={
                    "target_agent": step_agent,
                    "action": step_action,
                    "parameters": step_params
                },
                patient_id=patient_id
            )
            
            self.workflow_states[workflow_id]["results"].append(route_result)
            self.workflow_states[workflow_id]["current_step"] = i + 1
            
            if route_result.get("success"):
                self.workflow_states[workflow_id]["completed_steps"].append(i)
            else:
                if step.get("required", True):
                    self.workflow_states[workflow_id]["status"] = "FAILED"
                    return {
                        "success": False,
                        "workflow_id": workflow_id,
                        "failed_at_step": i,
                        "error": route_result.get("error", "Step failed")
                    }
        
        self.workflow_states[workflow_id]["status"] = "COMPLETED"
        self.workflow_states[workflow_id]["completed_at"] = datetime.utcnow().isoformat()
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "workflow_name": workflow_name,
            "total_steps": len(workflow_steps),
            "completed_steps": len(self.workflow_states[workflow_id]["completed_steps"]),
            "results": self.workflow_states[workflow_id]["results"]
        }
    
    def _enforce_governance(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Enforce governance policies on an action."""
        action_data = parameters.get("action")
        user_id = parameters.get("user_id", "system")
        
        if not action_data:
            return {"success": False, "error": "Missing action data"}
        
        action = AgentAction(**action_data)
        
        response = self.governance.process_action(
            action=action,
            user_id=user_id
        )
        
        return {
            "success": response.success,
            "action_id": response.action.action_id,
            "status": response.action.status.value,
            "result": response.result,
            "escalation_required": response.escalation_required
        }
    
    def _escalate_action(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Escalate an action for human review."""
        action_id = parameters.get("action_id")
        reason = parameters.get("reason", "Manual escalation")
        
        if not action_id:
            return {"success": False, "error": "Missing action_id"}
        
        from app.governance.fallback import EscalationTrigger
        
        action = AgentAction(
            action_id=action_id,
            agent_type=AgentType.ORCHESTRATOR,
            action_type="escalated_action"
        )
        
        escalation_id = self.governance.fallback.trigger_escalation(
            action=action,
            trigger=EscalationTrigger.SAFETY_CONCERN,
            reason=reason
        )
        
        return {
            "success": True,
            "escalation_id": escalation_id,
            "action_id": action_id,
            "reason": reason
        }
    
    def _approve_action(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Approve a pending action."""
        request_id = parameters.get("request_id")
        approver_id = parameters.get("approver_id")
        
        if not request_id or not approver_id:
            return {"success": False, "error": "Missing request_id or approver_id"}
        
        response = self.governance.process_approval(
            request_id=request_id,
            approver_id=approver_id,
            approved=True
        )
        
        return {
            "success": response.success,
            "request_id": request_id,
            "approved_by": approver_id,
            "result": response.result
        }
    
    def _reject_action(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Reject a pending action."""
        request_id = parameters.get("request_id")
        rejector_id = parameters.get("rejector_id")
        reason = parameters.get("reason", "")
        
        if not request_id or not rejector_id:
            return {"success": False, "error": "Missing request_id or rejector_id"}
        
        response = self.governance.process_approval(
            request_id=request_id,
            approver_id=rejector_id,
            approved=False,
            reason=reason
        )
        
        return {
            "success": True,
            "request_id": request_id,
            "rejected_by": rejector_id,
            "reason": reason
        }
    
    def _get_dashboard_data(self) -> dict[str, Any]:
        """Get comprehensive dashboard data."""
        dashboard = self.governance.get_dashboard_data()
        
        dashboard["registered_agents"] = [
            {
                "type": agent.agent_type.value,
                "name": agent.name,
                "is_active": agent.is_active,
                "total_actions": len(agent.action_history)
            }
            for agent in self.registered_agents.values()
        ]
        
        dashboard["active_workflows"] = [
            {
                "workflow_id": wf_id,
                "name": state["name"],
                "status": state["status"],
                "progress": f"{state['current_step']}/{len(state['steps'])}"
            }
            for wf_id, state in self.workflow_states.items()
            if state["status"] == "IN_PROGRESS"
        ]
        
        return {"success": True, **dashboard}
    
    def _update_configuration(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Update governance configuration."""
        updates = parameters.get("updates", {})
        
        if not updates:
            return {"success": False, "error": "No updates provided"}
        
        success = self.governance.update_configuration(updates)
        
        return {
            "success": success,
            "updated_fields": list(updates.keys()),
            "current_config": self.governance.get_configuration()
        }
    
    def get_workflow_status(self, workflow_id: str) -> Optional[dict]:
        """Get the status of a workflow."""
        return self.workflow_states.get(workflow_id)
    
    def get_all_agent_statuses(self) -> list[dict]:
        """Get status of all registered agents."""
        return [agent.get_status() for agent in self.registered_agents.values()]
