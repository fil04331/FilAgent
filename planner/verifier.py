"""
Task Verifier - Validation et Self-Checks pour HTN

Implémente:
- Validation des résultats de tâches
- Self-checks automatiques
- Niveaux de vérification (BASIC, STRICT, PARANOID)
- Tests unitaires sur sorties intermédiaires

Conformité:
- Loi 25: Validation systématique des sorties automatisées
- AI Act: Self-checks obligatoires pour transparence
- NIST AI RMF: Gestion des risques via validation multicouche

Niveaux de validation:
- BASIC: Vérifications minimales (type, non-null)
- STRICT: Vérifications structurelles (schéma, contraintes)
- PARANOID: Vérifications exhaustives (sémantique, cohérence)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, List, Dict, Optional, Union, Callable
from datetime import datetime, timezone
from .metrics import get_metrics

if TYPE_CHECKING:
    from .task_graph import Task, TaskGraph

# Types stricts pour le vérificateur
SchemaValue = Union[str, type, tuple[type, ...], Dict[str, Union[str, int, List[str]]]]
VerificationMetadataValue = Union[str, int, float, bool, List[str]]


class VerificationLevel(str, Enum):
    """Niveaux de rigueur de vérification"""

    BASIC = "basic"  # Minimal (rapide)
    STRICT = "strict"  # Standard (équilibré)
    PARANOID = "paranoid"  # Maximal (lent mais sûr)


@dataclass
class VerificationResult:
    """
    Résultat d'une vérification de tâche

    Attributes:
        passed: True si toutes les vérifications passent
        level: Niveau de vérification utilisé
        checks: Détails des vérifications individuelles
        errors: Liste des erreurs détectées
        warnings: Liste des avertissements
        confidence_score: Score de confiance (0-1)
        metadata: Métadonnées de traçabilité
    """

    passed: bool
    level: VerificationLevel
    checks: Dict[str, bool] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    confidence_score: float = 1.0
    metadata: Dict[str, VerificationMetadataValue] = field(default_factory=dict)

    def __post_init__(self):
        """Initialise métadonnées de traçabilité"""
        if "verified_at" not in self.metadata:
            self.metadata["verified_at"] = datetime.now(timezone.utc).isoformat()

    def to_dict(
        self,
    ) -> Dict[
        str,
        Union[bool, str, float, Dict[str, bool], List[str], Dict[str, VerificationMetadataValue]],
    ]:
        """Sérialise pour logging"""
        return {
            "passed": self.passed,
            "level": self.level.value,
            "checks": self.checks,
            "errors": self.errors,
            "warnings": self.warnings,
            "confidence_score": self.confidence_score,
            "metadata": self.metadata,
        }


class TaskVerifier:
    """
    Vérificateur de résultats de tâches HTN

    Responsabilités:
        - Valider les résultats selon le niveau requis
        - Exécuter self-checks automatiques
        - Détecter anomalies et incohérences
        - Tracer toutes les vérifications

    Usage:
        verifier = TaskVerifier(level=VerificationLevel.STRICT)
        result = verifier.verify_task(task, expected_schema)
        if not result.passed:
            print(f"Errors: {result.errors}")
    """

    def __init__(
        self,
        default_level: VerificationLevel = VerificationLevel.STRICT,
        enable_tracing: bool = True,
    ):
        """
        Initialise le vérificateur

        Args:
            default_level: Niveau de vérification par défaut
            enable_tracing: Active traçabilité complète
        """
        self.default_level = default_level
        self.enable_tracing = enable_tracing

        # Registre des vérificateurs personnalisés par action
        self._custom_verifiers: Dict[str, Callable] = {}

        # Statistiques
        self._stats = {
            "total_verifications": 0,
            "passed": 0,
            "failed": 0,
        }

    def register_custom_verifier(self, action: str, verifier: Callable):
        """
        Enregistre un vérificateur personnalisé pour une action

        Args:
            action: Nom de l'action
            verifier: Fonction de vérification (signature: func(task, result) -> VerificationResult)
        """
        self._custom_verifiers[action] = verifier

    def verify_task(
        self,
        task: "Task",
        level: Optional[VerificationLevel] = None,
        expected_schema: Optional[Dict[str, SchemaValue]] = None,
    ) -> VerificationResult:
        """
        Vérifie le résultat d'une tâche

        Args:
            task: Tâche dont le résultat doit être vérifié
            level: Niveau de vérification (override default)
            expected_schema: Schéma attendu pour le résultat

        Returns:
            VerificationResult avec détails des vérifications
        """
        level = level or self.default_level
        metadata = {
            "task_id": task.task_id,
            "task_name": task.name,
            "task_action": task.action,
            "level": level.value,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        checks = {}
        errors = []
        warnings = []

        try:
            # Vérification 1: Résultat existe
            if task.result is None:
                checks["result_exists"] = False
                errors.append("Task result is None")
            else:
                checks["result_exists"] = True

            # Vérification 2: Pas d'erreur reportée
            if task.error:
                checks["no_error"] = False
                errors.append(f"Task reported error: {task.error}")
            else:
                checks["no_error"] = True

            # Vérification 3: Statut cohérent
            if task.status.value not in ["completed", "failed"]:
                checks["status_coherent"] = False
                warnings.append(f"Unexpected status: {task.status.value}")
            else:
                checks["status_coherent"] = True

            # Vérifications selon le niveau
            if level in [VerificationLevel.STRICT, VerificationLevel.PARANOID]:
                # Vérification 4: Schéma (si fourni)
                if expected_schema and task.result is not None:
                    schema_valid = self._verify_schema(task.result, expected_schema)
                    checks["schema_valid"] = schema_valid
                    if not schema_valid:
                        errors.append("Result does not match expected schema")

                # Vérification 5: Cohérence temporelle
                temporal_ok = self._verify_temporal_coherence(task)
                checks["temporal_coherent"] = temporal_ok
                if not temporal_ok:
                    warnings.append("Temporal metadata inconsistent")

            if level == VerificationLevel.PARANOID:
                # Vérification 6: Sémantique (vérificateur custom)
                if task.action in self._custom_verifiers:
                    custom_result = self._custom_verifiers[task.action](task, task.result)
                    checks["custom_verification"] = custom_result.passed
                    errors.extend(custom_result.errors)
                    warnings.extend(custom_result.warnings)

                # Vérification 7: Cohérence avec dépendances
                # (à implémenter si graph disponible)

            # Calculer score de confiance
            passed_checks = sum(1 for v in checks.values() if v)
            total_checks = len(checks)
            confidence = passed_checks / total_checks if total_checks > 0 else 0.0

            # Déterminer succès global
            passed = len(errors) == 0

            # Mettre à jour statistiques
            self._stats["total_verifications"] += 1
            if passed:
                self._stats["passed"] += 1
            else:
                self._stats["failed"] += 1

            # Métriques: enregistrer vérification
            metrics = get_metrics()
            try:
                metrics.record_verification(
                    level=level.value,
                    passed=passed,
                    confidence_score=confidence,
                )
            except Exception:
                # Les métriques ne doivent jamais casser la vérification
                pass

            # Construire résultat
            metadata["completed_at"] = datetime.now(timezone.utc).isoformat()

            return VerificationResult(
                passed=passed,
                level=level,
                checks=checks,
                errors=errors,
                warnings=warnings,
                confidence_score=confidence,
                metadata=metadata,
            )

        except Exception as e:
            # Traçabilité: échec de vérification
            metadata["verification_error"] = str(e)
            metadata["completed_at"] = datetime.now(timezone.utc).isoformat()

            return VerificationResult(
                passed=False,
                level=level,
                checks=checks,
                errors=[f"Verification failed: {str(e)}"],
                warnings=warnings,
                confidence_score=0.0,
                metadata=metadata,
            )

    def verify_graph_results(
        self,
        graph: "TaskGraph",
        level: Optional[VerificationLevel] = None,
    ) -> Dict[str, VerificationResult]:
        """
        Vérifie tous les résultats d'un graphe

        Args:
            graph: TaskGraph avec tâches complétées
            level: Niveau de vérification

        Returns:
            Dict mapping task_id -> VerificationResult
        """
        results = {}

        for task_id, task in graph.tasks.items():
            if task.status.value == "completed":
                result = self.verify_task(task, level)
                results[task_id] = result

        return results

    def _verify_schema(self, result: object, schema: Dict[str, SchemaValue]) -> bool:
        """Vérifie que le résultat correspond au schéma attendu."""
        if not isinstance(schema, dict):
            return False

        # Support des schémas simples sous forme {"champ": type}
        if "type" not in schema:
            if not isinstance(result, dict):
                return False

            for key, expected in schema.items():
                if key not in result:
                    return False

                expected_types = expected if isinstance(expected, tuple) else (expected,)
                expected_types = tuple(t for t in expected_types if isinstance(t, type)) or (
                    type(result[key]),
                )

                if not isinstance(result[key], expected_types):
                    return False

            return True

        expected_type = schema.get("type")

        type_map = {
            "dict": dict,
            "list": list,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
        }

        if expected_type in type_map and not isinstance(result, type_map[expected_type]):
            return False

        if expected_type == "dict" and "required_keys" in schema:
            required = schema["required_keys"]
            if not all(key in result for key in required):
                return False

        if expected_type in ["list", "str"] and "min_length" in schema:
            if len(result) < schema["min_length"]:
                return False

        return True

    def _verify_temporal_coherence(self, task: "Task") -> bool:
        """
        Vérifie la cohérence temporelle des métadonnées

        Conditions:
        - created_at <= updated_at
        - updated_at <= completed_at (si existe)
        - Pas de timestamps futurs

        Args:
            task: Tâche à vérifier

        Returns:
            True si cohérent
        """
        try:
            created = datetime.fromisoformat(task.metadata.get("created_at", ""))
            updated = datetime.fromisoformat(task.metadata.get("updated_at", ""))
            now = datetime.now(timezone.utc)

            # Vérifier ordre chronologique
            if created > updated:
                return False

            # Vérifier pas de futur
            if created > now or updated > now:
                return False

            # Vérifier completed_at si existe
            if "completed_at" in task.metadata:
                completed = datetime.fromisoformat(task.metadata["completed_at"])
                if updated > completed or completed > now:
                    return False

            return True

        except (ValueError, KeyError):
            # Métadonnées manquantes ou invalides
            return False

    def self_check(self) -> Dict[str, Union[bool, Dict[str, bool], Dict[str, int], str]]:
        """
        Self-check du vérificateur lui-même

        Vérifie:
        - Statistiques cohérentes
        - Vérificateurs custom valides
        - État interne sain

        Returns:
            Dict avec résultats du self-check
        """
        checks: Dict[str, bool] = {}

        # Check 1: Statistiques cohérentes
        total = self._stats["total_verifications"]
        passed = self._stats["passed"]
        failed = self._stats["failed"]
        checks["stats_coherent"] = passed + failed == total

        # Check 2: Vérificateurs custom callables
        checks["custom_verifiers_valid"] = all(callable(v) for v in self._custom_verifiers.values())

        # Check 3: Configuration valide
        checks["config_valid"] = self.default_level in VerificationLevel

        return {
            "passed": all(checks.values()),
            "checks": checks,
            "stats": self._stats.copy(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_stats(self) -> Dict[str, int]:
        """Retourne les statistiques de vérification"""
        return self._stats.copy()
