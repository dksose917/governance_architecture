"""Care Planning Agent (02) - Manages MDS coordination and care team communication."""

import logging
import random
from datetime import datetime, date, timedelta
from typing import Optional, Any

from app.models.base import AgentType, AgentAction, AgentResponse, ActionStatus, RiskLevel
from app.models.patient import CarePlan
from app.agents.base_agent import BaseAgent
from app.integrations.elevenlabs import ElevenLabsClient
from app.integrations.twilio_client import TwilioClient

logger = logging.getLogger(__name__)


class CarePlanningAgent(BaseAgent):
    """Care Planning Agent (02) - Designed.
    
    Manages MDS coordination, interdisciplinary care team communication,
    and plan updates.
    
    Integrates ElevenLabs and Twilio for voice-enabled team updates.
    """
    
    def __init__(
        self,
        elevenlabs_client: Optional[ElevenLabsClient] = None,
        twilio_client: Optional[TwilioClient] = None
    ):
        super().__init__(AgentType.CARE_PLANNING)
        self.elevenlabs = elevenlabs_client or ElevenLabsClient(simulate=True)
        self.twilio = twilio_client or TwilioClient(simulate=True)
        self.care_plans: dict[str, CarePlan] = {}
        self.idt_meetings: list[dict] = []
    
    @property
    def name(self) -> str:
        return "Care Planning Agent"
    
    @property
    def description(self) -> str:
        return (
            "Manages MDS coordination, interdisciplinary care team communication, "
            "and plan updates. Uses ElevenLabs and Twilio for voice-enabled team updates."
        )
    
    @property
    def supported_actions(self) -> list[str]:
        return [
            "create_care_plan", "update_care_plan", "add_goal", "add_intervention",
            "schedule_mds_assessment", "schedule_idt_meeting", "notify_care_team",
            "send_voice_update", "get_care_plan", "review_care_plan"
        ]
    
    async def process(
        self,
        action_type: str,
        parameters: dict[str, Any],
        patient_id: Optional[str] = None
    ) -> AgentResponse:
        """Process a care planning action."""
        confidence = self._calculate_confidence(action_type, parameters)
        
        action = self.create_action(
            action_type=action_type,
            parameters=parameters,
            patient_id=patient_id,
            confidence_score=confidence,
            rationale=f"Care planning: {action_type}"
        )
        
        try:
            if action_type == "create_care_plan":
                result = await self._create_care_plan(patient_id, parameters)
            elif action_type == "update_care_plan":
                result = await self._update_care_plan(patient_id, parameters)
            elif action_type == "add_goal":
                result = await self._add_goal(patient_id, parameters)
            elif action_type == "add_intervention":
                result = await self._add_intervention(patient_id, parameters)
            elif action_type == "schedule_mds_assessment":
                result = await self._schedule_mds_assessment(patient_id, parameters)
            elif action_type == "schedule_idt_meeting":
                result = await self._schedule_idt_meeting(parameters)
            elif action_type == "notify_care_team":
                result = await self._notify_care_team(patient_id, parameters)
            elif action_type == "send_voice_update":
                result = await self._send_voice_update(patient_id, parameters)
            elif action_type == "get_care_plan":
                result = self._get_care_plan(patient_id)
            elif action_type == "review_care_plan":
                result = await self._review_care_plan(patient_id, parameters)
            else:
                result = {"success": False, "error": f"Unknown action: {action_type}"}
            
            action.status = ActionStatus.COMPLETED if result.get("success", True) else ActionStatus.FAILED
            
            return AgentResponse(
                success=result.get("success", True),
                action=action,
                result=result
            )
            
        except Exception as e:
            logger.error(f"Care planning agent error: {e}")
            action.status = ActionStatus.FAILED
            return AgentResponse(success=False, action=action, error=str(e))
    
    def _calculate_confidence(self, action_type: str, parameters: dict) -> float:
        """Calculate confidence score for an action."""
        base_confidence = 0.92
        
        if action_type == "create_care_plan":
            if parameters.get("primary_diagnosis") and parameters.get("goals"):
                base_confidence = 0.95
            else:
                base_confidence = 0.85
        
        noise = random.uniform(-0.03, 0.03)
        return min(1.0, max(0.0, base_confidence + noise))
    
    async def _create_care_plan(
        self,
        patient_id: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a new care plan for a patient."""
        if not patient_id:
            return {"success": False, "error": "Patient ID required"}
        
        if not parameters.get("primary_diagnosis"):
            return {"success": False, "error": "Primary diagnosis required"}
        
        effective_date = parameters.get("effective_date", date.today())
        if isinstance(effective_date, str):
            effective_date = date.fromisoformat(effective_date)
        
        review_date = parameters.get("review_date", effective_date + timedelta(days=90))
        if isinstance(review_date, str):
            review_date = date.fromisoformat(review_date)
        
        care_plan = CarePlan(
            patient_id=patient_id,
            effective_date=effective_date,
            review_date=review_date,
            status="DRAFT",
            primary_diagnosis=parameters["primary_diagnosis"],
            secondary_diagnoses=parameters.get("secondary_diagnoses", []),
            goals=parameters.get("goals", []),
            interventions=parameters.get("interventions", []),
            care_team_members=parameters.get("care_team_members", [])
        )
        
        self.care_plans[care_plan.plan_id] = care_plan
        
        logger.info(f"Care plan created: {care_plan.plan_id} for patient {patient_id}")
        
        return {
            "success": True,
            "plan_id": care_plan.plan_id,
            "patient_id": patient_id,
            "status": care_plan.status,
            "effective_date": effective_date.isoformat(),
            "review_date": review_date.isoformat()
        }
    
    async def _update_care_plan(
        self,
        patient_id: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Update an existing care plan."""
        plan_id = parameters.get("plan_id")
        
        if not plan_id:
            for pid, plan in self.care_plans.items():
                if plan.patient_id == patient_id:
                    plan_id = pid
                    break
        
        if not plan_id or plan_id not in self.care_plans:
            return {"success": False, "error": "Care plan not found"}
        
        plan = self.care_plans[plan_id]
        
        updatable_fields = [
            "status", "primary_diagnosis", "secondary_diagnoses",
            "care_team_members", "next_review_date"
        ]
        
        for field in updatable_fields:
            if field in parameters:
                setattr(plan, field, parameters[field])
        
        return {
            "success": True,
            "plan_id": plan_id,
            "updated_fields": [f for f in updatable_fields if f in parameters]
        }
    
    async def _add_goal(
        self,
        patient_id: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Add a goal to a care plan."""
        plan = self._find_patient_care_plan(patient_id)
        if not plan:
            return {"success": False, "error": "Care plan not found"}
        
        goal = {
            "goal_id": f"goal_{len(plan.goals) + 1}",
            "description": parameters.get("description", ""),
            "target_date": parameters.get("target_date"),
            "status": "ACTIVE",
            "progress": 0,
            "created_at": datetime.utcnow().isoformat()
        }
        
        plan.goals.append(goal)
        
        return {
            "success": True,
            "plan_id": plan.plan_id,
            "goal_id": goal["goal_id"],
            "total_goals": len(plan.goals)
        }
    
    async def _add_intervention(
        self,
        patient_id: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Add an intervention to a care plan."""
        plan = self._find_patient_care_plan(patient_id)
        if not plan:
            return {"success": False, "error": "Care plan not found"}
        
        intervention = {
            "intervention_id": f"int_{len(plan.interventions) + 1}",
            "description": parameters.get("description", ""),
            "frequency": parameters.get("frequency", "As needed"),
            "responsible_party": parameters.get("responsible_party", "Care Team"),
            "goal_id": parameters.get("goal_id"),
            "status": "ACTIVE",
            "created_at": datetime.utcnow().isoformat()
        }
        
        plan.interventions.append(intervention)
        
        return {
            "success": True,
            "plan_id": plan.plan_id,
            "intervention_id": intervention["intervention_id"],
            "total_interventions": len(plan.interventions)
        }
    
    async def _schedule_mds_assessment(
        self,
        patient_id: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Schedule an MDS assessment."""
        plan = self._find_patient_care_plan(patient_id)
        if not plan:
            return {"success": False, "error": "Care plan not found"}
        
        assessment_date = parameters.get("assessment_date", date.today() + timedelta(days=7))
        if isinstance(assessment_date, str):
            assessment_date = date.fromisoformat(assessment_date)
        
        plan.mds_assessment_date = assessment_date
        
        return {
            "success": True,
            "plan_id": plan.plan_id,
            "patient_id": patient_id,
            "mds_assessment_date": assessment_date.isoformat(),
            "assessment_type": parameters.get("assessment_type", "Quarterly")
        }
    
    async def _schedule_idt_meeting(
        self,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Schedule an interdisciplinary team meeting."""
        meeting = {
            "meeting_id": f"idt_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "scheduled_datetime": parameters.get("datetime", datetime.utcnow().isoformat()),
            "patient_ids": parameters.get("patient_ids", []),
            "attendees": parameters.get("attendees", []),
            "agenda": parameters.get("agenda", []),
            "status": "SCHEDULED"
        }
        
        self.idt_meetings.append(meeting)
        
        return {
            "success": True,
            "meeting_id": meeting["meeting_id"],
            "scheduled_datetime": meeting["scheduled_datetime"],
            "patient_count": len(meeting["patient_ids"])
        }
    
    async def _notify_care_team(
        self,
        patient_id: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Notify care team members via SMS."""
        plan = self._find_patient_care_plan(patient_id)
        
        message = parameters.get("message", "Care plan update available")
        recipients = parameters.get("recipients", [])
        
        if not recipients and plan:
            recipients = [{"phone": "+15551234567", "name": member} for member in plan.care_team_members[:3]]
        
        results = []
        for recipient in recipients:
            phone = recipient.get("phone")
            if phone:
                sms_result = self.twilio.send_sms(
                    to_number=phone,
                    message=f"Care Team Update for Patient {patient_id[:8]}: {message}"
                )
                results.append({
                    "recipient": recipient.get("name", phone),
                    "success": sms_result.get("success", False),
                    "message_sid": sms_result.get("message_sid")
                })
        
        return {
            "success": True,
            "patient_id": patient_id,
            "notifications_sent": len([r for r in results if r["success"]]),
            "results": results
        }
    
    async def _send_voice_update(
        self,
        patient_id: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Send a voice update using ElevenLabs and Twilio."""
        update_type = parameters.get("update_type", "care_update")
        recipient_phone = parameters.get("recipient_phone")
        patient_name = parameters.get("patient_name", "the patient")
        
        voice_result = self.elevenlabs.generate_voice_message(
            message_type=update_type,
            patient_name=patient_name,
            details=parameters.get("details", {}),
            voice_preference=parameters.get("voice_preference", "female")
        )
        
        if recipient_phone:
            call_result = self.twilio.make_call(
                to_number=recipient_phone,
                message=voice_result.get("generated_text", "")
            )
            
            return {
                "success": True,
                "patient_id": patient_id,
                "voice_generated": voice_result.get("success", False),
                "call_initiated": call_result.get("success", False),
                "call_sid": call_result.get("call_sid"),
                "message_text": voice_result.get("generated_text")
            }
        
        return {
            "success": True,
            "patient_id": patient_id,
            "voice_generated": voice_result.get("success", False),
            "audio_duration": voice_result.get("duration_seconds"),
            "message_text": voice_result.get("generated_text")
        }
    
    def _get_care_plan(self, patient_id: str) -> dict[str, Any]:
        """Get care plan for a patient."""
        plan = self._find_patient_care_plan(patient_id)
        if not plan:
            return {"success": False, "error": "Care plan not found"}
        
        return {
            "success": True,
            "care_plan": {
                "plan_id": plan.plan_id,
                "patient_id": plan.patient_id,
                "status": plan.status,
                "primary_diagnosis": plan.primary_diagnosis,
                "secondary_diagnoses": plan.secondary_diagnoses,
                "goals_count": len(plan.goals),
                "interventions_count": len(plan.interventions),
                "care_team_members": plan.care_team_members,
                "effective_date": plan.effective_date.isoformat(),
                "review_date": plan.review_date.isoformat(),
                "mds_assessment_date": plan.mds_assessment_date.isoformat() if plan.mds_assessment_date else None
            }
        }
    
    async def _review_care_plan(
        self,
        patient_id: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Review and update care plan status."""
        plan = self._find_patient_care_plan(patient_id)
        if not plan:
            return {"success": False, "error": "Care plan not found"}
        
        reviewer_id = parameters.get("reviewer_id")
        review_notes = parameters.get("notes", "")
        new_status = parameters.get("new_status", plan.status)
        
        plan.status = new_status
        plan.last_idt_meeting = datetime.utcnow()
        
        if parameters.get("extend_review"):
            plan.next_review_date = date.today() + timedelta(days=90)
        
        return {
            "success": True,
            "plan_id": plan.plan_id,
            "new_status": new_status,
            "reviewed_by": reviewer_id,
            "next_review_date": plan.next_review_date.isoformat() if plan.next_review_date else None
        }
    
    def _find_patient_care_plan(self, patient_id: str) -> Optional[CarePlan]:
        """Find the active care plan for a patient."""
        for plan in self.care_plans.values():
            if plan.patient_id == patient_id:
                return plan
        return None
