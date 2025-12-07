"""John Snow Labs Health NLP integration for advanced clinical NLP."""

import logging
import random
from typing import Optional
from datetime import datetime

from app.integrations.base import BaseIntegrationClient

logger = logging.getLogger(__name__)


class JohnSnowLabsClient(BaseIntegrationClient):
    """Client for John Snow Labs Health NLP services.
    
    Use Cases:
    - Advanced clinical entity recognition
    - Relation extraction between medical concepts
    - De-identification of clinical text
    - Bias detection in clinical documentation
    - Assertion status detection
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        license_key: Optional[str] = None,
        simulate: bool = True
    ):
        super().__init__(
            api_key=api_key,
            base_url="https://api.johnsnowlabs.com",
            timeout=60,
            simulate=simulate
        )
        self.license_key = license_key or "PLACEHOLDER_LICENSE_KEY"
        
        self.available_pipelines = {
            "ner_clinical_large": "Clinical NER - Large model",
            "ner_clinical": "Clinical NER - Base model",
            "ner_jsl": "JSL Clinical NER",
            "ner_posology": "Medication/Posology NER",
            "ner_deid": "De-identification NER",
            "re_clinical": "Clinical Relation Extraction",
            "assertion_dl": "Assertion Status Detection",
            "deidentify_enriched": "De-identification Pipeline"
        }
        
        self.entity_types = {
            "clinical": [
                "PROBLEM", "TREATMENT", "TEST", "SYMPTOM", "PROCEDURE",
                "DRUG", "DOSAGE", "FREQUENCY", "DURATION", "ROUTE",
                "BODY_PART", "DIAGNOSIS", "CLINICAL_DEPT"
            ],
            "deid": [
                "NAME", "DATE", "AGE", "PHONE", "EMAIL", "ADDRESS",
                "SSN", "MRN", "ACCOUNT", "LICENSE", "HOSPITAL", "DOCTOR"
            ]
        }
        
        self.relation_types = [
            "DRUG-DOSAGE", "DRUG-FREQUENCY", "DRUG-DURATION", "DRUG-ROUTE",
            "PROBLEM-TREATMENT", "TEST-PROBLEM", "SYMPTOM-PROBLEM",
            "PROCEDURE-BODY_PART", "TREATMENT-BODY_PART"
        ]
        
        self.assertion_statuses = [
            "present", "absent", "possible", "conditional", 
            "hypothetical", "associated_with_someone_else"
        ]
    
    @property
    def service_name(self) -> str:
        return "john_snow_labs"
    
    def extract_entities(
        self,
        text: str,
        pipeline: str = "ner_clinical_large"
    ) -> dict:
        """Extract clinical entities using NER pipeline.
        
        Args:
            text: Clinical text to analyze
            pipeline: NER pipeline to use
            
        Returns:
            dict with extracted entities
        """
        endpoint = "/api/v1/ner"
        request_payload = {
            "text": text,
            "pipeline": pipeline
        }
        
        if self.simulate:
            latency = self._simulate_latency(base_ms=1500, variance_ms=500)
            
            entities = self._extract_simulated_clinical_entities(text)
            
            response = {
                "success": True,
                "pipeline": pipeline,
                "entities": entities,
                "text_length": len(text),
                "processing_time_ms": latency,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self._log_api_call(
                endpoint=endpoint,
                method="POST",
                request_payload={"text_length": len(text), "pipeline": pipeline},
                response_payload={"entity_count": len(entities)},
                status_code=200,
                latency_ms=latency
            )
            
            logger.info(f"JSL NER extracted {len(entities)} entities using {pipeline}")
            
            return response
        
        return {"success": False, "error": "Live API calls not implemented"}
    
    def _extract_simulated_clinical_entities(self, text: str) -> list[dict]:
        """Extract simulated clinical entities."""
        entities = []
        text_lower = text.lower()
        
        clinical_terms = {
            "hypertension": ("PROBLEM", "I10"),
            "diabetes": ("PROBLEM", "E11.9"),
            "chest pain": ("SYMPTOM", "R07.9"),
            "shortness of breath": ("SYMPTOM", "R06.02"),
            "headache": ("SYMPTOM", "R51"),
            "fever": ("SYMPTOM", "R50.9"),
            "cough": ("SYMPTOM", "R05"),
            "fatigue": ("SYMPTOM", "R53.83"),
            "nausea": ("SYMPTOM", "R11.0"),
            "dizziness": ("SYMPTOM", "R42"),
            "metformin": ("DRUG", "6809"),
            "lisinopril": ("DRUG", "104377"),
            "aspirin": ("DRUG", "1191"),
            "ibuprofen": ("DRUG", "5640"),
            "blood pressure": ("TEST", None),
            "blood glucose": ("TEST", None),
            "ecg": ("TEST", None),
            "x-ray": ("TEST", None),
            "mri": ("TEST", None),
            "ct scan": ("TEST", None),
            "physical therapy": ("TREATMENT", None),
            "surgery": ("PROCEDURE", None),
            "biopsy": ("PROCEDURE", None),
        }
        
        for term, (entity_type, code) in clinical_terms.items():
            if term in text_lower:
                start_idx = text_lower.find(term)
                entity = {
                    "text": text[start_idx:start_idx + len(term)],
                    "entity_type": entity_type,
                    "start": start_idx,
                    "end": start_idx + len(term),
                    "confidence": random.uniform(0.88, 0.99),
                    "chunk": text[max(0, start_idx-20):min(len(text), start_idx+len(term)+20)]
                }
                if code:
                    entity["code"] = code
                entities.append(entity)
        
        import re
        dosage_pattern = r'\d+\s*(mg|ml|mcg|g|units)'
        for match in re.finditer(dosage_pattern, text_lower):
            entities.append({
                "text": match.group(),
                "entity_type": "DOSAGE",
                "start": match.start(),
                "end": match.end(),
                "confidence": random.uniform(0.90, 0.98)
            })
        
        freq_terms = ["daily", "twice daily", "three times daily", "once daily", 
                      "every 4 hours", "every 6 hours", "as needed", "prn"]
        for term in freq_terms:
            if term in text_lower:
                start_idx = text_lower.find(term)
                entities.append({
                    "text": term,
                    "entity_type": "FREQUENCY",
                    "start": start_idx,
                    "end": start_idx + len(term),
                    "confidence": random.uniform(0.85, 0.97)
                })
        
        return entities
    
    def extract_relations(
        self,
        text: str,
        pipeline: str = "re_clinical"
    ) -> dict:
        """Extract relations between clinical entities.
        
        Args:
            text: Clinical text to analyze
            pipeline: Relation extraction pipeline
            
        Returns:
            dict with extracted relations
        """
        endpoint = "/api/v1/relation"
        request_payload = {
            "text": text,
            "pipeline": pipeline
        }
        
        if self.simulate:
            latency = self._simulate_latency(base_ms=2000, variance_ms=700)
            
            entities_result = self.extract_entities(text)
            entities = entities_result.get("entities", [])
            
            relations = self._generate_simulated_relations(entities)
            
            response = {
                "success": True,
                "pipeline": pipeline,
                "entities": entities,
                "relations": relations,
                "text_length": len(text),
                "processing_time_ms": latency,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self._log_api_call(
                endpoint=endpoint,
                method="POST",
                request_payload={"text_length": len(text), "pipeline": pipeline},
                response_payload={"relation_count": len(relations)},
                status_code=200,
                latency_ms=latency
            )
            
            return response
        
        return {"success": False, "error": "Live API calls not implemented"}
    
    def _generate_simulated_relations(self, entities: list[dict]) -> list[dict]:
        """Generate simulated relations between entities."""
        relations = []
        
        drugs = [e for e in entities if e.get("entity_type") == "DRUG"]
        dosages = [e for e in entities if e.get("entity_type") == "DOSAGE"]
        frequencies = [e for e in entities if e.get("entity_type") == "FREQUENCY"]
        problems = [e for e in entities if e.get("entity_type") in ["PROBLEM", "SYMPTOM"]]
        treatments = [e for e in entities if e.get("entity_type") == "TREATMENT"]
        
        for drug in drugs:
            for dosage in dosages:
                if abs(drug["start"] - dosage["start"]) < 50:
                    relations.append({
                        "relation_type": "DRUG-DOSAGE",
                        "entity1": drug["text"],
                        "entity1_type": "DRUG",
                        "entity2": dosage["text"],
                        "entity2_type": "DOSAGE",
                        "confidence": random.uniform(0.85, 0.98)
                    })
            
            for freq in frequencies:
                if abs(drug["start"] - freq["start"]) < 80:
                    relations.append({
                        "relation_type": "DRUG-FREQUENCY",
                        "entity1": drug["text"],
                        "entity1_type": "DRUG",
                        "entity2": freq["text"],
                        "entity2_type": "FREQUENCY",
                        "confidence": random.uniform(0.82, 0.96)
                    })
        
        for problem in problems:
            for treatment in treatments:
                if abs(problem["start"] - treatment["start"]) < 100:
                    relations.append({
                        "relation_type": "PROBLEM-TREATMENT",
                        "entity1": problem["text"],
                        "entity1_type": problem["entity_type"],
                        "entity2": treatment["text"],
                        "entity2_type": "TREATMENT",
                        "confidence": random.uniform(0.78, 0.94)
                    })
        
        return relations
    
    def detect_assertions(
        self,
        text: str,
        pipeline: str = "assertion_dl"
    ) -> dict:
        """Detect assertion status of clinical entities.
        
        Args:
            text: Clinical text to analyze
            pipeline: Assertion detection pipeline
            
        Returns:
            dict with entities and their assertion status
        """
        endpoint = "/api/v1/assertion"
        request_payload = {
            "text": text,
            "pipeline": pipeline
        }
        
        if self.simulate:
            latency = self._simulate_latency(base_ms=1800, variance_ms=600)
            
            entities_result = self.extract_entities(text)
            entities = entities_result.get("entities", [])
            
            for entity in entities:
                entity["assertion"] = self._determine_assertion_status(
                    text, entity
                )
            
            response = {
                "success": True,
                "pipeline": pipeline,
                "entities_with_assertions": entities,
                "text_length": len(text),
                "processing_time_ms": latency,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self._log_api_call(
                endpoint=endpoint,
                method="POST",
                request_payload={"text_length": len(text), "pipeline": pipeline},
                response_payload={"entity_count": len(entities)},
                status_code=200,
                latency_ms=latency
            )
            
            return response
        
        return {"success": False, "error": "Live API calls not implemented"}
    
    def _determine_assertion_status(self, text: str, entity: dict) -> dict:
        """Determine assertion status for an entity."""
        text_lower = text.lower()
        entity_start = entity.get("start", 0)
        
        context_start = max(0, entity_start - 30)
        context = text_lower[context_start:entity_start]
        
        negation_terms = ["no ", "not ", "denies ", "without ", "negative for ", "absent "]
        possible_terms = ["possible ", "probable ", "suspected ", "likely ", "may have "]
        hypothetical_terms = ["if ", "would ", "should ", "consider "]
        
        for term in negation_terms:
            if term in context:
                return {
                    "status": "absent",
                    "confidence": random.uniform(0.88, 0.98)
                }
        
        for term in possible_terms:
            if term in context:
                return {
                    "status": "possible",
                    "confidence": random.uniform(0.82, 0.95)
                }
        
        for term in hypothetical_terms:
            if term in context:
                return {
                    "status": "hypothetical",
                    "confidence": random.uniform(0.80, 0.93)
                }
        
        return {
            "status": "present",
            "confidence": random.uniform(0.90, 0.99)
        }
    
    def deidentify(
        self,
        text: str,
        pipeline: str = "deidentify_enriched"
    ) -> dict:
        """De-identify clinical text by removing PHI.
        
        Args:
            text: Clinical text to de-identify
            pipeline: De-identification pipeline
            
        Returns:
            dict with de-identified text and detected PHI
        """
        endpoint = "/api/v1/deidentify"
        request_payload = {
            "text": text,
            "pipeline": pipeline
        }
        
        if self.simulate:
            latency = self._simulate_latency(base_ms=1200, variance_ms=400)
            
            phi_entities = self._detect_simulated_phi(text)
            deidentified_text = self._apply_deidentification(text, phi_entities)
            
            response = {
                "success": True,
                "pipeline": pipeline,
                "original_text": text,
                "deidentified_text": deidentified_text,
                "phi_entities": phi_entities,
                "phi_count": len(phi_entities),
                "processing_time_ms": latency,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self._log_api_call(
                endpoint=endpoint,
                method="POST",
                request_payload={"text_length": len(text), "pipeline": pipeline},
                response_payload={"phi_count": len(phi_entities)},
                status_code=200,
                latency_ms=latency
            )
            
            return response
        
        return {"success": False, "error": "Live API calls not implemented"}
    
    def _detect_simulated_phi(self, text: str) -> list[dict]:
        """Detect simulated PHI entities."""
        phi_entities = []
        
        import re
        
        date_pattern = r'\d{1,2}/\d{1,2}/\d{2,4}'
        for match in re.finditer(date_pattern, text):
            phi_entities.append({
                "text": match.group(),
                "entity_type": "DATE",
                "start": match.start(),
                "end": match.end(),
                "confidence": random.uniform(0.95, 0.99)
            })
        
        phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        for match in re.finditer(phone_pattern, text):
            phi_entities.append({
                "text": match.group(),
                "entity_type": "PHONE",
                "start": match.start(),
                "end": match.end(),
                "confidence": random.uniform(0.93, 0.99)
            })
        
        name_indicators = ["Mr.", "Mrs.", "Ms.", "Dr.", "Patient:"]
        for indicator in name_indicators:
            if indicator in text:
                idx = text.find(indicator)
                end_idx = text.find(" ", idx + len(indicator) + 1)
                if end_idx == -1:
                    end_idx = min(idx + 30, len(text))
                
                potential_name = text[idx:end_idx]
                phi_entities.append({
                    "text": potential_name,
                    "entity_type": "NAME",
                    "start": idx,
                    "end": end_idx,
                    "confidence": random.uniform(0.85, 0.95)
                })
        
        return phi_entities
    
    def _apply_deidentification(self, text: str, phi_entities: list[dict]) -> str:
        """Apply de-identification to text."""
        deidentified = text
        offset = 0
        
        for entity in sorted(phi_entities, key=lambda x: x["start"]):
            start = entity["start"] + offset
            end = entity["end"] + offset
            entity_type = entity["entity_type"]
            replacement = f"[{entity_type}]"
            
            deidentified = deidentified[:start] + replacement + deidentified[end:]
            offset += len(replacement) - (end - start)
        
        return deidentified
    
    def detect_bias(
        self,
        text: str,
        demographics: Optional[list[str]] = None
    ) -> dict:
        """Detect potential bias in clinical documentation.
        
        Args:
            text: Clinical text to analyze
            demographics: Demographic dimensions to check
            
        Returns:
            dict with bias analysis results
        """
        endpoint = "/api/v1/bias_detect"
        
        if demographics is None:
            demographics = ["age", "gender", "race", "ethnicity"]
        
        request_payload = {
            "text": text,
            "demographics": demographics
        }
        
        if self.simulate:
            latency = self._simulate_latency(base_ms=2500, variance_ms=800)
            
            bias_indicators = self._analyze_bias_indicators(text, demographics)
            
            response = {
                "success": True,
                "text_length": len(text),
                "demographics_analyzed": demographics,
                "bias_indicators": bias_indicators,
                "overall_bias_score": self._calculate_overall_bias_score(bias_indicators),
                "recommendations": self._generate_bias_recommendations(bias_indicators),
                "processing_time_ms": latency,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self._log_api_call(
                endpoint=endpoint,
                method="POST",
                request_payload={"text_length": len(text), "demographics": demographics},
                response_payload={
                    "indicator_count": len(bias_indicators),
                    "overall_score": response["overall_bias_score"]
                },
                status_code=200,
                latency_ms=latency
            )
            
            return response
        
        return {"success": False, "error": "Live API calls not implemented"}
    
    def _analyze_bias_indicators(
        self,
        text: str,
        demographics: list[str]
    ) -> list[dict]:
        """Analyze text for bias indicators."""
        indicators = []
        text_lower = text.lower()
        
        bias_terms = {
            "age": ["elderly", "old", "young", "aged"],
            "gender": ["female patient", "male patient", "woman", "man"],
            "race": ["african american", "caucasian", "hispanic", "asian"],
            "ethnicity": ["latino", "non-hispanic", "native"]
        }
        
        subjective_terms = [
            "noncompliant", "difficult", "drug-seeking", "frequent flyer",
            "hysterical", "exaggerating", "malingering"
        ]
        
        for term in subjective_terms:
            if term in text_lower:
                indicators.append({
                    "type": "SUBJECTIVE_LANGUAGE",
                    "term": term,
                    "severity": "HIGH",
                    "recommendation": f"Consider replacing '{term}' with objective clinical language"
                })
        
        for demo, terms in bias_terms.items():
            if demo in demographics:
                for term in terms:
                    if term in text_lower:
                        indicators.append({
                            "type": "DEMOGRAPHIC_MENTION",
                            "dimension": demo,
                            "term": term,
                            "severity": "LOW",
                            "recommendation": "Ensure demographic information is clinically relevant"
                        })
        
        return indicators
    
    def _calculate_overall_bias_score(self, indicators: list[dict]) -> float:
        """Calculate overall bias score from indicators."""
        if not indicators:
            return 0.0
        
        severity_weights = {"HIGH": 0.4, "MEDIUM": 0.2, "LOW": 0.1}
        
        total_score = sum(
            severity_weights.get(ind.get("severity", "LOW"), 0.1)
            for ind in indicators
        )
        
        return min(1.0, total_score)
    
    def _generate_bias_recommendations(self, indicators: list[dict]) -> list[str]:
        """Generate recommendations based on bias indicators."""
        recommendations = []
        
        high_severity = [i for i in indicators if i.get("severity") == "HIGH"]
        if high_severity:
            recommendations.append(
                "Review and revise subjective language to ensure objective clinical documentation"
            )
        
        demo_mentions = [i for i in indicators if i.get("type") == "DEMOGRAPHIC_MENTION"]
        if len(demo_mentions) > 2:
            recommendations.append(
                "Consider whether all demographic references are clinically necessary"
            )
        
        if not recommendations:
            recommendations.append(
                "Documentation appears to follow objective clinical standards"
            )
        
        return recommendations
    
    def get_available_pipelines(self) -> dict:
        """Get list of available NLP pipelines."""
        return {
            "success": True,
            "pipelines": self.available_pipelines
        }
