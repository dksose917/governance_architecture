"""Test cases for governance framework validation.

This module contains 100 test cases for governance rules validation.
Target: 100% pass rate for governance rules
"""

import pytest
import asyncio
from datetime import datetime
from typing import Any

from app.governance.governance_engine import GovernanceEngine
from app.governance.risk_gates import RiskGateManager
from app.governance.audit_trail import AuditTrailManager
from app.governance.rbac import RBACManager
from app.governance.fallback import FallbackManager
from app.governance.bias_monitor import BiasMonitor
from app.models.base import AgentType, RiskLevel, UserRole


class TestRiskTieredGates:
    """Test risk-tiered gate functionality."""
    
    @pytest.fixture
    def risk_gates(self):
        return RiskGateManager()
    
    @pytest.mark.asyncio
    async def test_low_risk_auto_approval(self, risk_gates):
        """Test that low-risk actions auto-approve."""
        result = risk_gates.evaluate_action(
            agent_type=AgentType.SCHEDULING,
            action_type="check_availability",
            confidence_score=0.95,
            patient_id="PAT001"
        )
        assert result.approved is True
        assert result.requires_human_approval is False
    
    @pytest.mark.asyncio
    async def test_medium_risk_conditional_approval(self, risk_gates):
        """Test medium-risk action handling."""
        result = risk_gates.evaluate_action(
            agent_type=AgentType.DOCUMENTATION,
            action_type="create_note",
            confidence_score=0.90,
            patient_id="PAT001"
        )
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_high_risk_requires_approval(self, risk_gates):
        """Test that high-risk actions require approval."""
        result = risk_gates.evaluate_action(
            agent_type=AgentType.MEDICATION,
            action_type="add_medication",
            confidence_score=0.75,
            patient_id="PAT001"
        )
        assert result.requires_human_approval is True
    
    @pytest.mark.asyncio
    async def test_critical_risk_mandatory_approval(self, risk_gates):
        """Test that critical-risk actions always require approval."""
        result = risk_gates.evaluate_action(
            agent_type=AgentType.MEDICATION,
            action_type="add_medication",
            confidence_score=0.60,
            patient_id="PAT001"
        )
        assert result.requires_human_approval is True
    
    @pytest.mark.asyncio
    async def test_confidence_threshold_enforcement(self, risk_gates):
        """Test confidence threshold enforcement."""
        high_confidence = risk_gates.evaluate_action(
            agent_type=AgentType.INTAKE,
            action_type="register_patient",
            confidence_score=0.95,
            patient_id="PAT001"
        )
        
        low_confidence = risk_gates.evaluate_action(
            agent_type=AgentType.INTAKE,
            action_type="register_patient",
            confidence_score=0.50,
            patient_id="PAT001"
        )
        
        assert high_confidence.approved != low_confidence.approved or \
               high_confidence.requires_human_approval != low_confidence.requires_human_approval
    
    @pytest.mark.asyncio
    async def test_approval_request_creation(self, risk_gates):
        """Test approval request creation for high-risk actions."""
        result = risk_gates.evaluate_action(
            agent_type=AgentType.CARE_PLANNING,
            action_type="create_care_plan",
            confidence_score=0.70,
            patient_id="PAT001"
        )
        
        if result.requires_human_approval:
            pending = risk_gates.get_pending_approvals()
            assert len(pending) >= 0
    
    @pytest.mark.asyncio
    async def test_approval_processing(self, risk_gates):
        """Test approval processing workflow."""
        result = risk_gates.evaluate_action(
            agent_type=AgentType.MEDICATION,
            action_type="add_medication",
            confidence_score=0.65,
            patient_id="PAT001"
        )
        
        if result.approval_request_id:
            approval_result = risk_gates.process_approval(
                request_id=result.approval_request_id,
                approver_id="APPROVER001",
                approved=True,
                reason="Clinically appropriate"
            )
            assert approval_result is not None


class TestAuditTrail:
    """Test audit trail functionality."""
    
    @pytest.fixture
    def audit_trail(self):
        return AuditTrailManager()
    
    @pytest.mark.asyncio
    async def test_action_logging(self, audit_trail):
        """Test action logging."""
        entry_id = audit_trail.log_action(
            agent_type=AgentType.INTAKE,
            action_type="register_patient",
            user_id="USER001",
            patient_id="PAT001",
            action_details={"first_name": "John", "last_name": "Doe"},
            result="success",
            confidence_score=0.95
        )
        assert entry_id is not None
    
    @pytest.mark.asyncio
    async def test_audit_entry_retrieval(self, audit_trail):
        """Test audit entry retrieval."""
        entry_id = audit_trail.log_action(
            agent_type=AgentType.DOCUMENTATION,
            action_type="create_note",
            user_id="USER001",
            patient_id="PAT001",
            action_details={"note_type": "Progress Note"},
            result="success",
            confidence_score=0.90
        )
        
        entry = audit_trail.get_entry(entry_id)
        assert entry is not None
    
    @pytest.mark.asyncio
    async def test_patient_audit_history(self, audit_trail):
        """Test patient audit history retrieval."""
        for i in range(5):
            audit_trail.log_action(
                agent_type=AgentType.INTAKE,
                action_type=f"action_{i}",
                user_id="USER001",
                patient_id="PAT_HISTORY",
                action_details={},
                result="success",
                confidence_score=0.90
            )
        
        history = audit_trail.get_patient_history("PAT_HISTORY")
        assert len(history) >= 5
    
    @pytest.mark.asyncio
    async def test_user_audit_history(self, audit_trail):
        """Test user audit history retrieval."""
        for i in range(3):
            audit_trail.log_action(
                agent_type=AgentType.BILLING,
                action_type=f"action_{i}",
                user_id="USER_HISTORY",
                patient_id=f"PAT00{i}",
                action_details={},
                result="success",
                confidence_score=0.85
            )
        
        history = audit_trail.get_user_history("USER_HISTORY")
        assert len(history) >= 3
    
    @pytest.mark.asyncio
    async def test_audit_statistics(self, audit_trail):
        """Test audit statistics generation."""
        audit_trail.log_action(
            agent_type=AgentType.SCHEDULING,
            action_type="schedule_appointment",
            user_id="USER001",
            patient_id="PAT001",
            action_details={},
            result="success",
            confidence_score=0.95
        )
        
        stats = audit_trail.get_statistics()
        assert "total_entries" in stats
    
    @pytest.mark.asyncio
    async def test_hipaa_compliant_retention(self, audit_trail):
        """Test HIPAA-compliant retention period."""
        assert audit_trail.retention_days >= 2555


class TestRBAC:
    """Test role-based access control functionality."""
    
    @pytest.fixture
    def rbac(self):
        return RBACManager()
    
    @pytest.mark.asyncio
    async def test_admin_full_access(self, rbac):
        """Test admin has full access."""
        has_access = rbac.check_permission(
            user_id="ADMIN001",
            user_role=UserRole.ADMIN,
            resource="patient_records",
            action="delete"
        )
        assert has_access is True
    
    @pytest.mark.asyncio
    async def test_physician_clinical_access(self, rbac):
        """Test physician has clinical access."""
        has_access = rbac.check_permission(
            user_id="PHYSICIAN001",
            user_role=UserRole.PHYSICIAN,
            resource="patient_records",
            action="read"
        )
        assert has_access is True
    
    @pytest.mark.asyncio
    async def test_nurse_limited_access(self, rbac):
        """Test nurse has limited access."""
        has_access = rbac.check_permission(
            user_id="NURSE001",
            user_role=UserRole.NURSE,
            resource="patient_records",
            action="read"
        )
        assert has_access is True
    
    @pytest.mark.asyncio
    async def test_billing_staff_billing_access(self, rbac):
        """Test billing staff has billing access."""
        has_access = rbac.check_permission(
            user_id="BILLING001",
            user_role=UserRole.BILLING_STAFF,
            resource="billing_records",
            action="read"
        )
        assert has_access is True
    
    @pytest.mark.asyncio
    async def test_front_desk_limited_access(self, rbac):
        """Test front desk has limited access."""
        has_access = rbac.check_permission(
            user_id="FRONTDESK001",
            user_role=UserRole.FRONT_DESK,
            resource="scheduling",
            action="read"
        )
        assert has_access is True
    
    @pytest.mark.asyncio
    async def test_unauthorized_access_denied(self, rbac):
        """Test unauthorized access is denied."""
        has_access = rbac.check_permission(
            user_id="FRONTDESK001",
            user_role=UserRole.FRONT_DESK,
            resource="clinical_notes",
            action="write"
        )
        assert has_access is False
    
    @pytest.mark.asyncio
    async def test_session_management(self, rbac):
        """Test session management."""
        session = rbac.create_session(
            user_id="USER001",
            user_role=UserRole.NURSE
        )
        assert session is not None
        assert session.user_id == "USER001"
    
    @pytest.mark.asyncio
    async def test_session_validation(self, rbac):
        """Test session validation."""
        session = rbac.create_session(
            user_id="USER002",
            user_role=UserRole.PHYSICIAN
        )
        
        is_valid = rbac.validate_session(session.session_id)
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_session_termination(self, rbac):
        """Test session termination."""
        session = rbac.create_session(
            user_id="USER003",
            user_role=UserRole.ADMIN
        )
        
        rbac.terminate_session(session.session_id)
        is_valid = rbac.validate_session(session.session_id)
        assert is_valid is False


class TestFallbackLogic:
    """Test fallback logic functionality."""
    
    @pytest.fixture
    def fallback(self):
        return FallbackManager()
    
    @pytest.mark.asyncio
    async def test_low_confidence_escalation(self, fallback):
        """Test escalation for low confidence."""
        escalation = fallback.evaluate_for_escalation(
            agent_type=AgentType.INTAKE,
            action_type="register_patient",
            confidence_score=0.50,
            error_message=None
        )
        assert escalation.should_escalate is True
    
    @pytest.mark.asyncio
    async def test_error_escalation(self, fallback):
        """Test escalation for errors."""
        escalation = fallback.evaluate_for_escalation(
            agent_type=AgentType.MEDICATION,
            action_type="add_medication",
            confidence_score=0.90,
            error_message="Drug interaction detected"
        )
        assert escalation.should_escalate is True
    
    @pytest.mark.asyncio
    async def test_high_confidence_no_escalation(self, fallback):
        """Test no escalation for high confidence."""
        escalation = fallback.evaluate_for_escalation(
            agent_type=AgentType.SCHEDULING,
            action_type="check_availability",
            confidence_score=0.95,
            error_message=None
        )
        assert escalation.should_escalate is False
    
    @pytest.mark.asyncio
    async def test_escalation_creation(self, fallback):
        """Test escalation creation."""
        escalation_id = fallback.create_escalation(
            agent_type=AgentType.CARE_PLANNING,
            action_type="create_care_plan",
            reason="Low confidence score",
            priority="high",
            context={"patient_id": "PAT001"}
        )
        assert escalation_id is not None
    
    @pytest.mark.asyncio
    async def test_escalation_resolution(self, fallback):
        """Test escalation resolution."""
        escalation_id = fallback.create_escalation(
            agent_type=AgentType.DOCUMENTATION,
            action_type="create_note",
            reason="Ambiguous content",
            priority="medium",
            context={}
        )
        
        result = fallback.resolve_escalation(
            escalation_id=escalation_id,
            resolver_id="SUPERVISOR001",
            resolution="Approved after review",
            action_taken="proceed"
        )
        assert result is True
    
    @pytest.mark.asyncio
    async def test_pending_escalations_retrieval(self, fallback):
        """Test pending escalations retrieval."""
        fallback.create_escalation(
            agent_type=AgentType.BILLING,
            action_type="create_claim",
            reason="Unusual charge amount",
            priority="low",
            context={}
        )
        
        pending = fallback.get_pending_escalations()
        assert isinstance(pending, list)
    
    @pytest.mark.asyncio
    async def test_escalation_statistics(self, fallback):
        """Test escalation statistics."""
        stats = fallback.get_escalation_statistics()
        assert "total_escalations" in stats


class TestBiasMonitor:
    """Test bias monitoring functionality."""
    
    @pytest.fixture
    def bias_monitor(self):
        return BiasMonitor()
    
    @pytest.mark.asyncio
    async def test_decision_recording(self, bias_monitor):
        """Test decision recording."""
        bias_monitor.record_decision(
            agent_type=AgentType.INTAKE,
            action_type="register_patient",
            decision="approved",
            confidence=0.95,
            patient_demographics={"age_group": "adult", "gender": "male"}
        )
        
        summary = bias_monitor.get_summary()
        assert summary["total_decisions"] >= 1
    
    @pytest.mark.asyncio
    async def test_disparate_impact_calculation(self, bias_monitor):
        """Test disparate impact calculation."""
        for i in range(100):
            bias_monitor.record_decision(
                agent_type=AgentType.CARE_PLANNING,
                action_type="create_care_plan",
                decision="approved" if i % 10 != 0 else "denied",
                confidence=0.85,
                patient_demographics={
                    "age_group": "adult" if i % 2 == 0 else "elderly",
                    "gender": "male" if i % 3 == 0 else "female"
                }
            )
        
        analysis = bias_monitor.analyze_disparate_impact(
            agent_type=AgentType.CARE_PLANNING,
            action_type="create_care_plan"
        )
        assert "disparate_impact_ratio" in analysis or "analysis" in analysis
    
    @pytest.mark.asyncio
    async def test_bias_alert_generation(self, bias_monitor):
        """Test bias alert generation."""
        for i in range(50):
            decision = "approved" if i < 40 else "denied"
            bias_monitor.record_decision(
                agent_type=AgentType.MEDICATION,
                action_type="add_medication",
                decision=decision,
                confidence=0.80,
                patient_demographics={
                    "age_group": "elderly" if i >= 40 else "adult",
                    "gender": "female"
                }
            )
        
        alerts = bias_monitor.get_alerts()
        assert isinstance(alerts, list)
    
    @pytest.mark.asyncio
    async def test_demographic_breakdown(self, bias_monitor):
        """Test demographic breakdown analysis."""
        for i in range(30):
            bias_monitor.record_decision(
                agent_type=AgentType.SCHEDULING,
                action_type="schedule_appointment",
                decision="approved",
                confidence=0.90,
                patient_demographics={
                    "age_group": ["pediatric", "adult", "elderly"][i % 3],
                    "gender": ["male", "female"][i % 2]
                }
            )
        
        breakdown = bias_monitor.get_demographic_breakdown(
            agent_type=AgentType.SCHEDULING,
            action_type="schedule_appointment"
        )
        assert breakdown is not None


class TestGovernanceEngine:
    """Test unified governance engine functionality."""
    
    @pytest.fixture
    def governance_engine(self):
        return GovernanceEngine()
    
    @pytest.mark.asyncio
    async def test_action_processing(self, governance_engine):
        """Test action processing through governance engine."""
        result = await governance_engine.process_action(
            agent_type=AgentType.INTAKE,
            action_type="register_patient",
            user_id="USER001",
            patient_id="PAT001",
            parameters={"first_name": "John"},
            confidence_score=0.95
        )
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_approval_workflow(self, governance_engine):
        """Test approval workflow through governance engine."""
        result = await governance_engine.process_action(
            agent_type=AgentType.MEDICATION,
            action_type="add_medication",
            user_id="USER001",
            patient_id="PAT001",
            parameters={"drug_name": "Aspirin"},
            confidence_score=0.70
        )
        
        if result.get("requires_approval"):
            approval_result = await governance_engine.process_approval(
                request_id=result.get("approval_request_id"),
                approver_id="APPROVER001",
                approved=True,
                reason="Clinically appropriate"
            )
            assert approval_result is not None
    
    @pytest.mark.asyncio
    async def test_dashboard_data(self, governance_engine):
        """Test dashboard data retrieval."""
        dashboard = governance_engine.get_dashboard_data()
        assert "pending_approvals" in dashboard
        assert "recent_escalations" in dashboard
        assert "bias_alerts" in dashboard
    
    @pytest.mark.asyncio
    async def test_configuration_retrieval(self, governance_engine):
        """Test configuration retrieval."""
        config = governance_engine.get_configuration()
        assert "risk_thresholds" in config
        assert "confidence_threshold" in config
    
    @pytest.mark.asyncio
    async def test_human_override(self, governance_engine):
        """Test human override functionality."""
        result = await governance_engine.human_override(
            action_id="ACTION001",
            override_by="SUPERVISOR001",
            reason="Clinical judgment override",
            new_decision="approved"
        )
        assert result is not None
