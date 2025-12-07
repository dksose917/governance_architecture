"""Family Communication Agent (07) - Handles family communication and portal access."""

import logging
import random
from datetime import datetime
from typing import Optional, Any

from app.models.base import AgentType, AgentAction, AgentResponse, ActionStatus
from app.agents.base_agent import BaseAgent
from app.integrations.twilio_client import TwilioClient
from app.integrations.elevenlabs import ElevenLabsClient

logger = logging.getLogger(__name__)


class FamilyCommunicationAgent(BaseAgent):
    """Family Communication Agent (07) - Communication Hub.
    
    Handles family communication and portal access.
    Integrates Twilio for SMS/voice and ElevenLabs for AI-generated voice responses.
    """
    
    def __init__(
        self,
        twilio_client: Optional[TwilioClient] = None,
        elevenlabs_client: Optional[ElevenLabsClient] = None
    ):
        super().__init__(AgentType.FAMILY_COMMUNICATION)
        self.twilio = twilio_client or TwilioClient(simulate=True)
        self.elevenlabs = elevenlabs_client or ElevenLabsClient(simulate=True)
        self.communications: list[dict] = []
        self.family_contacts: dict[str, list[dict]] = {}
        self.portal_access: dict[str, list[dict]] = {}
    
    @property
    def name(self) -> str:
        return "Family Communication Agent"
    
    @property
    def description(self) -> str:
        return (
            "Handles family communication and portal access. "
            "Integrates Twilio for SMS/voice and ElevenLabs for AI-generated voice responses."
        )
    
    @property
    def supported_actions(self) -> list[str]:
        return [
            "send_update", "send_voice_message", "register_family_contact",
            "grant_portal_access", "revoke_portal_access", "send_bulk_notification",
            "schedule_call", "get_communication_history", "verify_contact"
        ]
    
    async def process(
        self,
        action_type: str,
        parameters: dict[str, Any],
        patient_id: Optional[str] = None
    ) -> AgentResponse:
        """Process a family communication action."""
        confidence = self._calculate_confidence(action_type, parameters)
        
        action = self.create_action(
            action_type=action_type,
            parameters=parameters,
            patient_id=patient_id,
            confidence_score=confidence,
            rationale=f"Family communication: {action_type}"
        )
        
        try:
            if action_type == "send_update":
                result = await self._send_update(patient_id, parameters)
            elif action_type == "send_voice_message":
                result = await self._send_voice_message(patient_id, parameters)
            elif action_type == "register_family_contact":
                result = await self._register_family_contact(patient_id, parameters)
            elif action_type == "grant_portal_access":
                result = await self._grant_portal_access(patient_id, parameters)
            elif action_type == "revoke_portal_access":
                result = await self._revoke_portal_access(patient_id, parameters)
            elif action_type == "send_bulk_notification":
                result = await self._send_bulk_notification(parameters)
            elif action_type == "schedule_call":
                result = await self._schedule_call(patient_id, parameters)
            elif action_type == "get_communication_history":
                result = self._get_communication_history(patient_id)
            elif action_type == "verify_contact":
                result = await self._verify_contact(parameters)
            else:
                result = {"success": False, "error": f"Unknown action: {action_type}"}
            
            action.status = ActionStatus.COMPLETED if result.get("success", True) else ActionStatus.FAILED
            
            return AgentResponse(
                success=result.get("success", True),
                action=action,
                result=result
            )
            
        except Exception as e:
            logger.error(f"Family communication agent error: {e}")
            action.status = ActionStatus.FAILED
            return AgentResponse(success=False, action=action, error=str(e))
    
    def _calculate_confidence(self, action_type: str, parameters: dict) -> float:
        """Calculate confidence score."""
        base_confidence = 0.94
        
        if action_type == "send_voice_message":
            base_confidence = 0.92
        elif action_type == "verify_contact":
            base_confidence = 0.96
        
        return min(1.0, max(0.0, base_confidence + random.uniform(-0.02, 0.02)))
    
    async def _send_update(
        self,
        patient_id: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Send an update to family members."""
        if not patient_id:
            return {"success": False, "error": "Patient ID required"}
        
        message = parameters.get("message", "")
        update_type = parameters.get("update_type", "general")
        recipients = parameters.get("recipients", [])
        
        if not recipients and patient_id in self.family_contacts:
            recipients = [
                {"phone": c["phone"], "name": c["name"]}
                for c in self.family_contacts[patient_id]
                if c.get("receive_updates", True)
            ]
        
        if not recipients:
            return {"success": False, "error": "No recipients found"}
        
        results = []
        for recipient in recipients:
            phone = recipient.get("phone")
            if phone:
                sms_result = self.twilio.send_templated_sms(
                    to_number=phone,
                    template_name="care_update",
                    template_vars={
                        "patient_name": parameters.get("patient_name", "your family member"),
                        "message": message,
                        "callback_number": parameters.get("callback_number", "our care team")
                    }
                )
                results.append({
                    "recipient": recipient.get("name", phone),
                    "success": sms_result.get("success", False),
                    "message_sid": sms_result.get("message_sid")
                })
        
        communication_record = {
            "communication_id": f"COM{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "patient_id": patient_id,
            "type": "SMS",
            "update_type": update_type,
            "message": message,
            "recipients": len(results),
            "successful": len([r for r in results if r["success"]]),
            "timestamp": datetime.utcnow().isoformat()
        }
        self.communications.append(communication_record)
        
        return {
            "success": True,
            "communication_id": communication_record["communication_id"],
            "recipients_notified": len([r for r in results if r["success"]]),
            "results": results
        }
    
    async def _send_voice_message(
        self,
        patient_id: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Send an AI-generated voice message."""
        if not patient_id:
            return {"success": False, "error": "Patient ID required"}
        
        message_type = parameters.get("message_type", "care_update")
        recipient_phone = parameters.get("recipient_phone")
        patient_name = parameters.get("patient_name", "your family member")
        
        voice_result = self.elevenlabs.generate_voice_message(
            message_type=message_type,
            patient_name=patient_name,
            details=parameters.get("details", {}),
            voice_preference=parameters.get("voice_preference", "female")
        )
        
        if recipient_phone and voice_result.get("success"):
            call_result = self.twilio.make_call(
                to_number=recipient_phone,
                message=voice_result.get("generated_text", "")
            )
            
            communication_record = {
                "communication_id": f"COM{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                "patient_id": patient_id,
                "type": "VOICE",
                "message_type": message_type,
                "recipient_phone": recipient_phone[-4:],
                "call_sid": call_result.get("call_sid"),
                "timestamp": datetime.utcnow().isoformat()
            }
            self.communications.append(communication_record)
            
            return {
                "success": True,
                "communication_id": communication_record["communication_id"],
                "voice_generated": True,
                "call_initiated": call_result.get("success", False),
                "call_sid": call_result.get("call_sid"),
                "message_text": voice_result.get("generated_text")
            }
        
        return {
            "success": voice_result.get("success", False),
            "voice_generated": voice_result.get("success", False),
            "audio_duration": voice_result.get("duration_seconds"),
            "message_text": voice_result.get("generated_text"),
            "error": "No recipient phone provided" if not recipient_phone else None
        }
    
    async def _register_family_contact(
        self,
        patient_id: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Register a family contact for a patient."""
        if not patient_id:
            return {"success": False, "error": "Patient ID required"}
        
        required = ["name", "phone", "relationship"]
        missing = [f for f in required if not parameters.get(f)]
        if missing:
            return {"success": False, "error": f"Missing required fields: {missing}"}
        
        contact = {
            "contact_id": f"FC{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "name": parameters["name"],
            "phone": parameters["phone"],
            "email": parameters.get("email"),
            "relationship": parameters["relationship"],
            "is_primary": parameters.get("is_primary", False),
            "receive_updates": parameters.get("receive_updates", True),
            "authorized_phi": parameters.get("authorized_phi", False),
            "registered_at": datetime.utcnow().isoformat()
        }
        
        if patient_id not in self.family_contacts:
            self.family_contacts[patient_id] = []
        self.family_contacts[patient_id].append(contact)
        
        return {
            "success": True,
            "contact_id": contact["contact_id"],
            "patient_id": patient_id,
            "name": contact["name"],
            "relationship": contact["relationship"]
        }
    
    async def _grant_portal_access(
        self,
        patient_id: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Grant portal access to a family member."""
        if not patient_id:
            return {"success": False, "error": "Patient ID required"}
        
        contact_id = parameters.get("contact_id")
        access_level = parameters.get("access_level", "VIEW_ONLY")
        
        access_record = {
            "access_id": f"PA{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "contact_id": contact_id,
            "access_level": access_level,
            "granted_at": datetime.utcnow().isoformat(),
            "granted_by": parameters.get("granted_by"),
            "expires_at": parameters.get("expires_at"),
            "status": "ACTIVE"
        }
        
        if patient_id not in self.portal_access:
            self.portal_access[patient_id] = []
        self.portal_access[patient_id].append(access_record)
        
        return {
            "success": True,
            "access_id": access_record["access_id"],
            "patient_id": patient_id,
            "contact_id": contact_id,
            "access_level": access_level
        }
    
    async def _revoke_portal_access(
        self,
        patient_id: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Revoke portal access from a family member."""
        if not patient_id:
            return {"success": False, "error": "Patient ID required"}
        
        access_id = parameters.get("access_id")
        
        if patient_id in self.portal_access:
            for access in self.portal_access[patient_id]:
                if access["access_id"] == access_id:
                    access["status"] = "REVOKED"
                    access["revoked_at"] = datetime.utcnow().isoformat()
                    access["revoked_by"] = parameters.get("revoked_by")
                    
                    return {
                        "success": True,
                        "access_id": access_id,
                        "status": "REVOKED"
                    }
        
        return {"success": False, "error": "Access record not found"}
    
    async def _send_bulk_notification(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Send bulk notifications to multiple families."""
        patient_ids = parameters.get("patient_ids", [])
        message = parameters.get("message", "")
        notification_type = parameters.get("notification_type", "general")
        
        results = []
        
        for patient_id in patient_ids:
            if patient_id in self.family_contacts:
                for contact in self.family_contacts[patient_id]:
                    if contact.get("receive_updates", True):
                        sms_result = self.twilio.send_sms(
                            to_number=contact["phone"],
                            message=message
                        )
                        results.append({
                            "patient_id": patient_id,
                            "contact_name": contact["name"],
                            "success": sms_result.get("success", False)
                        })
        
        return {
            "success": True,
            "total_notifications": len(results),
            "successful": len([r for r in results if r["success"]]),
            "notification_type": notification_type
        }
    
    async def _schedule_call(
        self,
        patient_id: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Schedule a call with family members."""
        if not patient_id:
            return {"success": False, "error": "Patient ID required"}
        
        scheduled_call = {
            "call_id": f"SC{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "patient_id": patient_id,
            "scheduled_datetime": parameters.get("datetime"),
            "contact_id": parameters.get("contact_id"),
            "purpose": parameters.get("purpose", "Care update"),
            "caller_id": parameters.get("caller_id"),
            "status": "SCHEDULED",
            "created_at": datetime.utcnow().isoformat()
        }
        
        return {
            "success": True,
            "call_id": scheduled_call["call_id"],
            "scheduled_datetime": scheduled_call["scheduled_datetime"],
            "status": scheduled_call["status"]
        }
    
    def _get_communication_history(self, patient_id: str) -> dict[str, Any]:
        """Get communication history for a patient."""
        if not patient_id:
            return {"success": True, "communications": [], "count": 0}
        
        patient_comms = [
            c for c in self.communications
            if c.get("patient_id") == patient_id
        ]
        
        return {
            "success": True,
            "patient_id": patient_id,
            "communications": patient_comms,
            "count": len(patient_comms),
            "family_contacts": len(self.family_contacts.get(patient_id, []))
        }
    
    async def _verify_contact(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Verify a contact's phone number."""
        phone = parameters.get("phone")
        
        if not phone:
            return {"success": False, "error": "Phone number required"}
        
        verification_code = f"{random.randint(100000, 999999)}"
        
        sms_result = self.twilio.send_sms(
            to_number=phone,
            message=f"Your verification code is: {verification_code}. This code expires in 10 minutes."
        )
        
        return {
            "success": sms_result.get("success", False),
            "verification_sent": sms_result.get("success", False),
            "message_sid": sms_result.get("message_sid"),
            "expires_in_minutes": 10
        }
