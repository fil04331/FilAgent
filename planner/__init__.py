"""
Hierarchical Task Network (HTN) Planning Module for FilAgent

Ce module implémente un système de planification hiérarchique permettant de:
- Décomposer des requêtes complexes en DAG de sous-tâches
- Gérer les dépendances entre tâches
- Exécuter avec tri topologique et parallélisation
- Tracer toutes les décisions de planification (conformité)

Conformité:
- Loi 25 (QC): Traçabilité des décisions automatisées
- RGPD: Transparence des processus de traitement
- AI Act: Explicabilité des décompositions de tâches
- NIST AI RMF: Gestion des risques par validation à chaque étape

Author: FilAgent Team
Version: 1.0.0
Date: 2025-11-01
"""

from .task_graph import (
    Task,
    TaskStatus,
    TaskPriority,
    TaskGraph,
    TaskDecompositionError,
)

from .planner import (
    HierarchicalPlanner,
    PlanningStrategy,
    PlanningResult,
)

from .compliance_guardian import (
    ComplianceGuardian,
    ComplianceGuardianSettings,
    CompliancePolicyViolation,
    ComplianceReport,
)

from .executor import (
    TaskExecutor,
    ExecutionResult,
    ExecutionError,
    ExecutionStrategy,
)

from .verifier import (
    TaskVerifier,
    VerificationResult,
    VerificationLevel,
)

__all__ = [
    # Core types
    "Task",
    "TaskStatus",
    "TaskPriority",
    "TaskGraph",
    "TaskDecompositionError",
    
    # Planner
    "HierarchicalPlanner",
    "PlanningStrategy",
    "PlanningResult",

    # Compliance guardian
    "ComplianceGuardian",
    "ComplianceGuardianSettings",
    "CompliancePolicyViolation",
    "ComplianceReport",

    # Executor
    "TaskExecutor",
    "ExecutionResult",
    "ExecutionError",
    "ExecutionStrategy",
    
    # Verifier
    "TaskVerifier",
    "VerificationResult",
    "VerificationLevel",
]

__version__ = "1.0.0"
