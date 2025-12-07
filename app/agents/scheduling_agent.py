"""Scheduling Agent (08) - Manages appointments and therapy coordination."""

import logging
import random
from datetime import datetime, date, timedelta, time
from typing import Optional, Any

from app.models.base import AgentType, AgentAction, AgentResponse, ActionStatus
from app.models.patient import Appointment
from app.agents.base_agent import BaseAgent
from app.integrations.twilio_client import TwilioClient
from app.integrations.elevenlabs import ElevenLabsClient

logger = logging.getLogger(__name__)


class SchedulingAgent(BaseAgent):
    """Scheduling Agent (08) - Appointment Management.
    
    Manages appointments and therapy coordination.
    Uses Twilio and ElevenLabs for automated reminders and voice scheduling.
    """
    
    def __init__(
        self,
        twilio_client: Optional[TwilioClient] = None,
        elevenlabs_client: Optional[ElevenLabsClient] = None
    ):
        super().__init__(AgentType.SCHEDULING)
        self.twilio = twilio_client or TwilioClient(simulate=True)
        self.elevenlabs = elevenlabs_client or ElevenLabsClient(simulate=True)
        self.appointments: dict[str, Appointment] = {}
        self.patient_appointments: dict[str, list[str]] = {}
        self.provider_schedules: dict[str, list[dict]] = {}
        self.reminders_sent: list[dict] = []
    
    @property
    def name(self) -> str:
        return "Scheduling Agent"
    
    @property
    def description(self) -> str:
        return (
            "Manages appointments and therapy coordination. "
            "Uses Twilio and ElevenLabs for automated reminders and voice scheduling."
        )
    
    @property
    def supported_actions(self) -> list[str]:
        return [
            "schedule_appointment", "reschedule_appointment", "cancel_appointment",
            "check_availability", "send_reminder", "send_voice_reminder",
            "confirm_appointment", "get_patient_appointments", "get_provider_schedule"
        ]
    
    async def process(
        self,
        action_type: str,
        parameters: dict[str, Any],
        patient_id: Optional[str] = None
    ) -> AgentResponse:
        """Process a scheduling action."""
        confidence = self._calculate_confidence(action_type, parameters)
        
        action = self.create_action(
            action_type=action_type,
            parameters=parameters,
            patient_id=patient_id,
            confidence_score=confidence,
            rationale=f"Scheduling: {action_type}"
        )
        
        try:
            if action_type == "schedule_appointment":
                result = await self._schedule_appointment(patient_id, parameters)
            elif action_type == "reschedule_appointment":
                result = await self._reschedule_appointment(parameters)
            elif action_type == "cancel_appointment":
                result = await self._cancel_appointment(parameters)
            elif action_type == "check_availability":
                result = await self._check_availability(parameters)
            elif action_type == "send_reminder":
                result = await self._send_reminder(parameters)
            elif action_type == "send_voice_reminder":
                result = await self._send_voice_reminder(parameters)
            elif action_type == "confirm_appointment":
                result = await self._confirm_appointment(parameters)
            elif action_type == "get_patient_appointments":
                result = self._get_patient_appointments(patient_id)
            elif action_type == "get_provider_schedule":
                result = self._get_provider_schedule(parameters)
            else:
                result = {"success": False, "error": f"Unknown action: {action_type}"}
            
            action.status = ActionStatus.COMPLETED if result.get("success", True) else ActionStatus.FAILED
            
            return AgentResponse(
                success=result.get("success", True),
                action=action,
                result=result
            )
            
        except Exception as e:
            logger.error(f"Scheduling agent error: {e}")
            action.status = ActionStatus.FAILED
            return AgentResponse(success=False, action=action, error=str(e))
    
    def _calculate_confidence(self, action_type: str, parameters: dict) -> float:
        """Calculate confidence score."""
        base_confidence = 0.95
        
        if action_type == "check_availability":
            base_confidence = 0.98
        elif action_type == "send_voice_reminder":
            base_confidence = 0.92
        
        return min(1.0, max(0.0, base_confidence + random.uniform(-0.02, 0.02)))
    
    async def _schedule_appointment(
        self,
        patient_id: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Schedule a new appointment."""
        if not patient_id:
            return {"success": False, "error": "Patient ID required"}
        
        required = ["provider_id", "appointment_type", "date", "time"]
        missing = [f for f in required if not parameters.get(f)]
        if missing:
            return {"success": False, "error": f"Missing required fields: {missing}"}
        
        appt_date = parameters["date"]
        if isinstance(appt_date, str):
            appt_date = date.fromisoformat(appt_date)
        
        appt_time = parameters["time"]
        if isinstance(appt_time, str):
            hour, minute = map(int, appt_time.split(":"))
            appt_time = time(hour, minute)
        
        availability = await self._check_availability({
            "provider_id": parameters["provider_id"],
            "date": appt_date.isoformat(),
            "time": f"{appt_time.hour:02d}:{appt_time.minute:02d}"
        })
        
        if not availability.get("available", True):
            return {
                "success": False,
                "error": "Requested time slot is not available",
                "alternative_slots": availability.get("alternative_slots", [])
            }
        
        appointment = Appointment(
            patient_id=patient_id,
            provider_id=parameters["provider_id"],
            appointment_type=parameters["appointment_type"],
            scheduled_date=appt_date,
            scheduled_time=appt_time,
            duration_minutes=parameters.get("duration_minutes", 30),
            location=parameters.get("location", "Main Clinic"),
            notes=parameters.get("notes", ""),
            status="SCHEDULED"
        )
        
        self.appointments[appointment.appointment_id] = appointment
        
        if patient_id not in self.patient_appointments:
            self.patient_appointments[patient_id] = []
        self.patient_appointments[patient_id].append(appointment.appointment_id)
        
        provider_id = parameters["provider_id"]
        if provider_id not in self.provider_schedules:
            self.provider_schedules[provider_id] = []
        self.provider_schedules[provider_id].append({
            "appointment_id": appointment.appointment_id,
            "date": appt_date.isoformat(),
            "time": f"{appt_time.hour:02d}:{appt_time.minute:02d}",
            "patient_id": patient_id
        })
        
        return {
            "success": True,
            "appointment_id": appointment.appointment_id,
            "patient_id": patient_id,
            "provider_id": provider_id,
            "date": appt_date.isoformat(),
            "time": f"{appt_time.hour:02d}:{appt_time.minute:02d}",
            "appointment_type": appointment.appointment_type,
            "status": appointment.status
        }
    
    async def _reschedule_appointment(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Reschedule an existing appointment."""
        appointment_id = parameters.get("appointment_id")
        
        if not appointment_id or appointment_id not in self.appointments:
            return {"success": False, "error": "Appointment not found"}
        
        appointment = self.appointments[appointment_id]
        
        new_date = parameters.get("new_date")
        new_time = parameters.get("new_time")
        
        if new_date:
            if isinstance(new_date, str):
                new_date = date.fromisoformat(new_date)
            appointment.scheduled_date = new_date
        
        if new_time:
            if isinstance(new_time, str):
                hour, minute = map(int, new_time.split(":"))
                new_time = time(hour, minute)
            appointment.scheduled_time = new_time
        
        appointment.status = "RESCHEDULED"
        
        return {
            "success": True,
            "appointment_id": appointment_id,
            "new_date": appointment.scheduled_date.isoformat(),
            "new_time": f"{appointment.scheduled_time.hour:02d}:{appointment.scheduled_time.minute:02d}",
            "status": appointment.status
        }
    
    async def _cancel_appointment(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Cancel an appointment."""
        appointment_id = parameters.get("appointment_id")
        
        if not appointment_id or appointment_id not in self.appointments:
            return {"success": False, "error": "Appointment not found"}
        
        appointment = self.appointments[appointment_id]
        appointment.status = "CANCELLED"
        appointment.cancellation_reason = parameters.get("reason", "Patient request")
        
        return {
            "success": True,
            "appointment_id": appointment_id,
            "status": appointment.status,
            "cancellation_reason": appointment.cancellation_reason
        }
    
    async def _check_availability(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Check provider availability."""
        provider_id = parameters.get("provider_id")
        check_date = parameters.get("date")
        check_time = parameters.get("time")
        
        if isinstance(check_date, str):
            check_date = date.fromisoformat(check_date)
        
        booked_slots = []
        if provider_id in self.provider_schedules:
            for slot in self.provider_schedules[provider_id]:
                if slot["date"] == check_date.isoformat():
                    booked_slots.append(slot["time"])
        
        is_available = check_time not in booked_slots if check_time else True
        
        available_slots = []
        for hour in range(8, 17):
            for minute in [0, 30]:
                slot_time = f"{hour:02d}:{minute:02d}"
                if slot_time not in booked_slots:
                    available_slots.append(slot_time)
        
        return {
            "success": True,
            "provider_id": provider_id,
            "date": check_date.isoformat() if check_date else None,
            "requested_time": check_time,
            "available": is_available,
            "available_slots": available_slots[:10],
            "booked_slots_count": len(booked_slots)
        }
    
    async def _send_reminder(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Send an SMS appointment reminder."""
        appointment_id = parameters.get("appointment_id")
        
        if not appointment_id or appointment_id not in self.appointments:
            return {"success": False, "error": "Appointment not found"}
        
        appointment = self.appointments[appointment_id]
        recipient_phone = parameters.get("phone")
        patient_name = parameters.get("patient_name", "Patient")
        
        if not recipient_phone:
            return {"success": False, "error": "Phone number required"}
        
        sms_result = self.twilio.send_appointment_reminder(
            to_number=recipient_phone,
            patient_name=patient_name,
            appointment_date=appointment.scheduled_date.isoformat(),
            appointment_time=f"{appointment.scheduled_time.hour:02d}:{appointment.scheduled_time.minute:02d}",
            provider_name=parameters.get("provider_name", "your provider"),
            method="sms"
        )
        
        reminder_record = {
            "reminder_id": f"REM{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "appointment_id": appointment_id,
            "type": "SMS",
            "sent_at": datetime.utcnow().isoformat(),
            "success": sms_result.get("success", False),
            "message_sid": sms_result.get("message_sid")
        }
        self.reminders_sent.append(reminder_record)
        
        return {
            "success": sms_result.get("success", False),
            "reminder_id": reminder_record["reminder_id"],
            "appointment_id": appointment_id,
            "message_sid": sms_result.get("message_sid")
        }
    
    async def _send_voice_reminder(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Send a voice appointment reminder using ElevenLabs and Twilio."""
        appointment_id = parameters.get("appointment_id")
        
        if not appointment_id or appointment_id not in self.appointments:
            return {"success": False, "error": "Appointment not found"}
        
        appointment = self.appointments[appointment_id]
        recipient_phone = parameters.get("phone")
        patient_name = parameters.get("patient_name", "Patient")
        
        if not recipient_phone:
            return {"success": False, "error": "Phone number required"}
        
        voice_result = self.elevenlabs.generate_voice_message(
            message_type="appointment_reminder",
            patient_name=patient_name,
            details={
                "date": appointment.scheduled_date.strftime("%B %d"),
                "time": appointment.scheduled_time.strftime("%I:%M %p"),
                "provider": parameters.get("provider_name", "your healthcare provider")
            },
            voice_preference=parameters.get("voice_preference", "female")
        )
        
        if voice_result.get("success"):
            call_result = self.twilio.make_call(
                to_number=recipient_phone,
                message=voice_result.get("generated_text", "")
            )
            
            reminder_record = {
                "reminder_id": f"REM{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                "appointment_id": appointment_id,
                "type": "VOICE",
                "sent_at": datetime.utcnow().isoformat(),
                "success": call_result.get("success", False),
                "call_sid": call_result.get("call_sid")
            }
            self.reminders_sent.append(reminder_record)
            
            return {
                "success": call_result.get("success", False),
                "reminder_id": reminder_record["reminder_id"],
                "appointment_id": appointment_id,
                "call_sid": call_result.get("call_sid"),
                "message_text": voice_result.get("generated_text")
            }
        
        return {
            "success": False,
            "error": "Failed to generate voice message"
        }
    
    async def _confirm_appointment(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Confirm an appointment."""
        appointment_id = parameters.get("appointment_id")
        
        if not appointment_id or appointment_id not in self.appointments:
            return {"success": False, "error": "Appointment not found"}
        
        appointment = self.appointments[appointment_id]
        appointment.status = "CONFIRMED"
        appointment.confirmed_at = datetime.utcnow()
        
        return {
            "success": True,
            "appointment_id": appointment_id,
            "status": appointment.status,
            "confirmed_at": appointment.confirmed_at.isoformat()
        }
    
    def _get_patient_appointments(self, patient_id: str) -> dict[str, Any]:
        """Get all appointments for a patient."""
        if not patient_id or patient_id not in self.patient_appointments:
            return {"success": True, "appointments": [], "count": 0}
        
        appointments = []
        for appt_id in self.patient_appointments[patient_id]:
            appt = self.appointments.get(appt_id)
            if appt:
                appointments.append({
                    "appointment_id": appt.appointment_id,
                    "provider_id": appt.provider_id,
                    "appointment_type": appt.appointment_type,
                    "date": appt.scheduled_date.isoformat(),
                    "time": f"{appt.scheduled_time.hour:02d}:{appt.scheduled_time.minute:02d}",
                    "duration_minutes": appt.duration_minutes,
                    "location": appt.location,
                    "status": appt.status
                })
        
        upcoming = [a for a in appointments if a["status"] in ["SCHEDULED", "CONFIRMED"]]
        
        return {
            "success": True,
            "patient_id": patient_id,
            "appointments": appointments,
            "count": len(appointments),
            "upcoming_count": len(upcoming)
        }
    
    def _get_provider_schedule(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Get provider schedule."""
        provider_id = parameters.get("provider_id")
        schedule_date = parameters.get("date", date.today().isoformat())
        
        if not provider_id:
            return {"success": False, "error": "Provider ID required"}
        
        schedule = []
        if provider_id in self.provider_schedules:
            for slot in self.provider_schedules[provider_id]:
                if slot["date"] == schedule_date:
                    appt = self.appointments.get(slot["appointment_id"])
                    if appt:
                        schedule.append({
                            "appointment_id": slot["appointment_id"],
                            "time": slot["time"],
                            "patient_id": slot["patient_id"],
                            "appointment_type": appt.appointment_type,
                            "duration_minutes": appt.duration_minutes,
                            "status": appt.status
                        })
        
        schedule.sort(key=lambda x: x["time"])
        
        return {
            "success": True,
            "provider_id": provider_id,
            "date": schedule_date,
            "schedule": schedule,
            "appointment_count": len(schedule)
        }
