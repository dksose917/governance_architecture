"""ElevenLabs Voice AI integration for text-to-speech and conversational AI."""

import logging
import random
from typing import Optional
from datetime import datetime

from app.integrations.base import BaseIntegrationClient

logger = logging.getLogger(__name__)


class ElevenLabsClient(BaseIntegrationClient):
    """Client for ElevenLabs Voice AI services.
    
    Use Cases:
    - Text-to-speech for automated voice calls
    - Conversational AI for scheduling interactions
    - Voice-enabled care team updates
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        simulate: bool = True
    ):
        super().__init__(
            api_key=api_key,
            base_url="https://api.elevenlabs.io",
            timeout=30,
            simulate=simulate
        )
        
        self.available_voices = {
            "rachel": {"voice_id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "gender": "female"},
            "drew": {"voice_id": "29vD33N1CtxCmqQRPOHJ", "name": "Drew", "gender": "male"},
            "clyde": {"voice_id": "2EiwWnXFnvU5JabPnv8n", "name": "Clyde", "gender": "male"},
            "paul": {"voice_id": "5Q0t7uMcjvnagumLfvZi", "name": "Paul", "gender": "male"},
            "domi": {"voice_id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi", "gender": "female"},
            "bella": {"voice_id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella", "gender": "female"},
        }
    
    @property
    def service_name(self) -> str:
        return "elevenlabs"
    
    def text_to_speech(
        self,
        text: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        model_id: str = "eleven_monolingual_v1",
        stability: float = 0.5,
        similarity_boost: float = 0.75
    ) -> dict:
        """Convert text to speech audio.
        
        Args:
            text: Text to convert to speech
            voice_id: ElevenLabs voice ID
            model_id: Model to use for synthesis
            stability: Voice stability (0-1)
            similarity_boost: Voice similarity boost (0-1)
            
        Returns:
            dict with audio_data (base64), duration_seconds, and metadata
        """
        endpoint = f"/v1/text-to-speech/{voice_id}"
        request_payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost
            }
        }
        
        if self.simulate:
            latency = self._simulate_latency(base_ms=500, variance_ms=200)
            
            words = len(text.split())
            duration = words * 0.4
            
            response = {
                "success": True,
                "audio_data": f"[SIMULATED_AUDIO_BASE64_{len(text)}_chars]",
                "duration_seconds": duration,
                "voice_id": voice_id,
                "model_id": model_id,
                "characters_used": len(text),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self._log_api_call(
                endpoint=endpoint,
                method="POST",
                request_payload=request_payload,
                response_payload={"success": True, "duration": duration},
                status_code=200,
                latency_ms=latency
            )
            
            return response
        
        return {"success": False, "error": "Live API calls not implemented"}
    
    def generate_voice_message(
        self,
        message_type: str,
        patient_name: str,
        details: dict,
        voice_preference: str = "female"
    ) -> dict:
        """Generate a voice message for healthcare communications.
        
        Args:
            message_type: Type of message (appointment_reminder, care_update, etc.)
            patient_name: Patient's name for personalization
            details: Message-specific details
            voice_preference: Preferred voice gender
            
        Returns:
            dict with generated audio and metadata
        """
        templates = {
            "appointment_reminder": (
                f"Hello {patient_name}, this is a reminder about your upcoming appointment "
                f"on {details.get('date', 'the scheduled date')} at {details.get('time', 'the scheduled time')} "
                f"with {details.get('provider', 'your healthcare provider')}. "
                f"Please arrive 15 minutes early. If you need to reschedule, please call us."
            ),
            "care_update": (
                f"Hello, this is an update regarding {patient_name}'s care. "
                f"{details.get('update_message', 'Please contact us for more information.')} "
                f"If you have any questions, please don't hesitate to reach out to our care team."
            ),
            "medication_reminder": (
                f"Hello {patient_name}, this is a reminder to take your medication: "
                f"{details.get('medication', 'your prescribed medication')}. "
                f"Please take {details.get('dosage', 'as prescribed')} {details.get('instructions', '')}."
            ),
            "follow_up": (
                f"Hello {patient_name}, we're following up on your recent visit. "
                f"{details.get('follow_up_message', 'Please let us know if you have any concerns.')} "
                f"Your health is our priority."
            )
        }
        
        text = templates.get(message_type, f"Hello {patient_name}, {details.get('custom_message', '')}")
        
        voice_id = self._select_voice(voice_preference)
        
        result = self.text_to_speech(text=text, voice_id=voice_id)
        result["message_type"] = message_type
        result["generated_text"] = text
        
        return result
    
    def _select_voice(self, preference: str) -> str:
        """Select a voice based on preference."""
        if preference == "female":
            voices = [v for v in self.available_voices.values() if v["gender"] == "female"]
        elif preference == "male":
            voices = [v for v in self.available_voices.values() if v["gender"] == "male"]
        else:
            voices = list(self.available_voices.values())
        
        return random.choice(voices)["voice_id"] if voices else "21m00Tcm4TlvDq8ikWAM"
    
    def start_conversation(
        self,
        agent_id: str,
        initial_context: dict
    ) -> dict:
        """Start a conversational AI session.
        
        Args:
            agent_id: ElevenLabs conversational agent ID
            initial_context: Context for the conversation
            
        Returns:
            dict with conversation session details
        """
        endpoint = "/v1/convai/conversation"
        request_payload = {
            "agent_id": agent_id,
            "context": initial_context
        }
        
        if self.simulate:
            latency = self._simulate_latency(base_ms=300, variance_ms=100)
            
            response = {
                "success": True,
                "conversation_id": f"conv_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                "agent_id": agent_id,
                "status": "active",
                "created_at": datetime.utcnow().isoformat()
            }
            
            self._log_api_call(
                endpoint=endpoint,
                method="POST",
                request_payload=request_payload,
                response_payload=response,
                status_code=200,
                latency_ms=latency
            )
            
            return response
        
        return {"success": False, "error": "Live API calls not implemented"}
    
    def send_conversation_message(
        self,
        conversation_id: str,
        text: str
    ) -> dict:
        """Send a message in a conversation and get AI response.
        
        Args:
            conversation_id: Active conversation ID
            text: User's message text
            
        Returns:
            dict with AI response text and audio
        """
        endpoint = f"/v1/convai/conversation/{conversation_id}/message"
        request_payload = {"text": text}
        
        if self.simulate:
            latency = self._simulate_latency(base_ms=800, variance_ms=300)
            
            responses = [
                "I understand. Let me help you with that.",
                "Thank you for that information. Is there anything else I can assist you with?",
                "I've noted that down. Would you like me to proceed?",
                "That's helpful to know. Let me check on that for you.",
            ]
            
            ai_response = random.choice(responses)
            
            response = {
                "success": True,
                "conversation_id": conversation_id,
                "user_message": text,
                "ai_response": ai_response,
                "audio_data": f"[SIMULATED_AUDIO_{len(ai_response)}_chars]",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self._log_api_call(
                endpoint=endpoint,
                method="POST",
                request_payload=request_payload,
                response_payload={"ai_response": ai_response[:50] + "..."},
                status_code=200,
                latency_ms=latency
            )
            
            return response
        
        return {"success": False, "error": "Live API calls not implemented"}
    
    def get_voice_info(self, voice_id: str) -> dict:
        """Get information about a specific voice."""
        for voice in self.available_voices.values():
            if voice["voice_id"] == voice_id:
                return {"success": True, **voice}
        
        return {"success": False, "error": "Voice not found"}
    
    def list_available_voices(self) -> list[dict]:
        """List all available voices."""
        return list(self.available_voices.values())
