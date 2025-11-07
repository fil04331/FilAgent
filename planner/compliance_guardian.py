"""ComplianceGuardian: supervision de conformité pour les plans HTN.

Ce module introduit une couche de contrôle après la génération d'un plan
HTN. L'objectif est double:

1. **Surveiller la charge** : détecter les plans trop volumineux ou avec un
   facteur de branchement qui dépasse les capacités déclarées.
2. **Évaluer le risque** : signaler ou bloquer les actions sensibles lorsque
   le mode strict est activé.

Il produit un rapport structuré afin que la trace de décision puisse être
archivée (AI Act, Loi 25) et fournit un mode strict pour les environnements
de production.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .task_graph import TaskGraph


class CompliancePolicyViolation(Exception):
    """Exception levée lorsque le plan ne respecte pas les règles."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


@dataclass
class ComplianceGuardianSettings:
    """Paramètres de gouvernance appliqués par le guardian."""

    enabled: bool = True
    strict_mode: bool = False
    max_tasks: int = 60
    max_branching_factor: int = 12
    warning_stress_threshold: float = 0.7
    failure_stress_threshold: float = 0.9
    flagged_actions: List[str] = field(
        default_factory=lambda: [
            "delete_file",
            "drop_database",
            "exfiltrate_data",
            "disable_compliance",
        ]
    )

    def to_dict(self) -> Dict[str, Any]:
        """Sérialise les paramètres pour les journaux."""

        return {
            "enabled": self.enabled,
            "strict_mode": self.strict_mode,
            "max_tasks": self.max_tasks,
            "max_branching_factor": self.max_branching_factor,
            "warning_stress_threshold": self.warning_stress_threshold,
            "failure_stress_threshold": self.failure_stress_threshold,
            "flagged_actions": list(self.flagged_actions),
        }


@dataclass
class ComplianceReport:
    """Rapport détaillé produit pour chaque plan évalué."""

    passed: bool
    stress_score: float
    total_tasks: int
    max_branching_factor: int
    flagged_actions: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Représentation sérialisable du rapport."""

        return {
            "passed": self.passed,
            "stress_score": self.stress_score,
            "total_tasks": self.total_tasks,
            "max_branching_factor": self.max_branching_factor,
            "flagged_actions": list(self.flagged_actions),
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
        }


class ComplianceGuardian:
    """Superviseur de conformité appliqué aux plans HTN."""

    def __init__(self, settings: Optional[ComplianceGuardianSettings] = None):
        self.settings = settings or ComplianceGuardianSettings()

    def assess_plan(self, plan_result: "PlanningResult") -> ComplianceReport:
        """Évaluer un résultat de planification."""

        if not self.settings.enabled:
            return ComplianceReport(
                passed=True,
                stress_score=0.0,
                total_tasks=len(plan_result.graph.tasks),
                max_branching_factor=0,
                warnings=["ComplianceGuardian disabled"],
                metadata={"enabled": False},
            )

        graph = plan_result.graph
        total_tasks = len(graph.tasks)
        max_branching = self._compute_max_branching(graph)
        stress_score = self._compute_stress_score(total_tasks)

        warnings: List[str] = []
        flagged_actions = self._collect_flagged_actions(graph)
        violation_reasons: List[str] = []

        if stress_score >= self.settings.warning_stress_threshold:
            warnings.append(
                "Plan stress nearing limits: "
                f"score={stress_score:.2f} (threshold={self.settings.warning_stress_threshold:.2f})"
            )

        if stress_score > self.settings.failure_stress_threshold:
            violation_reasons.append(
                "Plan stress score exceeded maximum threshold "
                f"({stress_score:.2f} > {self.settings.failure_stress_threshold:.2f})"
            )

        if max_branching > self.settings.max_branching_factor:
            violation_reasons.append(
                "Maximum branching factor exceeded "
                f"({max_branching} > {self.settings.max_branching_factor})"
            )

        if flagged_actions:
            warnings.append(
                "Flagged actions present: " + ", ".join(sorted(flagged_actions))
            )
            if self.settings.strict_mode:
                violation_reasons.append("Sensitive actions are forbidden in strict mode")

        metadata = {
            "settings": self.settings.to_dict(),
            "reasons": list(violation_reasons),
            "generated_tasks": total_tasks,
            "strict_mode": self.settings.strict_mode,
        }

        if violation_reasons and self.settings.strict_mode:
            raise CompliancePolicyViolation(
                "; ".join(violation_reasons),
                details=metadata,
            )

        passed = not violation_reasons

        return ComplianceReport(
            passed=passed,
            stress_score=stress_score,
            total_tasks=total_tasks,
            max_branching_factor=max_branching,
            flagged_actions=flagged_actions,
            warnings=warnings,
            metadata=metadata,
        )

    def _compute_stress_score(self, total_tasks: int) -> float:
        """Calculer un score de stress basé sur le nombre de tâches."""

        if self.settings.max_tasks <= 0:
            return 0.0
        return min(1.0, total_tasks / float(self.settings.max_tasks))

    @staticmethod
    def _compute_max_branching(graph: TaskGraph) -> int:
        """Déterminer le facteur de branchement maximal du graphe."""

        if not graph.adjacency_list:
            return 0
        return max(len(children) for children in graph.adjacency_list.values())

    def _collect_flagged_actions(self, graph: TaskGraph) -> List[str]:
        """Lister les actions signalées présentes dans le plan."""

        if not self.settings.flagged_actions:
            return []

        flagged = {
            task.action
            for task in graph.tasks.values()
            if task.action in self.settings.flagged_actions
        }
        return sorted(flagged)


__all__ = [
    "ComplianceGuardian",
    "ComplianceGuardianSettings",
    "CompliancePolicyViolation",
    "ComplianceReport",
]

