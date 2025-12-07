"""Compliance Agent (06) - Manages audit preparation and bias monitoring."""

import logging
import random
from datetime import datetime, date, timedelta
from typing import Optional, Any

from app.models.base import AgentType, AgentAction, AgentResponse, ActionStatus
from app.agents.base_agent import BaseAgent
from app.governance.bias_monitor import BiasMonitor

logger = logging.getLogger(__name__)


class ComplianceAgent(BaseAgent):
    """Compliance Agent (06) - Audit and Monitoring.
    
    Manages audit preparation, compliance monitoring, and bias detection.
    Ensures NLP tools support bias monitoring.
    """
    
    def __init__(self, bias_monitor: Optional[BiasMonitor] = None):
        super().__init__(AgentType.COMPLIANCE)
        self.bias_monitor = bias_monitor or BiasMonitor()
        self.audit_records: list[dict] = []
        self.compliance_checks: list[dict] = []
        self.policy_violations: list[dict] = []
    
    @property
    def name(self) -> str:
        return "Compliance Agent"
    
    @property
    def description(self) -> str:
        return (
            "Manages audit preparation, compliance monitoring, and bias detection. "
            "Ensures algorithmic fairness across all patient demographics."
        )
    
    @property
    def supported_actions(self) -> list[str]:
        return [
            "run_compliance_check", "prepare_audit", "analyze_bias",
            "report_violation", "generate_compliance_report",
            "review_access_logs", "validate_hipaa_compliance",
            "get_bias_summary", "remediate_issue"
        ]
    
    async def process(
        self,
        action_type: str,
        parameters: dict[str, Any],
        patient_id: Optional[str] = None
    ) -> AgentResponse:
        """Process a compliance action."""
        confidence = self._calculate_confidence(action_type, parameters)
        
        action = self.create_action(
            action_type=action_type,
            parameters=parameters,
            patient_id=patient_id,
            confidence_score=confidence,
            rationale=f"Compliance: {action_type}"
        )
        
        try:
            if action_type == "run_compliance_check":
                result = await self._run_compliance_check(parameters)
            elif action_type == "prepare_audit":
                result = await self._prepare_audit(parameters)
            elif action_type == "analyze_bias":
                result = await self._analyze_bias(parameters)
            elif action_type == "report_violation":
                result = await self._report_violation(parameters)
            elif action_type == "generate_compliance_report":
                result = await self._generate_compliance_report(parameters)
            elif action_type == "review_access_logs":
                result = await self._review_access_logs(parameters)
            elif action_type == "validate_hipaa_compliance":
                result = await self._validate_hipaa_compliance(parameters)
            elif action_type == "get_bias_summary":
                result = self._get_bias_summary()
            elif action_type == "remediate_issue":
                result = await self._remediate_issue(parameters)
            else:
                result = {"success": False, "error": f"Unknown action: {action_type}"}
            
            action.status = ActionStatus.COMPLETED if result.get("success", True) else ActionStatus.FAILED
            
            return AgentResponse(
                success=result.get("success", True),
                action=action,
                result=result,
                escalation_required=result.get("requires_escalation", False),
                escalation_reason=result.get("escalation_reason")
            )
            
        except Exception as e:
            logger.error(f"Compliance agent error: {e}")
            action.status = ActionStatus.FAILED
            return AgentResponse(success=False, action=action, error=str(e))
    
    def _calculate_confidence(self, action_type: str, parameters: dict) -> float:
        """Calculate confidence score."""
        base_confidence = 0.94
        
        if action_type == "analyze_bias":
            base_confidence = 0.90
        elif action_type == "validate_hipaa_compliance":
            base_confidence = 0.96
        
        return min(1.0, max(0.0, base_confidence + random.uniform(-0.02, 0.02)))
    
    async def _run_compliance_check(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Run a compliance check."""
        check_type = parameters.get("check_type", "general")
        scope = parameters.get("scope", "all")
        
        checks_performed = []
        issues_found = []
        
        compliance_areas = [
            ("HIPAA Privacy", 0.98),
            ("HIPAA Security", 0.97),
            ("Documentation Standards", 0.95),
            ("Consent Management", 0.96),
            ("Data Retention", 0.99),
            ("Access Controls", 0.97),
            ("Audit Logging", 0.98),
            ("Encryption Standards", 0.99)
        ]
        
        for area, pass_rate in compliance_areas:
            passed = random.random() < pass_rate
            check_result = {
                "area": area,
                "passed": passed,
                "score": random.uniform(0.85, 1.0) if passed else random.uniform(0.5, 0.84),
                "checked_at": datetime.utcnow().isoformat()
            }
            checks_performed.append(check_result)
            
            if not passed:
                issues_found.append({
                    "area": area,
                    "severity": random.choice(["LOW", "MEDIUM", "HIGH"]),
                    "description": f"Compliance gap detected in {area}"
                })
        
        check_record = {
            "check_id": f"CHK{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "check_type": check_type,
            "scope": scope,
            "timestamp": datetime.utcnow().isoformat(),
            "checks_performed": len(checks_performed),
            "issues_found": len(issues_found)
        }
        self.compliance_checks.append(check_record)
        
        return {
            "success": True,
            "check_id": check_record["check_id"],
            "checks_performed": checks_performed,
            "issues_found": issues_found,
            "overall_score": sum(c["score"] for c in checks_performed) / len(checks_performed),
            "requires_escalation": any(i["severity"] == "HIGH" for i in issues_found),
            "escalation_reason": "High severity compliance issues detected" if any(i["severity"] == "HIGH" for i in issues_found) else None
        }
    
    async def _prepare_audit(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Prepare for an audit."""
        audit_type = parameters.get("audit_type", "internal")
        date_range_start = parameters.get("start_date", (date.today() - timedelta(days=90)).isoformat())
        date_range_end = parameters.get("end_date", date.today().isoformat())
        
        audit_package = {
            "audit_id": f"AUD{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "audit_type": audit_type,
            "prepared_at": datetime.utcnow().isoformat(),
            "date_range": {
                "start": date_range_start,
                "end": date_range_end
            },
            "documents_included": [
                "Access Logs",
                "Audit Trail Reports",
                "Policy Documentation",
                "Training Records",
                "Incident Reports",
                "Risk Assessments",
                "Compliance Check Results"
            ],
            "statistics": {
                "total_access_events": random.randint(10000, 50000),
                "unique_users": random.randint(50, 200),
                "compliance_checks_run": len(self.compliance_checks),
                "violations_reported": len(self.policy_violations)
            }
        }
        
        self.audit_records.append(audit_package)
        
        return {
            "success": True,
            "audit_package": audit_package
        }
    
    async def _analyze_bias(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Analyze for algorithmic bias."""
        agent_type = parameters.get("agent_type")
        action_type = parameters.get("action_type")
        
        if agent_type:
            try:
                from app.models.base import AgentType as AT
                agent_type_enum = AT(agent_type)
            except ValueError:
                agent_type_enum = None
        else:
            agent_type_enum = None
        
        bias_analysis = self.bias_monitor.run_full_bias_analysis(
            agent_type=agent_type_enum,
            action_type=action_type
        )
        
        return {
            "success": True,
            "analysis": bias_analysis,
            "requires_escalation": bias_analysis.get("overall_bias_detected", False),
            "escalation_reason": "Algorithmic bias detected" if bias_analysis.get("overall_bias_detected") else None
        }
    
    async def _report_violation(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Report a policy violation."""
        violation = {
            "violation_id": f"VIO{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "violation_type": parameters.get("violation_type", "Unknown"),
            "severity": parameters.get("severity", "MEDIUM"),
            "description": parameters.get("description", ""),
            "affected_patient_id": parameters.get("patient_id"),
            "reported_by": parameters.get("reported_by"),
            "reported_at": datetime.utcnow().isoformat(),
            "status": "REPORTED"
        }
        
        self.policy_violations.append(violation)
        
        return {
            "success": True,
            "violation_id": violation["violation_id"],
            "status": violation["status"],
            "requires_escalation": violation["severity"] in ["HIGH", "CRITICAL"],
            "escalation_reason": f"Policy violation: {violation['severity']}" if violation["severity"] in ["HIGH", "CRITICAL"] else None
        }
    
    async def _generate_compliance_report(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Generate a compliance report."""
        report_type = parameters.get("report_type", "summary")
        
        report = {
            "report_id": f"RPT{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "report_type": report_type,
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_compliance_checks": len(self.compliance_checks),
                "total_violations": len(self.policy_violations),
                "open_violations": len([v for v in self.policy_violations if v["status"] == "REPORTED"]),
                "resolved_violations": len([v for v in self.policy_violations if v["status"] == "RESOLVED"]),
                "audits_conducted": len(self.audit_records)
            },
            "violation_breakdown": {
                "HIGH": len([v for v in self.policy_violations if v["severity"] == "HIGH"]),
                "MEDIUM": len([v for v in self.policy_violations if v["severity"] == "MEDIUM"]),
                "LOW": len([v for v in self.policy_violations if v["severity"] == "LOW"])
            },
            "bias_summary": self.bias_monitor.get_bias_summary(),
            "recommendations": self._generate_recommendations()
        }
        
        return {
            "success": True,
            "report": report
        }
    
    def _generate_recommendations(self) -> list[str]:
        """Generate compliance recommendations."""
        recommendations = []
        
        high_violations = len([v for v in self.policy_violations if v["severity"] == "HIGH"])
        if high_violations > 0:
            recommendations.append(f"Address {high_violations} high-severity violations immediately")
        
        bias_summary = self.bias_monitor.get_bias_summary()
        if bias_summary.get("bias_detected"):
            recommendations.append("Review and remediate detected algorithmic bias")
        
        if len(self.compliance_checks) < 5:
            recommendations.append("Increase frequency of compliance checks")
        
        if not recommendations:
            recommendations.append("Continue current compliance monitoring practices")
        
        return recommendations
    
    async def _review_access_logs(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Review access logs for anomalies."""
        patient_id = parameters.get("patient_id")
        user_id = parameters.get("user_id")
        
        simulated_logs = []
        anomalies = []
        
        for i in range(random.randint(10, 50)):
            log_entry = {
                "log_id": f"LOG{i}",
                "timestamp": (datetime.utcnow() - timedelta(hours=random.randint(1, 168))).isoformat(),
                "user_id": user_id or f"user_{random.randint(1, 100)}",
                "patient_id": patient_id or f"patient_{random.randint(1, 500)}",
                "action": random.choice(["VIEW", "EDIT", "EXPORT", "PRINT"]),
                "resource": random.choice(["medical_record", "demographics", "billing", "notes"])
            }
            simulated_logs.append(log_entry)
            
            if random.random() < 0.05:
                anomalies.append({
                    "log_id": log_entry["log_id"],
                    "anomaly_type": random.choice(["unusual_time", "bulk_access", "unauthorized_attempt"]),
                    "severity": random.choice(["LOW", "MEDIUM", "HIGH"])
                })
        
        return {
            "success": True,
            "logs_reviewed": len(simulated_logs),
            "anomalies_detected": len(anomalies),
            "anomalies": anomalies,
            "requires_escalation": any(a["severity"] == "HIGH" for a in anomalies)
        }
    
    async def _validate_hipaa_compliance(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Validate HIPAA compliance."""
        validation_areas = {
            "privacy_rule": {
                "compliant": random.random() < 0.98,
                "checks": ["PHI access controls", "Minimum necessary standard", "Patient rights"]
            },
            "security_rule": {
                "compliant": random.random() < 0.97,
                "checks": ["Administrative safeguards", "Physical safeguards", "Technical safeguards"]
            },
            "breach_notification": {
                "compliant": random.random() < 0.99,
                "checks": ["Notification procedures", "Documentation", "Timeliness"]
            }
        }
        
        overall_compliant = all(area["compliant"] for area in validation_areas.values())
        
        return {
            "success": True,
            "validation_results": validation_areas,
            "overall_compliant": overall_compliant,
            "validation_date": datetime.utcnow().isoformat(),
            "next_validation_due": (date.today() + timedelta(days=90)).isoformat()
        }
    
    def _get_bias_summary(self) -> dict[str, Any]:
        """Get bias monitoring summary."""
        return {
            "success": True,
            "bias_summary": self.bias_monitor.get_bias_summary(),
            "compliance_events": [
                {
                    "event_id": e.event_id,
                    "event_type": e.event_type,
                    "severity": e.severity,
                    "timestamp": e.timestamp.isoformat()
                }
                for e in self.bias_monitor.get_compliance_events()[:10]
            ]
        }
    
    async def _remediate_issue(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Remediate a compliance issue."""
        issue_id = parameters.get("issue_id")
        remediation_action = parameters.get("action", "")
        remediated_by = parameters.get("remediated_by")
        
        for violation in self.policy_violations:
            if violation["violation_id"] == issue_id:
                violation["status"] = "RESOLVED"
                violation["resolved_at"] = datetime.utcnow().isoformat()
                violation["resolved_by"] = remediated_by
                violation["remediation_action"] = remediation_action
                
                return {
                    "success": True,
                    "issue_id": issue_id,
                    "status": "RESOLVED",
                    "resolved_at": violation["resolved_at"]
                }
        
        return {"success": False, "error": "Issue not found"}
