"""Healthcare Agent Framework - FastAPI Backend.

8+1 Agent Architecture for Healthcare Workflows with Five-Layer Governance.
"""

import logging
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.models.base import AgentType
from app.governance.governance_engine import GovernanceEngine
from app.agents.orchestrator import OrchestratorAgent
from app.agents.intake_agent import IntakeAgent
from app.agents.care_planning_agent import CarePlanningAgent
from app.agents.medication_agent import MedicationAgent
from app.agents.documentation_agent import DocumentationAgent
from app.agents.billing_agent import BillingAgent
from app.agents.compliance_agent import ComplianceAgent
from app.agents.family_communication_agent import FamilyCommunicationAgent
from app.agents.scheduling_agent import SchedulingAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

governance_engine: Optional[GovernanceEngine] = None
orchestrator: Optional[OrchestratorAgent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the agent framework on startup."""
    global governance_engine, orchestrator
    
    logger.info("Initializing Healthcare Agent Framework...")
    
    governance_engine = GovernanceEngine()
    orchestrator = OrchestratorAgent(governance_engine=governance_engine)
    
    intake_agent = IntakeAgent()
    care_planning_agent = CarePlanningAgent()
    medication_agent = MedicationAgent()
    documentation_agent = DocumentationAgent()
    billing_agent = BillingAgent()
    compliance_agent = ComplianceAgent(bias_monitor=governance_engine.bias_monitor)
    family_comm_agent = FamilyCommunicationAgent()
    scheduling_agent = SchedulingAgent()
    
    orchestrator.register_agent(intake_agent)
    orchestrator.register_agent(care_planning_agent)
    orchestrator.register_agent(medication_agent)
    orchestrator.register_agent(documentation_agent)
    orchestrator.register_agent(billing_agent)
    orchestrator.register_agent(compliance_agent)
    orchestrator.register_agent(family_comm_agent)
    orchestrator.register_agent(scheduling_agent)
    
    logger.info("Healthcare Agent Framework initialized with 8+1 agents")
    
    yield
    
    logger.info("Shutting down Healthcare Agent Framework...")


app = FastAPI(
    title="Healthcare Agent Framework",
    description="8+1 Agent Architecture for Healthcare Workflows with Five-Layer Governance",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PatientRegistrationRequest(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: str
    phone: str
    gender: Optional[str] = "Unknown"
    email: Optional[str] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None


class InsuranceVerificationRequest(BaseModel):
    payer_name: str
    policy_number: str
    subscriber_name: str
    group_number: Optional[str] = None
    subscriber_relationship: Optional[str] = "Self"


class AIMSScreeningRequest(BaseModel):
    chief_complaint: str
    medical_history: Optional[list[str]] = []
    current_medications: Optional[list[str]] = []
    allergies: Optional[list[str]] = []
    vital_signs: Optional[dict] = {}
    pain_level: Optional[int] = None
    fall_risk_score: Optional[float] = None
    cognitive_status: Optional[str] = None
    screener_id: Optional[str] = None


class VoiceBiomarkerRequest(BaseModel):
    audio_data: str = "[SIMULATED_AUDIO]"


class CarePlanRequest(BaseModel):
    primary_diagnosis: str
    secondary_diagnoses: Optional[list[str]] = []
    goals: Optional[list[dict]] = []
    interventions: Optional[list[dict]] = []
    care_team_members: Optional[list[str]] = []


class MedicationRequest(BaseModel):
    drug_name: str
    dosage: str
    frequency: str
    prescriber_id: str
    generic_name: Optional[str] = None
    route: Optional[str] = "oral"
    refills: Optional[int] = 0


class ClinicalNoteRequest(BaseModel):
    content: str
    note_type: Optional[str] = "Progress Note"
    author_id: Optional[str] = "system"
    auto_extract: Optional[bool] = True


class ClaimRequest(BaseModel):
    payer_id: str
    diagnosis_codes: list[str]
    procedure_codes: list[str]
    total_charge: float
    service_date: Optional[str] = None
    provider_id: Optional[str] = None


class AppointmentRequest(BaseModel):
    provider_id: str
    appointment_type: str
    date: str
    time: str
    duration_minutes: Optional[int] = 30
    location: Optional[str] = "Main Clinic"
    notes: Optional[str] = ""


class ApprovalDecisionRequest(BaseModel):
    approver_id: str
    approved: bool
    reason: Optional[str] = None


class AgentActionRequest(BaseModel):
    agent_type: str
    action_type: str
    parameters: dict = {}
    patient_id: Optional[str] = None
    user_id: Optional[str] = "system"


@app.get("/healthz")
async def healthz():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Healthcare Agent Framework",
        "version": "1.0.0",
        "description": "8+1 Agent Architecture for Healthcare Workflows",
        "agents": [
            "Orchestrator (+1)",
            "Intake (01)",
            "Care Planning (02)",
            "Medication (03)",
            "Documentation (04)",
            "Billing (05)",
            "Compliance (06)",
            "Family Communication (07)",
            "Scheduling (08)"
        ],
        "governance_layers": [
            "Risk-Tiered Gates",
            "Complete Audit Trail",
            "Role-Based Access Control",
            "Fallback Logic",
            "Bias Monitoring"
        ]
    }


@app.get("/api/dashboard")
async def get_dashboard():
    """Get comprehensive dashboard data for human oversight."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="get_dashboard_data",
        parameters={}
    )
    
    return response.result


@app.get("/api/agents")
async def get_agents():
    """Get status of all registered agents."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    return {
        "agents": orchestrator.get_all_agent_statuses(),
        "total": len(orchestrator.registered_agents)
    }


@app.get("/api/agents/{agent_type}")
async def get_agent_status(agent_type: str):
    """Get status of a specific agent."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    try:
        agent_type_enum = AgentType(agent_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid agent type: {agent_type}")
    
    agent = orchestrator.get_agent(agent_type_enum)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_type}")
    
    return agent.get_status()


@app.post("/api/agents/action")
async def execute_agent_action(request: AgentActionRequest):
    """Execute an action on a specific agent through the orchestrator."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": request.agent_type,
            "action": request.action_type,
            "parameters": request.parameters,
            "user_id": request.user_id
        },
        patient_id=request.patient_id
    )
    
    return {
        "success": response.success,
        "result": response.result,
        "action_id": response.action.action_id,
        "escalation_required": response.escalation_required,
        "escalation_reason": response.escalation_reason
    }


@app.post("/api/intake/register")
async def register_patient(request: PatientRegistrationRequest):
    """Register a new patient."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": AgentType.INTAKE.value,
            "action": "register_patient",
            "parameters": request.model_dump()
        }
    )
    
    if not response.success:
        raise HTTPException(status_code=400, detail=response.result.get("error", "Registration failed"))
    
    return response.result


@app.post("/api/intake/{patient_id}/insurance")
async def verify_insurance(patient_id: str, request: InsuranceVerificationRequest):
    """Verify patient insurance."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": AgentType.INTAKE.value,
            "action": "verify_insurance",
            "parameters": request.model_dump()
        },
        patient_id=patient_id
    )
    
    return response.result


@app.post("/api/intake/{patient_id}/aims-screening")
async def conduct_aims_screening(patient_id: str, request: AIMSScreeningRequest):
    """Conduct AIMS screening for a patient."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": AgentType.INTAKE.value,
            "action": "conduct_aims_screening",
            "parameters": request.model_dump()
        },
        patient_id=patient_id
    )
    
    return response.result


@app.post("/api/intake/{patient_id}/voice-biomarker")
async def perform_voice_biomarker_screening(patient_id: str, request: VoiceBiomarkerRequest):
    """Perform voice biomarker screening using Canary Speech."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": AgentType.INTAKE.value,
            "action": "perform_voice_biomarker_screening",
            "parameters": request.model_dump()
        },
        patient_id=patient_id
    )
    
    return response.result


@app.post("/api/intake/{patient_id}/complete")
async def complete_intake(patient_id: str):
    """Complete the intake process for a patient."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": AgentType.INTAKE.value,
            "action": "complete_intake",
            "parameters": {}
        },
        patient_id=patient_id
    )
    
    return response.result


@app.get("/api/intake/{patient_id}")
async def get_patient(patient_id: str):
    """Get patient information."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": AgentType.INTAKE.value,
            "action": "get_patient",
            "parameters": {}
        },
        patient_id=patient_id
    )
    
    return response.result


@app.get("/api/intake/search")
async def search_patients(
    query: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=100)
):
    """Search for patients."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": AgentType.INTAKE.value,
            "action": "search_patients",
            "parameters": {"query": query or "", "status": status, "limit": limit}
        }
    )
    
    return response.result


@app.post("/api/care-plan/{patient_id}")
async def create_care_plan(patient_id: str, request: CarePlanRequest):
    """Create a care plan for a patient."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": AgentType.CARE_PLANNING.value,
            "action": "create_care_plan",
            "parameters": request.model_dump()
        },
        patient_id=patient_id
    )
    
    return response.result


@app.get("/api/care-plan/{patient_id}")
async def get_care_plan(patient_id: str):
    """Get care plan for a patient."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": AgentType.CARE_PLANNING.value,
            "action": "get_care_plan",
            "parameters": {}
        },
        patient_id=patient_id
    )
    
    return response.result


@app.post("/api/care-plan/{patient_id}/goal")
async def add_care_plan_goal(patient_id: str, description: str = Body(..., embed=True)):
    """Add a goal to a care plan."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": AgentType.CARE_PLANNING.value,
            "action": "add_goal",
            "parameters": {"description": description}
        },
        patient_id=patient_id
    )
    
    return response.result


@app.post("/api/medication/{patient_id}")
async def add_medication(patient_id: str, request: MedicationRequest):
    """Add a medication for a patient."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": AgentType.MEDICATION.value,
            "action": "add_medication",
            "parameters": request.model_dump()
        },
        patient_id=patient_id
    )
    
    return response.result


@app.get("/api/medication/{patient_id}")
async def get_medications(patient_id: str):
    """Get medications for a patient."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": AgentType.MEDICATION.value,
            "action": "get_medication_list",
            "parameters": {}
        },
        patient_id=patient_id
    )
    
    return response.result


@app.post("/api/medication/{patient_id}/check-interactions")
async def check_drug_interactions(patient_id: str, new_drug: str = Body(..., embed=True)):
    """Check for drug interactions."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": AgentType.MEDICATION.value,
            "action": "check_interactions",
            "parameters": {"new_drug": new_drug}
        },
        patient_id=patient_id
    )
    
    return response.result


@app.post("/api/documentation/{patient_id}/note")
async def create_clinical_note(patient_id: str, request: ClinicalNoteRequest):
    """Create a clinical note for a patient."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": AgentType.DOCUMENTATION.value,
            "action": "create_note",
            "parameters": request.model_dump()
        },
        patient_id=patient_id
    )
    
    return response.result


@app.get("/api/documentation/{patient_id}/notes")
async def get_patient_notes(patient_id: str):
    """Get clinical notes for a patient."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": AgentType.DOCUMENTATION.value,
            "action": "get_patient_notes",
            "parameters": {}
        },
        patient_id=patient_id
    )
    
    return response.result


@app.post("/api/documentation/extract-entities")
async def extract_medical_entities(text: str = Body(..., embed=True)):
    """Extract medical entities from text using NLP."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": AgentType.DOCUMENTATION.value,
            "action": "extract_entities",
            "parameters": {"text": text}
        }
    )
    
    return response.result


@app.post("/api/documentation/deidentify")
async def deidentify_text(text: str = Body(..., embed=True)):
    """De-identify clinical text by removing PHI."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": AgentType.DOCUMENTATION.value,
            "action": "deidentify_note",
            "parameters": {"text": text}
        }
    )
    
    return response.result


@app.post("/api/billing/{patient_id}/claim")
async def create_claim(patient_id: str, request: ClaimRequest):
    """Create a billing claim."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": AgentType.BILLING.value,
            "action": "create_claim",
            "parameters": request.model_dump()
        },
        patient_id=patient_id
    )
    
    return response.result


@app.get("/api/billing/{patient_id}/claims")
async def get_patient_claims(patient_id: str):
    """Get claims for a patient."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": AgentType.BILLING.value,
            "action": "get_patient_claims",
            "parameters": {}
        },
        patient_id=patient_id
    )
    
    return response.result


@app.get("/api/billing/revenue-report")
async def get_revenue_report():
    """Get revenue cycle report."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": AgentType.BILLING.value,
            "action": "get_revenue_report",
            "parameters": {}
        }
    )
    
    return response.result


@app.post("/api/scheduling/{patient_id}/appointment")
async def schedule_appointment(patient_id: str, request: AppointmentRequest):
    """Schedule an appointment."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": AgentType.SCHEDULING.value,
            "action": "schedule_appointment",
            "parameters": request.model_dump()
        },
        patient_id=patient_id
    )
    
    return response.result


@app.get("/api/scheduling/{patient_id}/appointments")
async def get_patient_appointments(patient_id: str):
    """Get appointments for a patient."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": AgentType.SCHEDULING.value,
            "action": "get_patient_appointments",
            "parameters": {}
        },
        patient_id=patient_id
    )
    
    return response.result


@app.get("/api/scheduling/availability")
async def check_availability(
    provider_id: str = Query(...),
    date: str = Query(...)
):
    """Check provider availability."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": AgentType.SCHEDULING.value,
            "action": "check_availability",
            "parameters": {"provider_id": provider_id, "date": date}
        }
    )
    
    return response.result


@app.post("/api/compliance/check")
async def run_compliance_check(check_type: str = Body("general", embed=True)):
    """Run a compliance check."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": AgentType.COMPLIANCE.value,
            "action": "run_compliance_check",
            "parameters": {"check_type": check_type}
        }
    )
    
    return response.result


@app.get("/api/compliance/bias-summary")
async def get_bias_summary():
    """Get bias monitoring summary."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": AgentType.COMPLIANCE.value,
            "action": "get_bias_summary",
            "parameters": {}
        }
    )
    
    return response.result


@app.post("/api/compliance/analyze-bias")
async def analyze_bias(
    agent_type: Optional[str] = Body(None),
    action_type: Optional[str] = Body(None)
):
    """Analyze for algorithmic bias."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": AgentType.COMPLIANCE.value,
            "action": "analyze_bias",
            "parameters": {"agent_type": agent_type, "action_type": action_type}
        }
    )
    
    return response.result


@app.get("/api/compliance/report")
async def get_compliance_report(report_type: str = Query("summary")):
    """Generate a compliance report."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="route_request",
        parameters={
            "target_agent": AgentType.COMPLIANCE.value,
            "action": "generate_compliance_report",
            "parameters": {"report_type": report_type}
        }
    )
    
    return response.result


@app.get("/api/governance/pending-approvals")
async def get_pending_approvals():
    """Get pending approval requests."""
    if not governance_engine:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    approvals = governance_engine.risk_gates.get_pending_approvals()
    
    return {
        "pending_approvals": [
            {
                "request_id": a.request_id,
                "action_id": a.action_id,
                "agent_type": a.agent_type.value,
                "action_type": a.action_type,
                "risk_level": a.risk_level.value,
                "confidence_score": a.confidence_score,
                "priority": a.priority,
                "created_at": a.created_at.isoformat(),
                "required_approvers": a.required_approvers
            }
            for a in approvals
        ],
        "count": len(approvals)
    }


@app.post("/api/governance/approve/{request_id}")
async def approve_action(request_id: str, request: ApprovalDecisionRequest):
    """Approve or reject a pending action."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    action_type = "approve_action" if request.approved else "reject_action"
    
    response = await orchestrator.process(
        action_type=action_type,
        parameters={
            "request_id": request_id,
            "approver_id": request.approver_id,
            "rejector_id": request.approver_id,
            "reason": request.reason
        }
    )
    
    return response.result


@app.get("/api/governance/escalations")
async def get_pending_escalations():
    """Get pending escalations."""
    if not governance_engine:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    return {
        "escalations": governance_engine.fallback.get_pending_escalations(),
        "statistics": governance_engine.fallback.get_escalation_statistics()
    }


@app.get("/api/governance/audit-trail")
async def get_audit_statistics():
    """Get audit trail statistics."""
    if not governance_engine:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    return governance_engine.audit_trail.get_statistics()


@app.get("/api/governance/configuration")
async def get_governance_configuration():
    """Get current governance configuration."""
    if not governance_engine:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    return governance_engine.get_configuration()


@app.post("/api/workflow")
async def execute_workflow(
    workflow_name: str = Body(...),
    steps: list[dict] = Body(...),
    patient_id: Optional[str] = Body(None)
):
    """Execute a multi-agent workflow."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    response = await orchestrator.process(
        action_type="coordinate_workflow",
        parameters={
            "workflow_name": workflow_name,
            "steps": steps
        },
        patient_id=patient_id
    )
    
    return response.result


@app.post("/api/intake/workflow/{patient_id}")
async def run_full_intake_workflow(
    patient_id: str,
    include_voice_screening: bool = Query(True)
):
    """Run the complete intake workflow for a patient."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    steps = [
        {
            "agent": AgentType.INTAKE.value,
            "action": "conduct_aims_screening",
            "parameters": {
                "chief_complaint": "General intake assessment",
                "vital_signs": {"bp": "120/80", "hr": 72, "temp": 98.6}
            }
        }
    ]
    
    if include_voice_screening:
        steps.append({
            "agent": AgentType.INTAKE.value,
            "action": "perform_voice_biomarker_screening",
            "parameters": {"audio_data": "[SIMULATED_AUDIO]"}
        })
    
    steps.append({
        "agent": AgentType.INTAKE.value,
        "action": "complete_intake",
        "parameters": {}
    })
    
    response = await orchestrator.process(
        action_type="coordinate_workflow",
        parameters={
            "workflow_name": "full_intake",
            "steps": steps
        },
        patient_id=patient_id
    )
    
    return response.result
