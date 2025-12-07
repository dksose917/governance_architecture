"""Medication Agent (03) - Oversees pharmacy coordination and medication management."""

import logging
import random
from datetime import datetime, date, timedelta
from typing import Optional, Any

from app.models.base import AgentType, AgentAction, AgentResponse, ActionStatus, RiskLevel
from app.models.patient import Medication
from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class MedicationAgent(BaseAgent):
    """Medication Agent (03) - Designed.
    
    Oversees pharmacy coordination, medication reconciliation,
    and adverse event monitoring.
    """
    
    def __init__(self):
        super().__init__(AgentType.MEDICATION)
        self.medications: dict[str, Medication] = {}
        self.patient_medications: dict[str, list[str]] = {}
        self.adverse_events: list[dict] = []
        self.interaction_database = self._load_interaction_database()
    
    @property
    def name(self) -> str:
        return "Medication Agent"
    
    @property
    def description(self) -> str:
        return (
            "Oversees pharmacy coordination, medication reconciliation, "
            "and adverse event monitoring."
        )
    
    @property
    def supported_actions(self) -> list[str]:
        return [
            "add_medication", "update_medication", "discontinue_medication",
            "check_interactions", "reconcile_medications", "report_adverse_event",
            "request_refill", "get_medication_list", "verify_medication"
        ]
    
    def _load_interaction_database(self) -> dict:
        """Load simulated drug interaction database."""
        return {
            ("warfarin", "aspirin"): {"severity": "HIGH", "description": "Increased bleeding risk"},
            ("lisinopril", "potassium"): {"severity": "MEDIUM", "description": "Risk of hyperkalemia"},
            ("metformin", "contrast"): {"severity": "HIGH", "description": "Risk of lactic acidosis"},
            ("simvastatin", "grapefruit"): {"severity": "MEDIUM", "description": "Increased statin levels"},
            ("ssri", "maoi"): {"severity": "CRITICAL", "description": "Serotonin syndrome risk"},
        }
    
    async def process(
        self,
        action_type: str,
        parameters: dict[str, Any],
        patient_id: Optional[str] = None
    ) -> AgentResponse:
        """Process a medication action."""
        confidence = self._calculate_confidence(action_type, parameters)
        
        action = self.create_action(
            action_type=action_type,
            parameters=parameters,
            patient_id=patient_id,
            confidence_score=confidence,
            rationale=f"Medication management: {action_type}"
        )
        
        if action_type in ["add_medication", "update_medication"]:
            action.risk_level = RiskLevel.HIGH
            action.requires_approval = True
        
        try:
            if action_type == "add_medication":
                result = await self._add_medication(patient_id, parameters)
            elif action_type == "update_medication":
                result = await self._update_medication(patient_id, parameters)
            elif action_type == "discontinue_medication":
                result = await self._discontinue_medication(patient_id, parameters)
            elif action_type == "check_interactions":
                result = await self._check_interactions(patient_id, parameters)
            elif action_type == "reconcile_medications":
                result = await self._reconcile_medications(patient_id, parameters)
            elif action_type == "report_adverse_event":
                result = await self._report_adverse_event(patient_id, parameters)
            elif action_type == "request_refill":
                result = await self._request_refill(patient_id, parameters)
            elif action_type == "get_medication_list":
                result = self._get_medication_list(patient_id)
            elif action_type == "verify_medication":
                result = await self._verify_medication(parameters)
            else:
                result = {"success": False, "error": f"Unknown action: {action_type}"}
            
            action.status = ActionStatus.COMPLETED if result.get("success", True) else ActionStatus.FAILED
            
            escalation_required = result.get("requires_review", False)
            
            return AgentResponse(
                success=result.get("success", True),
                action=action,
                result=result,
                escalation_required=escalation_required,
                escalation_reason=result.get("escalation_reason")
            )
            
        except Exception as e:
            logger.error(f"Medication agent error: {e}")
            action.status = ActionStatus.FAILED
            return AgentResponse(success=False, action=action, error=str(e))
    
    def _calculate_confidence(self, action_type: str, parameters: dict) -> float:
        """Calculate confidence score."""
        base_confidence = 0.90
        
        if action_type == "check_interactions":
            base_confidence = 0.95
        elif action_type in ["add_medication", "update_medication"]:
            if parameters.get("drug_name") and parameters.get("dosage"):
                base_confidence = 0.92
            else:
                base_confidence = 0.80
        
        return min(1.0, max(0.0, base_confidence + random.uniform(-0.03, 0.03)))
    
    async def _add_medication(
        self,
        patient_id: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Add a new medication for a patient."""
        if not patient_id:
            return {"success": False, "error": "Patient ID required"}
        
        required = ["drug_name", "dosage", "frequency", "prescriber_id"]
        missing = [f for f in required if not parameters.get(f)]
        if missing:
            return {"success": False, "error": f"Missing required fields: {missing}"}
        
        interaction_check = await self._check_interactions(patient_id, {
            "new_drug": parameters["drug_name"]
        })
        
        medication = Medication(
            patient_id=patient_id,
            drug_name=parameters["drug_name"],
            generic_name=parameters.get("generic_name"),
            dosage=parameters["dosage"],
            route=parameters.get("route", "oral"),
            frequency=parameters["frequency"],
            start_date=date.today(),
            prescriber_id=parameters["prescriber_id"],
            pharmacy_id=parameters.get("pharmacy_id"),
            refills_remaining=parameters.get("refills", 0),
            interactions_checked=True
        )
        
        self.medications[medication.medication_id] = medication
        
        if patient_id not in self.patient_medications:
            self.patient_medications[patient_id] = []
        self.patient_medications[patient_id].append(medication.medication_id)
        
        has_interactions = len(interaction_check.get("interactions", [])) > 0
        
        return {
            "success": True,
            "medication_id": medication.medication_id,
            "patient_id": patient_id,
            "drug_name": medication.drug_name,
            "interactions_found": has_interactions,
            "interactions": interaction_check.get("interactions", []),
            "requires_review": has_interactions,
            "escalation_reason": "Drug interactions detected" if has_interactions else None
        }
    
    async def _update_medication(
        self,
        patient_id: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Update an existing medication."""
        medication_id = parameters.get("medication_id")
        
        if not medication_id or medication_id not in self.medications:
            return {"success": False, "error": "Medication not found"}
        
        medication = self.medications[medication_id]
        
        updatable = ["dosage", "frequency", "route", "refills_remaining", "status"]
        updated = []
        
        for field in updatable:
            if field in parameters:
                setattr(medication, field, parameters[field])
                updated.append(field)
        
        return {
            "success": True,
            "medication_id": medication_id,
            "updated_fields": updated,
            "requires_review": "dosage" in updated
        }
    
    async def _discontinue_medication(
        self,
        patient_id: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Discontinue a medication."""
        medication_id = parameters.get("medication_id")
        
        if not medication_id or medication_id not in self.medications:
            return {"success": False, "error": "Medication not found"}
        
        medication = self.medications[medication_id]
        medication.status = "DISCONTINUED"
        medication.end_date = date.today()
        
        return {
            "success": True,
            "medication_id": medication_id,
            "drug_name": medication.drug_name,
            "discontinued_date": medication.end_date.isoformat(),
            "reason": parameters.get("reason", "Not specified")
        }
    
    async def _check_interactions(
        self,
        patient_id: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Check for drug interactions."""
        new_drug = parameters.get("new_drug", "").lower()
        
        current_meds = []
        if patient_id and patient_id in self.patient_medications:
            for med_id in self.patient_medications[patient_id]:
                med = self.medications.get(med_id)
                if med and med.status == "ACTIVE":
                    current_meds.append(med.drug_name.lower())
        
        interactions = []
        
        for (drug1, drug2), info in self.interaction_database.items():
            if new_drug:
                if (new_drug in drug1 or drug1 in new_drug) and any(drug2 in m or m in drug2 for m in current_meds):
                    interactions.append({
                        "drug1": new_drug,
                        "drug2": drug2,
                        "severity": info["severity"],
                        "description": info["description"]
                    })
                elif (new_drug in drug2 or drug2 in new_drug) and any(drug1 in m or m in drug1 for m in current_meds):
                    interactions.append({
                        "drug1": new_drug,
                        "drug2": drug1,
                        "severity": info["severity"],
                        "description": info["description"]
                    })
        
        return {
            "success": True,
            "patient_id": patient_id,
            "new_drug": new_drug,
            "current_medications": current_meds,
            "interactions": interactions,
            "interaction_count": len(interactions),
            "has_critical": any(i["severity"] == "CRITICAL" for i in interactions)
        }
    
    async def _reconcile_medications(
        self,
        patient_id: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Reconcile medications from different sources."""
        if not patient_id:
            return {"success": False, "error": "Patient ID required"}
        
        external_meds = parameters.get("external_medications", [])
        source = parameters.get("source", "Unknown")
        
        current_med_ids = self.patient_medications.get(patient_id, [])
        current_meds = [self.medications[mid] for mid in current_med_ids if mid in self.medications]
        
        discrepancies = []
        matched = []
        new_meds = []
        
        for ext_med in external_meds:
            ext_name = ext_med.get("drug_name", "").lower()
            found = False
            
            for curr_med in current_meds:
                if ext_name in curr_med.drug_name.lower() or curr_med.drug_name.lower() in ext_name:
                    found = True
                    matched.append(ext_med)
                    
                    if ext_med.get("dosage") != curr_med.dosage:
                        discrepancies.append({
                            "drug": ext_name,
                            "type": "DOSAGE_MISMATCH",
                            "current": curr_med.dosage,
                            "external": ext_med.get("dosage")
                        })
                    break
            
            if not found:
                new_meds.append(ext_med)
        
        return {
            "success": True,
            "patient_id": patient_id,
            "source": source,
            "total_current": len(current_meds),
            "total_external": len(external_meds),
            "matched": len(matched),
            "new_medications": new_meds,
            "discrepancies": discrepancies,
            "requires_review": len(discrepancies) > 0 or len(new_meds) > 0
        }
    
    async def _report_adverse_event(
        self,
        patient_id: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Report an adverse drug event."""
        if not patient_id:
            return {"success": False, "error": "Patient ID required"}
        
        event = {
            "event_id": f"ae_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "patient_id": patient_id,
            "medication_id": parameters.get("medication_id"),
            "drug_name": parameters.get("drug_name"),
            "event_type": parameters.get("event_type", "Unknown"),
            "severity": parameters.get("severity", "MODERATE"),
            "description": parameters.get("description", ""),
            "onset_date": parameters.get("onset_date", date.today().isoformat()),
            "reported_by": parameters.get("reported_by"),
            "reported_at": datetime.utcnow().isoformat(),
            "status": "REPORTED"
        }
        
        self.adverse_events.append(event)
        
        if parameters.get("medication_id") and parameters["medication_id"] in self.medications:
            med = self.medications[parameters["medication_id"]]
            med.adverse_events.append(event["event_id"])
        
        return {
            "success": True,
            "event_id": event["event_id"],
            "patient_id": patient_id,
            "severity": event["severity"],
            "requires_review": event["severity"] in ["SEVERE", "CRITICAL"],
            "escalation_reason": f"Adverse event reported: {event['severity']}" if event["severity"] in ["SEVERE", "CRITICAL"] else None
        }
    
    async def _request_refill(
        self,
        patient_id: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Request a medication refill."""
        medication_id = parameters.get("medication_id")
        
        if not medication_id or medication_id not in self.medications:
            return {"success": False, "error": "Medication not found"}
        
        medication = self.medications[medication_id]
        
        if medication.refills_remaining <= 0:
            return {
                "success": False,
                "error": "No refills remaining",
                "requires_new_prescription": True
            }
        
        medication.refills_remaining -= 1
        medication.last_filled_date = date.today()
        
        return {
            "success": True,
            "medication_id": medication_id,
            "drug_name": medication.drug_name,
            "refills_remaining": medication.refills_remaining,
            "filled_date": medication.last_filled_date.isoformat()
        }
    
    def _get_medication_list(self, patient_id: str) -> dict[str, Any]:
        """Get medication list for a patient."""
        if not patient_id or patient_id not in self.patient_medications:
            return {"success": True, "medications": [], "count": 0}
        
        meds = []
        for med_id in self.patient_medications[patient_id]:
            med = self.medications.get(med_id)
            if med:
                meds.append({
                    "medication_id": med.medication_id,
                    "drug_name": med.drug_name,
                    "dosage": med.dosage,
                    "frequency": med.frequency,
                    "route": med.route,
                    "status": med.status,
                    "start_date": med.start_date.isoformat(),
                    "refills_remaining": med.refills_remaining
                })
        
        return {
            "success": True,
            "patient_id": patient_id,
            "medications": meds,
            "count": len(meds),
            "active_count": len([m for m in meds if m["status"] == "ACTIVE"])
        }
    
    async def _verify_medication(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Verify medication details."""
        drug_name = parameters.get("drug_name", "")
        ndc = parameters.get("ndc")
        
        verified = random.random() < 0.98
        
        return {
            "success": True,
            "drug_name": drug_name,
            "ndc": ndc,
            "verified": verified,
            "verification_source": "Simulated Drug Database",
            "confidence": random.uniform(0.92, 0.99) if verified else random.uniform(0.5, 0.7)
        }
