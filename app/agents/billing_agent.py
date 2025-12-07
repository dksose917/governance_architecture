"""Billing Agent (05) - Handles revenue cycle management and claims processing."""

import logging
import random
from datetime import datetime, date, timedelta
from typing import Optional, Any

from app.models.base import AgentType, AgentAction, AgentResponse, ActionStatus
from app.models.patient import Claim
from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class BillingAgent(BaseAgent):
    """Billing Agent (05) - Revenue Cycle Management.
    
    Handles claims processing, revenue cycle management,
    and billing operations.
    """
    
    def __init__(self):
        super().__init__(AgentType.BILLING)
        self.claims: dict[str, Claim] = {}
        self.patient_claims: dict[str, list[str]] = {}
        self.revenue_summary: dict[str, float] = {
            "submitted": 0.0,
            "approved": 0.0,
            "denied": 0.0,
            "pending": 0.0
        }
    
    @property
    def name(self) -> str:
        return "Billing Agent"
    
    @property
    def description(self) -> str:
        return "Handles revenue cycle management, claims processing, and billing operations."
    
    @property
    def supported_actions(self) -> list[str]:
        return [
            "create_claim", "submit_claim", "check_claim_status",
            "process_remittance", "appeal_denial", "generate_invoice",
            "verify_eligibility", "get_patient_claims", "get_revenue_report"
        ]
    
    async def process(
        self,
        action_type: str,
        parameters: dict[str, Any],
        patient_id: Optional[str] = None
    ) -> AgentResponse:
        """Process a billing action."""
        confidence = self._calculate_confidence(action_type, parameters)
        
        action = self.create_action(
            action_type=action_type,
            parameters=parameters,
            patient_id=patient_id,
            confidence_score=confidence,
            rationale=f"Billing: {action_type}"
        )
        
        try:
            if action_type == "create_claim":
                result = await self._create_claim(patient_id, parameters)
            elif action_type == "submit_claim":
                result = await self._submit_claim(parameters)
            elif action_type == "check_claim_status":
                result = await self._check_claim_status(parameters)
            elif action_type == "process_remittance":
                result = await self._process_remittance(parameters)
            elif action_type == "appeal_denial":
                result = await self._appeal_denial(parameters)
            elif action_type == "generate_invoice":
                result = await self._generate_invoice(patient_id, parameters)
            elif action_type == "verify_eligibility":
                result = await self._verify_eligibility(patient_id, parameters)
            elif action_type == "get_patient_claims":
                result = self._get_patient_claims(patient_id)
            elif action_type == "get_revenue_report":
                result = self._get_revenue_report(parameters)
            else:
                result = {"success": False, "error": f"Unknown action: {action_type}"}
            
            action.status = ActionStatus.COMPLETED if result.get("success", True) else ActionStatus.FAILED
            
            return AgentResponse(
                success=result.get("success", True),
                action=action,
                result=result
            )
            
        except Exception as e:
            logger.error(f"Billing agent error: {e}")
            action.status = ActionStatus.FAILED
            return AgentResponse(success=False, action=action, error=str(e))
    
    def _calculate_confidence(self, action_type: str, parameters: dict) -> float:
        """Calculate confidence score."""
        base_confidence = 0.93
        
        if action_type == "create_claim":
            if parameters.get("diagnosis_codes") and parameters.get("procedure_codes"):
                base_confidence = 0.95
            else:
                base_confidence = 0.82
        
        return min(1.0, max(0.0, base_confidence + random.uniform(-0.03, 0.03)))
    
    async def _create_claim(
        self,
        patient_id: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a new claim."""
        if not patient_id:
            return {"success": False, "error": "Patient ID required"}
        
        required = ["payer_id", "diagnosis_codes", "procedure_codes", "total_charge"]
        missing = [f for f in required if not parameters.get(f)]
        if missing:
            return {"success": False, "error": f"Missing required fields: {missing}"}
        
        service_date = parameters.get("service_date", date.today())
        if isinstance(service_date, str):
            service_date = date.fromisoformat(service_date)
        
        claim = Claim(
            patient_id=patient_id,
            payer_id=parameters["payer_id"],
            service_date=service_date,
            diagnosis_codes=parameters["diagnosis_codes"],
            procedure_codes=parameters["procedure_codes"],
            total_charge=parameters["total_charge"],
            provider_id=parameters.get("provider_id"),
            facility_id=parameters.get("facility_id"),
            status="CREATED"
        )
        
        self.claims[claim.claim_id] = claim
        
        if patient_id not in self.patient_claims:
            self.patient_claims[patient_id] = []
        self.patient_claims[patient_id].append(claim.claim_id)
        
        return {
            "success": True,
            "claim_id": claim.claim_id,
            "patient_id": patient_id,
            "total_charge": claim.total_charge,
            "status": claim.status
        }
    
    async def _submit_claim(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Submit a claim to the payer."""
        claim_id = parameters.get("claim_id")
        
        if not claim_id or claim_id not in self.claims:
            return {"success": False, "error": "Claim not found"}
        
        claim = self.claims[claim_id]
        
        if claim.status not in ["CREATED", "CORRECTED"]:
            return {"success": False, "error": f"Cannot submit claim in status: {claim.status}"}
        
        claim.status = "SUBMITTED"
        claim.submitted_date = datetime.utcnow()
        
        self.revenue_summary["submitted"] += claim.total_charge
        self.revenue_summary["pending"] += claim.total_charge
        
        return {
            "success": True,
            "claim_id": claim_id,
            "status": claim.status,
            "submitted_date": claim.submitted_date.isoformat(),
            "tracking_number": f"TRK{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        }
    
    async def _check_claim_status(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Check the status of a claim."""
        claim_id = parameters.get("claim_id")
        
        if not claim_id or claim_id not in self.claims:
            return {"success": False, "error": "Claim not found"}
        
        claim = self.claims[claim_id]
        
        if claim.status == "SUBMITTED":
            outcomes = ["APPROVED", "DENIED", "PENDING_INFO", "SUBMITTED"]
            weights = [0.7, 0.15, 0.1, 0.05]
            new_status = random.choices(outcomes, weights=weights)[0]
            
            if new_status != claim.status:
                old_status = claim.status
                claim.status = new_status
                
                if new_status == "APPROVED":
                    claim.approved_amount = claim.total_charge * random.uniform(0.8, 1.0)
                    claim.paid_date = datetime.utcnow()
                    self.revenue_summary["approved"] += claim.approved_amount
                    self.revenue_summary["pending"] -= claim.total_charge
                elif new_status == "DENIED":
                    claim.denial_reason = random.choice([
                        "Invalid diagnosis code",
                        "Service not covered",
                        "Prior authorization required",
                        "Duplicate claim"
                    ])
                    self.revenue_summary["denied"] += claim.total_charge
                    self.revenue_summary["pending"] -= claim.total_charge
        
        return {
            "success": True,
            "claim_id": claim_id,
            "status": claim.status,
            "total_charge": claim.total_charge,
            "approved_amount": claim.approved_amount,
            "denial_reason": claim.denial_reason,
            "paid_date": claim.paid_date.isoformat() if claim.paid_date else None
        }
    
    async def _process_remittance(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Process a remittance advice."""
        claim_id = parameters.get("claim_id")
        payment_amount = parameters.get("payment_amount", 0)
        adjustment_codes = parameters.get("adjustment_codes", [])
        
        if not claim_id or claim_id not in self.claims:
            return {"success": False, "error": "Claim not found"}
        
        claim = self.claims[claim_id]
        claim.approved_amount = payment_amount
        claim.paid_date = datetime.utcnow()
        claim.status = "PAID"
        
        return {
            "success": True,
            "claim_id": claim_id,
            "payment_amount": payment_amount,
            "adjustment_codes": adjustment_codes,
            "patient_responsibility": claim.total_charge - payment_amount
        }
    
    async def _appeal_denial(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Appeal a denied claim."""
        claim_id = parameters.get("claim_id")
        appeal_reason = parameters.get("reason", "")
        supporting_docs = parameters.get("supporting_documents", [])
        
        if not claim_id or claim_id not in self.claims:
            return {"success": False, "error": "Claim not found"}
        
        claim = self.claims[claim_id]
        
        if claim.status != "DENIED":
            return {"success": False, "error": "Can only appeal denied claims"}
        
        claim.status = "APPEALED"
        claim.appeal_date = datetime.utcnow()
        
        appeal_id = f"APL{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        return {
            "success": True,
            "claim_id": claim_id,
            "appeal_id": appeal_id,
            "status": claim.status,
            "appeal_date": claim.appeal_date.isoformat()
        }
    
    async def _generate_invoice(
        self,
        patient_id: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate a patient invoice."""
        if not patient_id:
            return {"success": False, "error": "Patient ID required"}
        
        claim_ids = self.patient_claims.get(patient_id, [])
        
        line_items = []
        total_charges = 0.0
        total_payments = 0.0
        
        for claim_id in claim_ids:
            claim = self.claims.get(claim_id)
            if claim and claim.status in ["APPROVED", "PAID"]:
                patient_responsibility = claim.total_charge - (claim.approved_amount or 0)
                line_items.append({
                    "claim_id": claim_id,
                    "service_date": claim.service_date.isoformat(),
                    "total_charge": claim.total_charge,
                    "insurance_paid": claim.approved_amount or 0,
                    "patient_responsibility": patient_responsibility
                })
                total_charges += claim.total_charge
                total_payments += claim.approved_amount or 0
        
        invoice = {
            "invoice_id": f"INV{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "patient_id": patient_id,
            "generated_date": datetime.utcnow().isoformat(),
            "line_items": line_items,
            "total_charges": total_charges,
            "total_insurance_payments": total_payments,
            "patient_balance": total_charges - total_payments,
            "due_date": (date.today() + timedelta(days=30)).isoformat()
        }
        
        return {
            "success": True,
            "invoice": invoice
        }
    
    async def _verify_eligibility(
        self,
        patient_id: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Verify patient insurance eligibility."""
        payer_id = parameters.get("payer_id")
        policy_number = parameters.get("policy_number")
        service_date = parameters.get("service_date", date.today())
        
        is_eligible = random.random() < 0.92
        
        return {
            "success": True,
            "patient_id": patient_id,
            "payer_id": payer_id,
            "policy_number": policy_number,
            "service_date": service_date.isoformat() if isinstance(service_date, date) else service_date,
            "is_eligible": is_eligible,
            "coverage_type": "PPO" if is_eligible else None,
            "copay": random.choice([20, 30, 40, 50]) if is_eligible else None,
            "deductible_remaining": random.uniform(0, 1000) if is_eligible else None
        }
    
    def _get_patient_claims(self, patient_id: str) -> dict[str, Any]:
        """Get all claims for a patient."""
        if not patient_id or patient_id not in self.patient_claims:
            return {"success": True, "claims": [], "count": 0}
        
        claims = []
        for claim_id in self.patient_claims[patient_id]:
            claim = self.claims.get(claim_id)
            if claim:
                claims.append({
                    "claim_id": claim.claim_id,
                    "service_date": claim.service_date.isoformat(),
                    "total_charge": claim.total_charge,
                    "approved_amount": claim.approved_amount,
                    "status": claim.status,
                    "payer_id": claim.payer_id
                })
        
        return {
            "success": True,
            "patient_id": patient_id,
            "claims": claims,
            "count": len(claims)
        }
    
    def _get_revenue_report(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Get revenue cycle report."""
        total_claims = len(self.claims)
        
        status_counts = {}
        for claim in self.claims.values():
            status_counts[claim.status] = status_counts.get(claim.status, 0) + 1
        
        return {
            "success": True,
            "report_date": datetime.utcnow().isoformat(),
            "total_claims": total_claims,
            "status_breakdown": status_counts,
            "revenue_summary": self.revenue_summary,
            "collection_rate": (
                self.revenue_summary["approved"] / self.revenue_summary["submitted"]
                if self.revenue_summary["submitted"] > 0 else 0
            )
        }
