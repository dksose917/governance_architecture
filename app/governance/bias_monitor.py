"""Layer 5: Bias Monitoring System for the governance framework."""

import logging
from datetime import datetime
from typing import Optional, Any
from collections import defaultdict
import statistics

from app.models.base import AgentType
from app.models.audit import BiasMetric, ComplianceEvent

logger = logging.getLogger(__name__)


class BiasMonitor:
    """Monitors for algorithmic bias across all agent decisions.
    
    Monitoring Dimensions:
    - Demographic parity across patient populations
    - Treatment recommendation consistency
    - Wait time equity
    - Resource allocation fairness
    - Communication frequency balance
    
    Bias Detection Methods:
    - Statistical parity analysis
    - Disparate impact ratio calculation
    - NLP sentiment analysis across demographics
    - Outcome tracking by population segment
    """
    
    def __init__(self, disparate_impact_threshold: float = 0.8):
        self.disparate_impact_threshold = disparate_impact_threshold
        self.metrics: dict[str, BiasMetric] = {}
        self.compliance_events: dict[str, ComplianceEvent] = {}
        self.action_records: dict[str, list[dict]] = defaultdict(list)
        self.demographic_outcomes: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    
    def record_action_outcome(
        self,
        agent_type: AgentType,
        action_type: str,
        patient_demographics: dict[str, str],
        outcome: str,
        outcome_value: Optional[float] = None,
        metadata: Optional[dict] = None
    ):
        """Record an action outcome for bias analysis."""
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_type": agent_type.value,
            "action_type": action_type,
            "demographics": patient_demographics,
            "outcome": outcome,
            "outcome_value": outcome_value,
            "metadata": metadata or {}
        }
        
        key = f"{agent_type.value}_{action_type}"
        self.action_records[key].append(record)
        
        for dimension, value in patient_demographics.items():
            outcome_key = f"{key}_{dimension}_{value}"
            if outcome_value is not None:
                self.demographic_outcomes[key][outcome_key].append(outcome_value)
    
    def calculate_disparate_impact(
        self,
        agent_type: AgentType,
        action_type: str,
        dimension: str,
        protected_group: str,
        reference_group: str
    ) -> Optional[BiasMetric]:
        """Calculate disparate impact ratio for a specific dimension.
        
        Disparate Impact Ratio = (Protected Group Rate) / (Reference Group Rate)
        A ratio below 0.8 (80% rule) indicates potential discrimination.
        """
        key = f"{agent_type.value}_{action_type}"
        records = self.action_records.get(key, [])
        
        if len(records) < 10:
            logger.debug(f"Insufficient data for bias analysis: {len(records)} records")
            return None
        
        protected_outcomes = []
        reference_outcomes = []
        
        for record in records:
            demo_value = record["demographics"].get(dimension)
            outcome_value = record.get("outcome_value")
            
            if outcome_value is None:
                outcome_value = 1.0 if record["outcome"] == "POSITIVE" else 0.0
            
            if demo_value == protected_group:
                protected_outcomes.append(outcome_value)
            elif demo_value == reference_group:
                reference_outcomes.append(outcome_value)
        
        if len(protected_outcomes) < 5 or len(reference_outcomes) < 5:
            logger.debug(f"Insufficient samples for groups: protected={len(protected_outcomes)}, reference={len(reference_outcomes)}")
            return None
        
        protected_rate = statistics.mean(protected_outcomes)
        reference_rate = statistics.mean(reference_outcomes)
        
        if reference_rate == 0:
            disparity_ratio = 1.0 if protected_rate == 0 else float('inf')
        else:
            disparity_ratio = protected_rate / reference_rate
        
        threshold_exceeded = disparity_ratio < self.disparate_impact_threshold
        
        try:
            protected_stdev = statistics.stdev(protected_outcomes) if len(protected_outcomes) > 1 else 0
            reference_stdev = statistics.stdev(reference_outcomes) if len(reference_outcomes) > 1 else 0
            ci_lower = disparity_ratio - 1.96 * max(protected_stdev, reference_stdev)
            ci_upper = disparity_ratio + 1.96 * max(protected_stdev, reference_stdev)
        except Exception:
            ci_lower, ci_upper = disparity_ratio, disparity_ratio
        
        metric = BiasMetric(
            metric_type="DISPARATE_IMPACT",
            dimension=dimension,
            agent_type=agent_type,
            action_type=action_type,
            baseline_rate=reference_rate,
            observed_rate=protected_rate,
            disparity_ratio=disparity_ratio,
            threshold_exceeded=threshold_exceeded,
            sample_size=len(protected_outcomes) + len(reference_outcomes),
            confidence_interval=(ci_lower, ci_upper),
            details={
                "protected_group": protected_group,
                "reference_group": reference_group,
                "protected_count": len(protected_outcomes),
                "reference_count": len(reference_outcomes)
            }
        )
        
        self.metrics[metric.metric_id] = metric
        
        if threshold_exceeded:
            self._create_compliance_event(metric)
        
        logger.info(
            f"Disparate impact calculated: {dimension} {protected_group} vs {reference_group} "
            f"ratio={disparity_ratio:.3f} threshold_exceeded={threshold_exceeded}"
        )
        
        return metric
    
    def calculate_demographic_parity(
        self,
        agent_type: AgentType,
        action_type: str,
        dimension: str
    ) -> dict[str, float]:
        """Calculate outcome rates across all groups in a dimension."""
        key = f"{agent_type.value}_{action_type}"
        records = self.action_records.get(key, [])
        
        group_outcomes: dict[str, list[float]] = defaultdict(list)
        
        for record in records:
            group = record["demographics"].get(dimension)
            if group:
                outcome_value = record.get("outcome_value")
                if outcome_value is None:
                    outcome_value = 1.0 if record["outcome"] == "POSITIVE" else 0.0
                group_outcomes[group].append(outcome_value)
        
        rates = {}
        for group, outcomes in group_outcomes.items():
            if outcomes:
                rates[group] = statistics.mean(outcomes)
        
        return rates
    
    def analyze_wait_time_equity(
        self,
        agent_type: AgentType,
        dimension: str
    ) -> dict[str, Any]:
        """Analyze wait time equity across demographic groups."""
        key = f"{agent_type.value}_scheduling"
        records = self.action_records.get(key, [])
        
        wait_times: dict[str, list[float]] = defaultdict(list)
        
        for record in records:
            group = record["demographics"].get(dimension)
            wait_time = record.get("metadata", {}).get("wait_time_minutes")
            if group and wait_time is not None:
                wait_times[group].append(wait_time)
        
        analysis = {}
        for group, times in wait_times.items():
            if times:
                analysis[group] = {
                    "mean": statistics.mean(times),
                    "median": statistics.median(times),
                    "stdev": statistics.stdev(times) if len(times) > 1 else 0,
                    "count": len(times)
                }
        
        if len(analysis) >= 2:
            means = [v["mean"] for v in analysis.values()]
            max_disparity = max(means) / min(means) if min(means) > 0 else float('inf')
            analysis["_disparity_ratio"] = max_disparity
            analysis["_threshold_exceeded"] = max_disparity > (1 / self.disparate_impact_threshold)
        
        return analysis
    
    def analyze_communication_frequency(
        self,
        dimension: str
    ) -> dict[str, Any]:
        """Analyze communication frequency across demographic groups."""
        key = f"{AgentType.FAMILY_COMMUNICATION.value}_send_communication"
        records = self.action_records.get(key, [])
        
        comm_counts: dict[str, int] = defaultdict(int)
        patient_counts: dict[str, set] = defaultdict(set)
        
        for record in records:
            group = record["demographics"].get(dimension)
            patient_id = record.get("metadata", {}).get("patient_id")
            if group:
                comm_counts[group] += 1
                if patient_id:
                    patient_counts[group].add(patient_id)
        
        analysis = {}
        for group in comm_counts:
            patient_count = len(patient_counts[group])
            analysis[group] = {
                "total_communications": comm_counts[group],
                "unique_patients": patient_count,
                "avg_per_patient": comm_counts[group] / patient_count if patient_count > 0 else 0
            }
        
        return analysis
    
    def _create_compliance_event(self, metric: BiasMetric):
        """Create a compliance event for a bias threshold violation."""
        event = ComplianceEvent(
            event_type="BIAS_DETECTED",
            severity="WARNING",
            description=(
                f"Disparate impact detected in {metric.agent_type.value} "
                f"{metric.action_type} for {metric.dimension}. "
                f"Ratio: {metric.disparity_ratio:.3f} (threshold: {self.disparate_impact_threshold})"
            ),
            affected_agents=[metric.agent_type],
            remediation_required=True,
            remediation_status="PENDING"
        )
        
        self.compliance_events[event.event_id] = event
        
        logger.warning(f"Compliance event created: {event.event_id} - {event.description}")
    
    def run_full_bias_analysis(
        self,
        agent_type: Optional[AgentType] = None
    ) -> dict[str, Any]:
        """Run comprehensive bias analysis across all dimensions."""
        dimensions = ["age", "gender", "race", "ethnicity", "language"]
        
        agents = [agent_type] if agent_type else list(AgentType)
        
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "threshold": self.disparate_impact_threshold,
            "analyses": [],
            "violations": []
        }
        
        for agent in agents:
            for key in self.action_records:
                if not key.startswith(agent.value):
                    continue
                
                action_type = key.replace(f"{agent.value}_", "")
                
                for dimension in dimensions:
                    parity = self.calculate_demographic_parity(agent, action_type, dimension)
                    
                    if len(parity) >= 2:
                        groups = list(parity.keys())
                        for i, protected in enumerate(groups):
                            for reference in groups[i+1:]:
                                metric = self.calculate_disparate_impact(
                                    agent, action_type, dimension, protected, reference
                                )
                                if metric:
                                    results["analyses"].append({
                                        "agent": agent.value,
                                        "action": action_type,
                                        "dimension": dimension,
                                        "protected_group": protected,
                                        "reference_group": reference,
                                        "disparity_ratio": metric.disparity_ratio,
                                        "threshold_exceeded": metric.threshold_exceeded
                                    })
                                    
                                    if metric.threshold_exceeded:
                                        results["violations"].append({
                                            "metric_id": metric.metric_id,
                                            "agent": agent.value,
                                            "action": action_type,
                                            "dimension": dimension,
                                            "ratio": metric.disparity_ratio
                                        })
        
        results["total_analyses"] = len(results["analyses"])
        results["total_violations"] = len(results["violations"])
        
        return results
    
    def get_compliance_events(
        self,
        severity: Optional[str] = None,
        status: Optional[str] = None
    ) -> list[ComplianceEvent]:
        """Get compliance events, optionally filtered."""
        events = list(self.compliance_events.values())
        
        if severity:
            events = [e for e in events if e.severity == severity]
        if status:
            events = [e for e in events if e.remediation_status == status]
        
        return sorted(events, key=lambda x: x.timestamp, reverse=True)
    
    def update_compliance_event(
        self,
        event_id: str,
        status: str,
        assigned_to: Optional[str] = None
    ) -> bool:
        """Update a compliance event status."""
        if event_id not in self.compliance_events:
            return False
        
        event = self.compliance_events[event_id]
        event.remediation_status = status
        if assigned_to:
            event.assigned_to = assigned_to
        
        logger.info(f"Compliance event {event_id} updated: status={status}")
        return True
    
    def get_bias_summary(self) -> dict[str, Any]:
        """Get a summary of bias monitoring results."""
        return {
            "total_metrics": len(self.metrics),
            "total_compliance_events": len(self.compliance_events),
            "pending_remediations": len([
                e for e in self.compliance_events.values()
                if e.remediation_status == "PENDING"
            ]),
            "threshold": self.disparate_impact_threshold,
            "action_records_count": sum(len(v) for v in self.action_records.values()),
            "monitored_agents": list(set(
                k.split("_")[0] for k in self.action_records.keys()
            ))
        }
