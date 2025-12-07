"""Patient-related models for the healthcare agent framework."""

from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class Demographics(BaseModel):
    """Patient demographic information."""
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    race: Optional[str] = None
    ethnicity: Optional[str] = None
    preferred_language: str = "English"
    marital_status: Optional[str] = None


class ContactInfo(BaseModel):
    """Patient contact information."""
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone_primary: str
    phone_secondary: Optional[str] = None
    email: Optional[str] = None


class EmergencyContact(BaseModel):
    """Emergency contact information."""
    name: str
    relationship: str
    phone: str
    email: Optional[str] = None


class InsuranceInfo(BaseModel):
    """Patient insurance information."""
    insurance_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    payer_name: str
    policy_number: str
    group_number: Optional[str] = None
    subscriber_name: str
    subscriber_relationship: str = "Self"
    effective_date: date
    termination_date: Optional[date] = None
    is_primary: bool = True
    verified: bool = False
    verification_date: Optional[datetime] = None
    eligibility_status: str = "PENDING"


class AIMSScreening(BaseModel):
    """AIMS (Admission, Intake, and Medical Screening) results."""
    screening_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    screening_date: datetime = Field(default_factory=datetime.utcnow)
    chief_complaint: str
    medical_history: list[str] = Field(default_factory=list)
    current_medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    vital_signs: dict = Field(default_factory=dict)
    pain_level: Optional[int] = Field(None, ge=0, le=10)
    fall_risk_score: Optional[float] = None
    cognitive_status: Optional[str] = None
    functional_status: Optional[str] = None
    screening_complete: bool = False
    screener_id: Optional[str] = None
    risk_level: Optional[str] = None


class VoiceBiomarkerResult(BaseModel):
    """Results from Canary Speech voice biomarker analysis."""
    result_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)
    overall_confidence: float = Field(ge=0.0, le=1.0)
    mood_score: float = Field(ge=0.0, le=1.0)
    mood_classification: str
    cognitive_score: float = Field(ge=0.0, le=1.0)
    cognitive_classification: str
    respiratory_score: float = Field(ge=0.0, le=1.0)
    respiratory_classification: str
    risk_indicators: list[str] = Field(default_factory=list)
    requires_clinical_review: bool = False
    raw_audio_hash: Optional[str] = None


class Patient(BaseModel):
    """Complete patient record."""
    patient_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mrn: str  # Medical Record Number
    demographics: Demographics
    contact_info: ContactInfo
    emergency_contacts: list[EmergencyContact] = Field(default_factory=list)
    insurance_info: list[InsuranceInfo] = Field(default_factory=list)
    aims_screening: Optional[AIMSScreening] = None
    voice_biomarker_results: list[VoiceBiomarkerResult] = Field(default_factory=list)
    intake_status: str = "PENDING"
    intake_completion_date: Optional[datetime] = None
    assigned_care_team: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    consent_signed: bool = False
    hipaa_acknowledged: bool = False

    class Config:
        from_attributes = True


class CarePlan(BaseModel):
    """Patient care plan."""
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    created_date: datetime = Field(default_factory=datetime.utcnow)
    effective_date: date
    review_date: date
    status: str = "DRAFT"
    primary_diagnosis: str
    secondary_diagnoses: list[str] = Field(default_factory=list)
    goals: list[dict] = Field(default_factory=list)
    interventions: list[dict] = Field(default_factory=list)
    care_team_members: list[str] = Field(default_factory=list)
    mds_assessment_date: Optional[date] = None
    last_idt_meeting: Optional[datetime] = None
    next_review_date: Optional[date] = None


class Medication(BaseModel):
    """Medication record."""
    medication_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    drug_name: str
    generic_name: Optional[str] = None
    dosage: str
    route: str
    frequency: str
    start_date: date
    end_date: Optional[date] = None
    prescriber_id: str
    pharmacy_id: Optional[str] = None
    status: str = "ACTIVE"
    refills_remaining: int = 0
    last_filled_date: Optional[date] = None
    interactions_checked: bool = False
    adverse_events: list[str] = Field(default_factory=list)


class Appointment(BaseModel):
    """Appointment record."""
    appointment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    provider_id: str
    appointment_type: str
    scheduled_datetime: datetime
    duration_minutes: int = 30
    location: str
    status: str = "SCHEDULED"
    reminder_sent: bool = False
    reminder_sent_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ClinicalNote(BaseModel):
    """Clinical documentation note."""
    note_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    author_id: str
    note_type: str
    content: str
    extracted_entities: list[dict] = Field(default_factory=list)
    icd_codes: list[str] = Field(default_factory=list)
    cpt_codes: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    signed: bool = False
    signed_at: Optional[datetime] = None
    signed_by: Optional[str] = None


class Claim(BaseModel):
    """Billing claim record."""
    claim_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    service_date: date
    diagnosis_codes: list[str] = Field(default_factory=list)
    procedure_codes: list[str] = Field(default_factory=list)
    total_charges: float
    payer_id: str
    status: str = "PENDING"
    submitted_date: Optional[datetime] = None
    adjudicated_date: Optional[datetime] = None
    paid_amount: Optional[float] = None
    denial_reason: Optional[str] = None
