"""Documentation Agent (04) - Manages clinical documentation and NLP extraction."""

import logging
import random
from datetime import datetime
from typing import Optional, Any

from app.models.base import AgentType, AgentAction, AgentResponse, ActionStatus
from app.models.patient import ClinicalNote
from app.agents.base_agent import BaseAgent
from app.integrations.aws_comprehend import AWSComprehendMedicalClient
from app.integrations.john_snow_labs import JohnSnowLabsClient

logger = logging.getLogger(__name__)


class DocumentationAgent(BaseAgent):
    """Documentation Agent (04) - Designed.
    
    Manages progress notes, regulatory reporting, and quality metrics tracking.
    Integrates AWS Comprehend Medical and John Snow Labs for NLP extraction.
    """
    
    def __init__(
        self,
        comprehend_client: Optional[AWSComprehendMedicalClient] = None,
        jsl_client: Optional[JohnSnowLabsClient] = None
    ):
        super().__init__(AgentType.DOCUMENTATION)
        self.comprehend = comprehend_client or AWSComprehendMedicalClient(simulate=True)
        self.jsl = jsl_client or JohnSnowLabsClient(simulate=True)
        self.clinical_notes: dict[str, ClinicalNote] = {}
        self.patient_notes: dict[str, list[str]] = {}
        self.quality_metrics: dict[str, list[dict]] = {}
    
    @property
    def name(self) -> str:
        return "Documentation Agent"
    
    @property
    def description(self) -> str:
        return (
            "Manages progress notes, regulatory reporting, and quality metrics tracking. "
            "Integrates AWS Comprehend Medical and John Snow Labs for NLP extraction."
        )
    
    @property
    def supported_actions(self) -> list[str]:
        return [
            "create_note", "update_note", "sign_note", "extract_entities",
            "extract_codes", "analyze_note", "deidentify_note",
            "generate_report", "track_quality_metric", "get_patient_notes"
        ]
    
    async def process(
        self,
        action_type: str,
        parameters: dict[str, Any],
        patient_id: Optional[str] = None
    ) -> AgentResponse:
        """Process a documentation action."""
        confidence = self._calculate_confidence(action_type, parameters)
        
        action = self.create_action(
            action_type=action_type,
            parameters=parameters,
            patient_id=patient_id,
            confidence_score=confidence,
            rationale=f"Documentation: {action_type}"
        )
        
        try:
            if action_type == "create_note":
                result = await self._create_note(patient_id, parameters)
            elif action_type == "update_note":
                result = await self._update_note(parameters)
            elif action_type == "sign_note":
                result = await self._sign_note(parameters)
            elif action_type == "extract_entities":
                result = await self._extract_entities(parameters)
            elif action_type == "extract_codes":
                result = await self._extract_codes(parameters)
            elif action_type == "analyze_note":
                result = await self._analyze_note(parameters)
            elif action_type == "deidentify_note":
                result = await self._deidentify_note(parameters)
            elif action_type == "generate_report":
                result = await self._generate_report(parameters)
            elif action_type == "track_quality_metric":
                result = await self._track_quality_metric(patient_id, parameters)
            elif action_type == "get_patient_notes":
                result = self._get_patient_notes(patient_id)
            else:
                result = {"success": False, "error": f"Unknown action: {action_type}"}
            
            action.status = ActionStatus.COMPLETED if result.get("success", True) else ActionStatus.FAILED
            
            return AgentResponse(
                success=result.get("success", True),
                action=action,
                result=result
            )
            
        except Exception as e:
            logger.error(f"Documentation agent error: {e}")
            action.status = ActionStatus.FAILED
            return AgentResponse(success=False, action=action, error=str(e))
    
    def _calculate_confidence(self, action_type: str, parameters: dict) -> float:
        """Calculate confidence score."""
        base_confidence = 0.92
        
        if action_type in ["extract_entities", "extract_codes"]:
            base_confidence = 0.88
        elif action_type == "deidentify_note":
            base_confidence = 0.95
        
        return min(1.0, max(0.0, base_confidence + random.uniform(-0.03, 0.03)))
    
    async def _create_note(
        self,
        patient_id: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a new clinical note."""
        if not patient_id:
            return {"success": False, "error": "Patient ID required"}
        
        if not parameters.get("content"):
            return {"success": False, "error": "Note content required"}
        
        note = ClinicalNote(
            patient_id=patient_id,
            author_id=parameters.get("author_id", "system"),
            note_type=parameters.get("note_type", "Progress Note"),
            content=parameters["content"]
        )
        
        if parameters.get("auto_extract", True):
            entities_result = self.comprehend.detect_entities(note.content)
            note.extracted_entities = entities_result.get("entities", [])
            
            icd_result = self.comprehend.infer_icd10(note.content)
            note.icd_codes = [
                e.get("ICD10CMConcepts", [{}])[0].get("Code", "")
                for e in icd_result.get("entities", [])
                if e.get("ICD10CMConcepts")
            ]
        
        self.clinical_notes[note.note_id] = note
        
        if patient_id not in self.patient_notes:
            self.patient_notes[patient_id] = []
        self.patient_notes[patient_id].append(note.note_id)
        
        return {
            "success": True,
            "note_id": note.note_id,
            "patient_id": patient_id,
            "note_type": note.note_type,
            "entities_extracted": len(note.extracted_entities),
            "icd_codes": note.icd_codes
        }
    
    async def _update_note(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Update an existing note."""
        note_id = parameters.get("note_id")
        
        if not note_id or note_id not in self.clinical_notes:
            return {"success": False, "error": "Note not found"}
        
        note = self.clinical_notes[note_id]
        
        if note.signed:
            return {"success": False, "error": "Cannot update signed note"}
        
        if "content" in parameters:
            note.content = parameters["content"]
            
            if parameters.get("re_extract", True):
                entities_result = self.comprehend.detect_entities(note.content)
                note.extracted_entities = entities_result.get("entities", [])
        
        return {
            "success": True,
            "note_id": note_id,
            "updated": True
        }
    
    async def _sign_note(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Sign a clinical note."""
        note_id = parameters.get("note_id")
        signer_id = parameters.get("signer_id")
        
        if not note_id or note_id not in self.clinical_notes:
            return {"success": False, "error": "Note not found"}
        
        if not signer_id:
            return {"success": False, "error": "Signer ID required"}
        
        note = self.clinical_notes[note_id]
        note.signed = True
        note.signed_at = datetime.utcnow()
        note.signed_by = signer_id
        
        return {
            "success": True,
            "note_id": note_id,
            "signed_by": signer_id,
            "signed_at": note.signed_at.isoformat()
        }
    
    async def _extract_entities(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Extract medical entities from text."""
        text = parameters.get("text", "")
        note_id = parameters.get("note_id")
        
        if note_id and note_id in self.clinical_notes:
            text = self.clinical_notes[note_id].content
        
        if not text:
            return {"success": False, "error": "No text provided"}
        
        use_jsl = parameters.get("use_jsl", False)
        
        if use_jsl:
            result = self.jsl.extract_entities(text)
            entities = result.get("entities", [])
        else:
            result = self.comprehend.detect_entities(text)
            entities = result.get("entities", [])
        
        return {
            "success": True,
            "text_length": len(text),
            "entities": entities,
            "entity_count": len(entities),
            "source": "john_snow_labs" if use_jsl else "aws_comprehend_medical"
        }
    
    async def _extract_codes(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Extract ICD-10 and RxNorm codes from text."""
        text = parameters.get("text", "")
        note_id = parameters.get("note_id")
        
        if note_id and note_id in self.clinical_notes:
            text = self.clinical_notes[note_id].content
        
        if not text:
            return {"success": False, "error": "No text provided"}
        
        icd_result = self.comprehend.infer_icd10(text)
        rxnorm_result = self.comprehend.infer_rxnorm(text)
        
        icd_codes = []
        for entity in icd_result.get("entities", []):
            for concept in entity.get("ICD10CMConcepts", []):
                icd_codes.append({
                    "code": concept.get("Code"),
                    "description": concept.get("Description"),
                    "score": concept.get("Score")
                })
        
        rxnorm_codes = []
        for entity in rxnorm_result.get("entities", []):
            for concept in entity.get("RxNormConcepts", []):
                rxnorm_codes.append({
                    "code": concept.get("Code"),
                    "description": concept.get("Description"),
                    "score": concept.get("Score")
                })
        
        return {
            "success": True,
            "icd10_codes": icd_codes,
            "rxnorm_codes": rxnorm_codes,
            "total_codes": len(icd_codes) + len(rxnorm_codes)
        }
    
    async def _analyze_note(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Comprehensive analysis of a clinical note."""
        text = parameters.get("text", "")
        note_id = parameters.get("note_id")
        
        if note_id and note_id in self.clinical_notes:
            text = self.clinical_notes[note_id].content
        
        if not text:
            return {"success": False, "error": "No text provided"}
        
        comprehend_result = self.comprehend.analyze_clinical_note(text)
        
        jsl_entities = self.jsl.extract_entities(text)
        jsl_relations = self.jsl.extract_relations(text)
        jsl_assertions = self.jsl.detect_assertions(text)
        
        return {
            "success": True,
            "text_length": len(text),
            "comprehend_analysis": comprehend_result.get("summary", {}),
            "jsl_entities": len(jsl_entities.get("entities", [])),
            "jsl_relations": len(jsl_relations.get("relations", [])),
            "assertions": [
                {
                    "entity": e.get("text"),
                    "type": e.get("entity_type"),
                    "assertion": e.get("assertion", {}).get("status")
                }
                for e in jsl_assertions.get("entities_with_assertions", [])[:10]
            ]
        }
    
    async def _deidentify_note(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """De-identify a clinical note."""
        text = parameters.get("text", "")
        note_id = parameters.get("note_id")
        
        if note_id and note_id in self.clinical_notes:
            text = self.clinical_notes[note_id].content
        
        if not text:
            return {"success": False, "error": "No text provided"}
        
        jsl_result = self.jsl.deidentify(text)
        comprehend_result = self.comprehend.redact_phi(text)
        
        return {
            "success": True,
            "original_length": len(text),
            "jsl_deidentified": jsl_result.get("deidentified_text", ""),
            "comprehend_redacted": comprehend_result.get("redacted_text", ""),
            "phi_count_jsl": jsl_result.get("phi_count", 0),
            "phi_count_comprehend": comprehend_result.get("phi_count", 0)
        }
    
    async def _generate_report(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Generate a regulatory or quality report."""
        report_type = parameters.get("report_type", "quality_summary")
        date_range = parameters.get("date_range", {})
        
        total_notes = len(self.clinical_notes)
        signed_notes = sum(1 for n in self.clinical_notes.values() if n.signed)
        
        report = {
            "report_type": report_type,
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_notes": total_notes,
                "signed_notes": signed_notes,
                "unsigned_notes": total_notes - signed_notes,
                "signing_rate": signed_notes / total_notes if total_notes > 0 else 0
            },
            "note_types": {},
            "quality_metrics": self.quality_metrics
        }
        
        for note in self.clinical_notes.values():
            note_type = note.note_type
            if note_type not in report["note_types"]:
                report["note_types"][note_type] = 0
            report["note_types"][note_type] += 1
        
        return {
            "success": True,
            "report": report
        }
    
    async def _track_quality_metric(
        self,
        patient_id: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Track a quality metric."""
        metric_name = parameters.get("metric_name")
        metric_value = parameters.get("value")
        
        if not metric_name:
            return {"success": False, "error": "Metric name required"}
        
        metric_entry = {
            "patient_id": patient_id,
            "value": metric_value,
            "timestamp": datetime.utcnow().isoformat(),
            "source": parameters.get("source", "system")
        }
        
        if metric_name not in self.quality_metrics:
            self.quality_metrics[metric_name] = []
        self.quality_metrics[metric_name].append(metric_entry)
        
        return {
            "success": True,
            "metric_name": metric_name,
            "value": metric_value,
            "total_entries": len(self.quality_metrics[metric_name])
        }
    
    def _get_patient_notes(self, patient_id: str) -> dict[str, Any]:
        """Get all notes for a patient."""
        if not patient_id or patient_id not in self.patient_notes:
            return {"success": True, "notes": [], "count": 0}
        
        notes = []
        for note_id in self.patient_notes[patient_id]:
            note = self.clinical_notes.get(note_id)
            if note:
                notes.append({
                    "note_id": note.note_id,
                    "note_type": note.note_type,
                    "author_id": note.author_id,
                    "created_at": note.created_at.isoformat(),
                    "signed": note.signed,
                    "entity_count": len(note.extracted_entities),
                    "icd_codes": note.icd_codes
                })
        
        return {
            "success": True,
            "patient_id": patient_id,
            "notes": notes,
            "count": len(notes)
        }
