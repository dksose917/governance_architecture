"""AWS Comprehend Medical integration for healthcare NLP."""

import logging
import random
from typing import Optional
from datetime import datetime

from app.integrations.base import BaseIntegrationClient

logger = logging.getLogger(__name__)


class AWSComprehendMedicalClient(BaseIntegrationClient):
    """Client for AWS Comprehend Medical NLP services.
    
    Use Cases:
    - Medical entity extraction from clinical text
    - PHI detection and redaction
    - ICD-10/RxNorm code mapping
    - Clinical concept identification
    """
    
    def __init__(
        self,
        aws_access_key: Optional[str] = None,
        aws_secret_key: Optional[str] = None,
        region: str = "us-east-1",
        simulate: bool = True
    ):
        super().__init__(
            api_key=aws_access_key,
            base_url=f"https://comprehendmedical.{region}.amazonaws.com",
            timeout=30,
            simulate=simulate
        )
        self.region = region
        
        self.entity_categories = [
            "MEDICATION", "MEDICAL_CONDITION", "PROTECTED_HEALTH_INFORMATION",
            "TEST_TREATMENT_PROCEDURE", "ANATOMY", "TIME_EXPRESSION"
        ]
        
        self.medication_types = [
            "BRAND_NAME", "GENERIC_NAME", "DOSAGE", "DURATION",
            "FORM", "FREQUENCY", "RATE", "ROUTE_OR_MODE", "STRENGTH"
        ]
        
        self.condition_types = [
            "ACUITY", "DIRECTION", "QUALITY", "SYSTEM_ORGAN_SITE"
        ]
        
        self.sample_medications = [
            {"name": "Lisinopril", "generic": True, "rxnorm": "104377"},
            {"name": "Metformin", "generic": True, "rxnorm": "6809"},
            {"name": "Atorvastatin", "generic": True, "rxnorm": "83367"},
            {"name": "Amlodipine", "generic": True, "rxnorm": "17767"},
            {"name": "Omeprazole", "generic": True, "rxnorm": "7646"},
            {"name": "Levothyroxine", "generic": True, "rxnorm": "10582"},
            {"name": "Gabapentin", "generic": True, "rxnorm": "25480"},
            {"name": "Hydrochlorothiazide", "generic": True, "rxnorm": "5487"},
        ]
        
        self.sample_conditions = [
            {"name": "Hypertension", "icd10": "I10"},
            {"name": "Type 2 Diabetes", "icd10": "E11.9"},
            {"name": "Hyperlipidemia", "icd10": "E78.5"},
            {"name": "Chronic kidney disease", "icd10": "N18.9"},
            {"name": "Atrial fibrillation", "icd10": "I48.91"},
            {"name": "Heart failure", "icd10": "I50.9"},
            {"name": "COPD", "icd10": "J44.9"},
            {"name": "Osteoarthritis", "icd10": "M19.90"},
        ]
    
    @property
    def service_name(self) -> str:
        return "aws_comprehend_medical"
    
    def detect_entities(self, text: str) -> dict:
        """Detect medical entities in clinical text.
        
        Args:
            text: Clinical text to analyze
            
        Returns:
            dict with detected entities and metadata
        """
        endpoint = "/detect-entities-v2"
        request_payload = {"Text": text}
        
        if self.simulate:
            latency = self._simulate_latency(base_ms=500, variance_ms=200)
            
            entities = self._extract_simulated_entities(text)
            
            response = {
                "success": True,
                "entities": entities,
                "unmapped_attributes": [],
                "model_version": "2.0.0",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self._log_api_call(
                endpoint=endpoint,
                method="POST",
                request_payload={"text_length": len(text)},
                response_payload={"entity_count": len(entities)},
                status_code=200,
                latency_ms=latency
            )
            
            logger.info(f"Detected {len(entities)} entities in text of {len(text)} chars")
            
            return response
        
        return {"success": False, "error": "Live API calls not implemented"}
    
    def _extract_simulated_entities(self, text: str) -> list[dict]:
        """Extract simulated entities from text."""
        entities = []
        text_lower = text.lower()
        
        for med in self.sample_medications:
            if med["name"].lower() in text_lower:
                start_idx = text_lower.find(med["name"].lower())
                entities.append({
                    "Id": len(entities),
                    "Text": med["name"],
                    "Category": "MEDICATION",
                    "Type": "GENERIC_NAME" if med["generic"] else "BRAND_NAME",
                    "Score": random.uniform(0.92, 0.99),
                    "BeginOffset": start_idx,
                    "EndOffset": start_idx + len(med["name"]),
                    "Traits": [],
                    "Attributes": [
                        {
                            "Type": "RXNORM_CONCEPT",
                            "Score": random.uniform(0.85, 0.98),
                            "Text": med["rxnorm"]
                        }
                    ]
                })
        
        for condition in self.sample_conditions:
            if condition["name"].lower() in text_lower:
                start_idx = text_lower.find(condition["name"].lower())
                entities.append({
                    "Id": len(entities),
                    "Text": condition["name"],
                    "Category": "MEDICAL_CONDITION",
                    "Type": "DX_NAME",
                    "Score": random.uniform(0.90, 0.99),
                    "BeginOffset": start_idx,
                    "EndOffset": start_idx + len(condition["name"]),
                    "Traits": [],
                    "Attributes": [
                        {
                            "Type": "ICD10_CM_CONCEPT",
                            "Score": random.uniform(0.85, 0.98),
                            "Text": condition["icd10"]
                        }
                    ]
                })
        
        dosage_patterns = ["mg", "ml", "mcg", "units"]
        for pattern in dosage_patterns:
            if pattern in text_lower:
                idx = text_lower.find(pattern)
                start = max(0, idx - 5)
                end = idx + len(pattern)
                dosage_text = text[start:end].strip()
                if any(c.isdigit() for c in dosage_text):
                    entities.append({
                        "Id": len(entities),
                        "Text": dosage_text,
                        "Category": "MEDICATION",
                        "Type": "DOSAGE",
                        "Score": random.uniform(0.88, 0.97),
                        "BeginOffset": start,
                        "EndOffset": end,
                        "Traits": [],
                        "Attributes": []
                    })
        
        return entities
    
    def detect_phi(self, text: str) -> dict:
        """Detect Protected Health Information (PHI) in text.
        
        Args:
            text: Text to analyze for PHI
            
        Returns:
            dict with detected PHI entities
        """
        endpoint = "/detect-phi"
        request_payload = {"Text": text}
        
        if self.simulate:
            latency = self._simulate_latency(base_ms=400, variance_ms=150)
            
            phi_entities = self._detect_simulated_phi(text)
            
            response = {
                "success": True,
                "entities": phi_entities,
                "model_version": "2.0.0",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self._log_api_call(
                endpoint=endpoint,
                method="POST",
                request_payload={"text_length": len(text)},
                response_payload={"phi_count": len(phi_entities)},
                status_code=200,
                latency_ms=latency
            )
            
            return response
        
        return {"success": False, "error": "Live API calls not implemented"}
    
    def _detect_simulated_phi(self, text: str) -> list[dict]:
        """Detect simulated PHI in text."""
        phi_entities = []
        
        import re
        
        date_pattern = r'\d{1,2}/\d{1,2}/\d{2,4}'
        for match in re.finditer(date_pattern, text):
            phi_entities.append({
                "Id": len(phi_entities),
                "Text": match.group(),
                "Category": "PROTECTED_HEALTH_INFORMATION",
                "Type": "DATE",
                "Score": random.uniform(0.95, 0.99),
                "BeginOffset": match.start(),
                "EndOffset": match.end()
            })
        
        phone_pattern = r'\d{3}[-.]?\d{3}[-.]?\d{4}'
        for match in re.finditer(phone_pattern, text):
            phi_entities.append({
                "Id": len(phi_entities),
                "Text": match.group(),
                "Category": "PROTECTED_HEALTH_INFORMATION",
                "Type": "PHONE_OR_FAX",
                "Score": random.uniform(0.92, 0.99),
                "BeginOffset": match.start(),
                "EndOffset": match.end()
            })
        
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        for match in re.finditer(email_pattern, text):
            phi_entities.append({
                "Id": len(phi_entities),
                "Text": match.group(),
                "Category": "PROTECTED_HEALTH_INFORMATION",
                "Type": "EMAIL",
                "Score": random.uniform(0.95, 0.99),
                "BeginOffset": match.start(),
                "EndOffset": match.end()
            })
        
        return phi_entities
    
    def infer_icd10(self, text: str) -> dict:
        """Infer ICD-10-CM codes from clinical text.
        
        Args:
            text: Clinical text to analyze
            
        Returns:
            dict with inferred ICD-10 codes
        """
        endpoint = "/infer-icd10-cm"
        request_payload = {"Text": text}
        
        if self.simulate:
            latency = self._simulate_latency(base_ms=600, variance_ms=250)
            
            entities = self.detect_entities(text)
            icd10_entities = []
            
            for entity in entities.get("entities", []):
                if entity.get("Category") == "MEDICAL_CONDITION":
                    for attr in entity.get("Attributes", []):
                        if attr.get("Type") == "ICD10_CM_CONCEPT":
                            icd10_entities.append({
                                "Id": len(icd10_entities),
                                "Text": entity["Text"],
                                "Category": "MEDICAL_CONDITION",
                                "Type": "DX_NAME",
                                "Score": entity["Score"],
                                "ICD10CMConcepts": [
                                    {
                                        "Code": attr["Text"],
                                        "Description": entity["Text"],
                                        "Score": attr["Score"]
                                    }
                                ]
                            })
            
            response = {
                "success": True,
                "entities": icd10_entities,
                "model_version": "2.0.0",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self._log_api_call(
                endpoint=endpoint,
                method="POST",
                request_payload={"text_length": len(text)},
                response_payload={"icd10_count": len(icd10_entities)},
                status_code=200,
                latency_ms=latency
            )
            
            return response
        
        return {"success": False, "error": "Live API calls not implemented"}
    
    def infer_rxnorm(self, text: str) -> dict:
        """Infer RxNorm codes from clinical text.
        
        Args:
            text: Clinical text to analyze
            
        Returns:
            dict with inferred RxNorm codes
        """
        endpoint = "/infer-rx-norm"
        request_payload = {"Text": text}
        
        if self.simulate:
            latency = self._simulate_latency(base_ms=550, variance_ms=200)
            
            entities = self.detect_entities(text)
            rxnorm_entities = []
            
            for entity in entities.get("entities", []):
                if entity.get("Category") == "MEDICATION":
                    for attr in entity.get("Attributes", []):
                        if attr.get("Type") == "RXNORM_CONCEPT":
                            rxnorm_entities.append({
                                "Id": len(rxnorm_entities),
                                "Text": entity["Text"],
                                "Category": "MEDICATION",
                                "Type": entity.get("Type", "GENERIC_NAME"),
                                "Score": entity["Score"],
                                "RxNormConcepts": [
                                    {
                                        "Code": attr["Text"],
                                        "Description": entity["Text"],
                                        "Score": attr["Score"]
                                    }
                                ]
                            })
            
            response = {
                "success": True,
                "entities": rxnorm_entities,
                "model_version": "2.0.0",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self._log_api_call(
                endpoint=endpoint,
                method="POST",
                request_payload={"text_length": len(text)},
                response_payload={"rxnorm_count": len(rxnorm_entities)},
                status_code=200,
                latency_ms=latency
            )
            
            return response
        
        return {"success": False, "error": "Live API calls not implemented"}
    
    def redact_phi(self, text: str) -> dict:
        """Redact PHI from clinical text.
        
        Args:
            text: Text to redact PHI from
            
        Returns:
            dict with redacted text
        """
        phi_result = self.detect_phi(text)
        
        if not phi_result.get("success"):
            return phi_result
        
        redacted_text = text
        offset_adjustment = 0
        
        for entity in sorted(phi_result.get("entities", []), key=lambda x: x["BeginOffset"]):
            start = entity["BeginOffset"] + offset_adjustment
            end = entity["EndOffset"] + offset_adjustment
            phi_type = entity.get("Type", "PHI")
            replacement = f"[{phi_type}]"
            
            redacted_text = redacted_text[:start] + replacement + redacted_text[end:]
            offset_adjustment += len(replacement) - (end - start)
        
        return {
            "success": True,
            "original_length": len(text),
            "redacted_length": len(redacted_text),
            "redacted_text": redacted_text,
            "phi_count": len(phi_result.get("entities", [])),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def analyze_clinical_note(self, note_text: str) -> dict:
        """Comprehensive analysis of a clinical note.
        
        Args:
            note_text: Clinical note text
            
        Returns:
            dict with comprehensive analysis results
        """
        entities_result = self.detect_entities(note_text)
        phi_result = self.detect_phi(note_text)
        icd10_result = self.infer_icd10(note_text)
        rxnorm_result = self.infer_rxnorm(note_text)
        
        medications = [
            e for e in entities_result.get("entities", [])
            if e.get("Category") == "MEDICATION"
        ]
        
        conditions = [
            e for e in entities_result.get("entities", [])
            if e.get("Category") == "MEDICAL_CONDITION"
        ]
        
        return {
            "success": True,
            "summary": {
                "total_entities": len(entities_result.get("entities", [])),
                "medications_found": len(medications),
                "conditions_found": len(conditions),
                "phi_detected": len(phi_result.get("entities", [])),
                "icd10_codes": len(icd10_result.get("entities", [])),
                "rxnorm_codes": len(rxnorm_result.get("entities", []))
            },
            "entities": entities_result.get("entities", []),
            "phi": phi_result.get("entities", []),
            "icd10": icd10_result.get("entities", []),
            "rxnorm": rxnorm_result.get("entities", []),
            "timestamp": datetime.utcnow().isoformat()
        }
