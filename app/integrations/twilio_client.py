"""Twilio integration for SMS, voice calls, and IVR."""

import logging
import random
from typing import Optional
from datetime import datetime

from app.integrations.base import BaseIntegrationClient

logger = logging.getLogger(__name__)


class TwilioClient(BaseIntegrationClient):
    """Client for Twilio communication services.
    
    Use Cases:
    - SMS notifications and reminders
    - Voice calls for urgent communications
    - IVR systems for patient interaction
    - Two-way messaging
    """
    
    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_number: Optional[str] = None,
        simulate: bool = True
    ):
        super().__init__(
            api_key=auth_token,
            base_url="https://api.twilio.com",
            timeout=15,
            simulate=simulate
        )
        self.account_sid = account_sid or "PLACEHOLDER_ACCOUNT_SID"
        self.from_number = from_number or "+15551234567"
        
        self.message_templates = {
            "appointment_reminder": (
                "Reminder: You have an appointment on {date} at {time} with {provider}. "
                "Reply CONFIRM to confirm or RESCHEDULE to change."
            ),
            "medication_reminder": (
                "Reminder: Time to take your {medication}. "
                "Dosage: {dosage}. Reply TAKEN when complete."
            ),
            "care_update": (
                "Care Update for {patient_name}: {message}. "
                "Questions? Reply or call {callback_number}."
            ),
            "lab_results": (
                "Your lab results are ready. Please log into the patient portal "
                "or contact your care team for details."
            ),
            "follow_up": (
                "Hi {patient_name}, this is a follow-up from your recent visit. "
                "{message} Reply with any questions."
            )
        }
    
    @property
    def service_name(self) -> str:
        return "twilio"
    
    def send_sms(
        self,
        to_number: str,
        message: str,
        from_number: Optional[str] = None
    ) -> dict:
        """Send an SMS message.
        
        Args:
            to_number: Recipient phone number
            message: Message content
            from_number: Sender phone number (optional)
            
        Returns:
            dict with message SID and status
        """
        endpoint = f"/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        request_payload = {
            "To": to_number,
            "From": from_number or self.from_number,
            "Body": message
        }
        
        if self.simulate:
            latency = self._simulate_latency(base_ms=200, variance_ms=100)
            
            message_sid = f"SM{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"
            
            response = {
                "success": True,
                "message_sid": message_sid,
                "to": to_number,
                "from": from_number or self.from_number,
                "status": "queued",
                "segments": (len(message) // 160) + 1,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self._log_api_call(
                endpoint=endpoint,
                method="POST",
                request_payload=request_payload,
                response_payload={"sid": message_sid, "status": "queued"},
                status_code=201,
                latency_ms=latency
            )
            
            logger.info(f"SMS sent to {to_number[-4:]}: {message_sid}")
            
            return response
        
        return {"success": False, "error": "Live API calls not implemented"}
    
    def send_templated_sms(
        self,
        to_number: str,
        template_name: str,
        template_vars: dict
    ) -> dict:
        """Send an SMS using a predefined template.
        
        Args:
            to_number: Recipient phone number
            template_name: Name of the template to use
            template_vars: Variables to fill in the template
            
        Returns:
            dict with message details
        """
        template = self.message_templates.get(template_name)
        if not template:
            return {"success": False, "error": f"Template '{template_name}' not found"}
        
        try:
            message = template.format(**template_vars)
        except KeyError as e:
            return {"success": False, "error": f"Missing template variable: {e}"}
        
        result = self.send_sms(to_number, message)
        result["template_name"] = template_name
        result["template_vars"] = template_vars
        
        return result
    
    def make_call(
        self,
        to_number: str,
        twiml_url: Optional[str] = None,
        message: Optional[str] = None,
        from_number: Optional[str] = None
    ) -> dict:
        """Initiate a voice call.
        
        Args:
            to_number: Recipient phone number
            twiml_url: URL for TwiML instructions
            message: Simple message to speak (if no twiml_url)
            from_number: Caller ID number
            
        Returns:
            dict with call SID and status
        """
        endpoint = f"/2010-04-01/Accounts/{self.account_sid}/Calls.json"
        request_payload = {
            "To": to_number,
            "From": from_number or self.from_number,
            "Url": twiml_url or "http://example.com/twiml"
        }
        
        if self.simulate:
            latency = self._simulate_latency(base_ms=300, variance_ms=150)
            
            call_sid = f"CA{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"
            
            response = {
                "success": True,
                "call_sid": call_sid,
                "to": to_number,
                "from": from_number or self.from_number,
                "status": "queued",
                "direction": "outbound-api",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self._log_api_call(
                endpoint=endpoint,
                method="POST",
                request_payload=request_payload,
                response_payload={"sid": call_sid, "status": "queued"},
                status_code=201,
                latency_ms=latency
            )
            
            logger.info(f"Call initiated to {to_number[-4:]}: {call_sid}")
            
            return response
        
        return {"success": False, "error": "Live API calls not implemented"}
    
    def send_appointment_reminder(
        self,
        to_number: str,
        patient_name: str,
        appointment_date: str,
        appointment_time: str,
        provider_name: str,
        method: str = "sms"
    ) -> dict:
        """Send an appointment reminder via SMS or voice.
        
        Args:
            to_number: Recipient phone number
            patient_name: Patient's name
            appointment_date: Appointment date
            appointment_time: Appointment time
            provider_name: Provider's name
            method: Communication method (sms or voice)
            
        Returns:
            dict with communication details
        """
        template_vars = {
            "date": appointment_date,
            "time": appointment_time,
            "provider": provider_name
        }
        
        if method == "sms":
            return self.send_templated_sms(
                to_number=to_number,
                template_name="appointment_reminder",
                template_vars=template_vars
            )
        elif method == "voice":
            message = (
                f"Hello {patient_name}, this is a reminder about your appointment "
                f"on {appointment_date} at {appointment_time} with {provider_name}. "
                f"Please press 1 to confirm or 2 to request a callback to reschedule."
            )
            result = self.make_call(to_number=to_number, message=message)
            result["message_content"] = message
            return result
        
        return {"success": False, "error": f"Unknown method: {method}"}
    
    def send_bulk_sms(
        self,
        recipients: list[dict],
        template_name: str
    ) -> dict:
        """Send bulk SMS messages using a template.
        
        Args:
            recipients: List of dicts with 'phone' and template variables
            template_name: Template to use
            
        Returns:
            dict with bulk send results
        """
        results = {
            "success": True,
            "total": len(recipients),
            "sent": 0,
            "failed": 0,
            "details": []
        }
        
        for recipient in recipients:
            phone = recipient.pop("phone", None)
            if not phone:
                results["failed"] += 1
                results["details"].append({"error": "Missing phone number"})
                continue
            
            result = self.send_templated_sms(
                to_number=phone,
                template_name=template_name,
                template_vars=recipient
            )
            
            if result.get("success"):
                results["sent"] += 1
            else:
                results["failed"] += 1
            
            results["details"].append(result)
        
        return results
    
    def get_message_status(self, message_sid: str) -> dict:
        """Get the status of a sent message.
        
        Args:
            message_sid: Message SID to check
            
        Returns:
            dict with message status
        """
        endpoint = f"/2010-04-01/Accounts/{self.account_sid}/Messages/{message_sid}.json"
        
        if self.simulate:
            latency = self._simulate_latency(base_ms=100, variance_ms=50)
            
            statuses = ["queued", "sent", "delivered", "failed"]
            weights = [0.1, 0.2, 0.65, 0.05]
            status = random.choices(statuses, weights=weights)[0]
            
            response = {
                "success": True,
                "message_sid": message_sid,
                "status": status,
                "error_code": None if status != "failed" else 30003,
                "error_message": None if status != "failed" else "Unreachable destination",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self._log_api_call(
                endpoint=endpoint,
                method="GET",
                request_payload={"sid": message_sid},
                response_payload=response,
                status_code=200,
                latency_ms=latency
            )
            
            return response
        
        return {"success": False, "error": "Live API calls not implemented"}
    
    def get_call_status(self, call_sid: str) -> dict:
        """Get the status of a call.
        
        Args:
            call_sid: Call SID to check
            
        Returns:
            dict with call status
        """
        endpoint = f"/2010-04-01/Accounts/{self.account_sid}/Calls/{call_sid}.json"
        
        if self.simulate:
            latency = self._simulate_latency(base_ms=100, variance_ms=50)
            
            statuses = ["queued", "ringing", "in-progress", "completed", "busy", "no-answer", "failed"]
            weights = [0.05, 0.1, 0.1, 0.5, 0.1, 0.1, 0.05]
            status = random.choices(statuses, weights=weights)[0]
            
            response = {
                "success": True,
                "call_sid": call_sid,
                "status": status,
                "duration": random.randint(30, 180) if status == "completed" else 0,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self._log_api_call(
                endpoint=endpoint,
                method="GET",
                request_payload={"sid": call_sid},
                response_payload=response,
                status_code=200,
                latency_ms=latency
            )
            
            return response
        
        return {"success": False, "error": "Live API calls not implemented"}
    
    def generate_twiml_say(self, message: str, voice: str = "alice") -> str:
        """Generate TwiML for text-to-speech.
        
        Args:
            message: Message to speak
            voice: Voice to use
            
        Returns:
            TwiML XML string
        """
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="{voice}">{message}</Say>
</Response>'''
    
    def generate_twiml_gather(
        self,
        prompt: str,
        action_url: str,
        num_digits: int = 1,
        timeout: int = 10
    ) -> str:
        """Generate TwiML for gathering input.
        
        Args:
            prompt: Prompt to speak
            action_url: URL to send input to
            num_digits: Number of digits to gather
            timeout: Timeout in seconds
            
        Returns:
            TwiML XML string
        """
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather numDigits="{num_digits}" action="{action_url}" timeout="{timeout}">
        <Say>{prompt}</Say>
    </Gather>
    <Say>We didn't receive any input. Goodbye.</Say>
</Response>'''
