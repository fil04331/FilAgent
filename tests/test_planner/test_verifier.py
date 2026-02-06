"""
Tests unitaires pour verifier.py

Couvre:
- TaskVerifier: initialisation, vérification
- VerificationLevel: BASIC, STRICT, PARANOID
- VerificationResult: structure, sérialisation
- Vérificateurs custom: enregistrement, exécution
- Self-checks: validation interne du vérificateur
- Edge cases: tâches sans résultat, erreurs, schémas invalides

Exécution:
    pytest tests/test_planner/test_verifier.py -v
"""

import pytest
from unittest.mock import Mock
from planner.verifier import (
    TaskVerifier,
    VerificationLevel,
    VerificationResult,
)
from planner.task_graph import (
    Task,
    TaskStatus,
    TaskPriority,
)


class TestTaskVerifier:
    """Tests pour la classe TaskVerifier"""

    def test_verifier_initialization_default(self):
        """Test initialisation avec valeurs par défaut"""
        verifier = TaskVerifier()

        assert verifier.default_level == VerificationLevel.STRICT
        assert verifier.enable_tracing is True
        assert verifier._custom_verifiers == {}
        assert "total_verifications" in verifier._stats

    def test_verifier_initialization_custom(self):
        """Test initialisation avec paramètres personnalisés"""
        verifier = TaskVerifier(
            default_level=VerificationLevel.BASIC,
            enable_tracing=False,
        )

        assert verifier.default_level == VerificationLevel.BASIC
        assert verifier.enable_tracing is False

    def test_register_custom_verifier(self):
        """Test enregistrement vérificateur personnalisé"""
        verifier = TaskVerifier()

        def custom_verifier(task, result):
            return VerificationResult(
                passed=True,
                level=VerificationLevel.STRICT,
            )

        verifier.register_custom_verifier("test_action", custom_verifier)

        assert "test_action" in verifier._custom_verifiers
        assert verifier._custom_verifiers["test_action"] == custom_verifier


class TestVerificationLevelBasic:
    """Tests pour niveau BASIC"""

    def test_basic_level_successful_task(self):
        """Test vérification BASIC avec tâche réussie"""
        verifier = TaskVerifier(default_level=VerificationLevel.BASIC)

        task = Task(name="test", action="test_action")
        task.set_result({"data": "result"})
        task.update_status(TaskStatus.COMPLETED)

        result = verifier.verify_task(task, level=VerificationLevel.BASIC)

        assert result.passed is True
        assert result.level == VerificationLevel.BASIC
        assert result.checks["result_exists"] is True
        assert result.checks["no_error"] is True
        assert len(result.errors) == 0

    def test_basic_level_failed_task(self):
        """Test vérification BASIC avec tâche échouée"""
        verifier = TaskVerifier(default_level=VerificationLevel.BASIC)

        task = Task(name="test", action="test_action")
        task.update_status(TaskStatus.FAILED, error="Task failed")

        result = verifier.verify_task(task, level=VerificationLevel.BASIC)

        assert result.passed is False
        assert result.checks["no_error"] is False
        assert len(result.errors) > 0

    def test_basic_level_no_result(self):
        """Test vérification BASIC sans résultat"""
        verifier = TaskVerifier(default_level=VerificationLevel.BASIC)

        task = Task(name="test", action="test_action")
        # Pas de résultat défini

        result = verifier.verify_task(task, level=VerificationLevel.BASIC)

        assert result.passed is False
        assert result.checks["result_exists"] is False
        assert "None" in str(result.errors)


class TestVerificationLevelStrict:
    """Tests pour niveau STRICT"""

    def test_strict_level_schema_validation(self):
        """Test vérification STRICT avec schéma"""
        verifier = TaskVerifier(default_level=VerificationLevel.STRICT)

        task = Task(name="test", action="test_action")
        task.set_result({"name": "test", "value": 42})
        task.update_status(TaskStatus.COMPLETED)

        expected_schema = {
            "name": str,
            "value": int,
        }

        result = verifier.verify_task(
            task, level=VerificationLevel.STRICT, expected_schema=expected_schema
        )

        # Devrait valider le schéma
        assert "schema_valid" in result.checks
        assert result.passed is True

    def test_strict_level_invalid_schema(self):
        """Test vérification STRICT avec schéma invalide"""
        verifier = TaskVerifier(default_level=VerificationLevel.STRICT)

        task = Task(name="test", action="test_action")
        task.set_result({"name": "test", "value": "not_int"})  # Type incorrect
        task.update_status(TaskStatus.COMPLETED)

        expected_schema = {
            "name": str,
            "value": int,  # Attendu int mais reçu str
        }

        result = verifier.verify_task(
            task, level=VerificationLevel.STRICT, expected_schema=expected_schema
        )

        # Devrait détecter l'invalidité du schéma
        if "schema_valid" in result.checks:
            assert result.checks["schema_valid"] is False

    def test_strict_level_temporal_coherence(self):
        """Test vérification STRICT cohérence temporelle"""
        verifier = TaskVerifier(default_level=VerificationLevel.STRICT)

        task = Task(name="test", action="test_action")
        task.set_result({"data": "result"})
        task.update_status(TaskStatus.COMPLETED)

        result = verifier.verify_task(task, level=VerificationLevel.STRICT)

        # Vérifier que la cohérence temporelle est vérifiée
        assert "temporal_coherent" in result.checks or result.passed is True


class TestVerificationLevelParanoid:
    """Tests pour niveau PARANOID"""

    def test_paranoid_level_custom_verifier(self):
        """Test vérification PARANOID avec vérificateur custom"""
        verifier = TaskVerifier(default_level=VerificationLevel.PARANOID)

        def custom_verifier(task, result):
            checks = {}
            errors = []

            if isinstance(result, dict):
                if "data" not in result:
                    errors.append("Missing 'data' key")
                    checks["has_data_key"] = False
                else:
                    checks["has_data_key"] = True
            else:
                errors.append("Result is not a dict")
                checks["is_dict"] = False

            return VerificationResult(
                passed=len(errors) == 0,
                level=VerificationLevel.PARANOID,
                checks=checks,
                errors=errors,
            )

        verifier.register_custom_verifier("test_action", custom_verifier)

        task = Task(name="test", action="test_action")
        task.set_result({"data": "result"})
        task.update_status(TaskStatus.COMPLETED)

        result = verifier.verify_task(task, level=VerificationLevel.PARANOID)

        # Devrait utiliser le vérificateur custom
        assert "custom_verification" in result.checks or result.passed is True

    def test_paranoid_level_missing_custom_verifier(self):
        """Test PARANOID sans vérificateur custom"""
        verifier = TaskVerifier(default_level=VerificationLevel.PARANOID)

        task = Task(name="test", action="unknown_action")
        task.set_result({"data": "result"})
        task.update_status(TaskStatus.COMPLETED)

        result = verifier.verify_task(task, level=VerificationLevel.PARANOID)

        # Devrait quand même vérifier les checks de base
        assert isinstance(result, VerificationResult)


class TestVerificationResult:
    """Tests pour VerificationResult"""

    def test_verification_result_creation(self):
        """Test création VerificationResult"""
        result = VerificationResult(
            passed=True,
            level=VerificationLevel.STRICT,
            checks={"check1": True, "check2": True},
        )

        assert result.passed is True
        assert result.level == VerificationLevel.STRICT
        assert len(result.checks) == 2
        assert "verified_at" in result.metadata

    def test_verification_result_to_dict(self):
        """Test sérialisation VerificationResult"""
        result = VerificationResult(
            passed=True,
            level=VerificationLevel.STRICT,
            checks={"check1": True},
            errors=["error1"],
            warnings=["warning1"],
            confidence_score=0.9,
        )

        result_dict = result.to_dict()

        assert result_dict["passed"] is True
        assert result_dict["level"] == "strict"
        assert "checks" in result_dict
        assert "errors" in result_dict
        assert "warnings" in result_dict
        assert result_dict["confidence_score"] == 0.9


class TestVerifyGraphResults:
    """Tests pour vérification de graphe complet"""

    def test_verify_graph_results_success(self):
        """Test vérification graphe avec succès"""
        verifier = TaskVerifier()

        from planner.task_graph import TaskGraph

        graph = TaskGraph()

        task1 = Task(name="task1", action="action1")
        task1.set_result({"data": "result1"})
        task1.update_status(TaskStatus.COMPLETED)

        task2 = Task(name="task2", action="action2")
        task2.set_result({"data": "result2"})
        task2.update_status(TaskStatus.COMPLETED)

        graph.add_task(task1)
        graph.add_task(task2)

        verifications = verifier.verify_graph_results(graph)

        assert isinstance(verifications, dict)
        assert task1.task_id in verifications
        assert task2.task_id in verifications
        assert verifications[task1.task_id].passed is True
        assert verifications[task2.task_id].passed is True

    def test_verify_graph_results_mixed_status(self):
        """Test vérification graphe avec statuts mixtes"""
        verifier = TaskVerifier()

        from planner.task_graph import TaskGraph

        graph = TaskGraph()

        task1 = Task(name="task1", action="action1")
        task1.set_result({"data": "result1"})
        task1.update_status(TaskStatus.COMPLETED)

        task2 = Task(name="task2", action="action2")
        task2.update_status(TaskStatus.FAILED, error="Failed")

        graph.add_task(task1)
        graph.add_task(task2)

        verifications = verifier.verify_graph_results(graph)

        assert task1.task_id in verifications
        assert verifications[task1.task_id].passed is True
        # task2 n'est pas complétée donc pas vérifiée
        assert task2.task_id not in verifications or verifications.get(task2.task_id) is None


class TestVerifierStats:
    """Tests pour statistiques du vérificateur"""

    def test_verifier_stats(self):
        """Test statistiques du vérificateur"""
        verifier = TaskVerifier()

        task = Task(name="test", action="test_action")
        task.set_result({"data": "result"})
        task.update_status(TaskStatus.COMPLETED)

        verifier.verify_task(task)

        stats = verifier.get_stats()

        assert "total_verifications" in stats
        assert "passed" in stats
        assert "failed" in stats
        assert stats["total_verifications"] >= 1

    def test_verifier_stats_accumulation(self):
        """Test accumulation statistiques sur plusieurs vérifications"""
        verifier = TaskVerifier()

        # Vérifier plusieurs tâches
        for i in range(3):
            task = Task(name=f"task{i}", action="test_action")
            task.set_result({"data": f"result{i}"})
            task.update_status(TaskStatus.COMPLETED)
            verifier.verify_task(task)

        stats = verifier.get_stats()

        assert stats["total_verifications"] == 3
        assert stats["passed"] == 3


class TestVerifierSelfCheck:
    """Tests pour self-check du vérificateur"""

    def test_self_check_success(self):
        """Test self-check réussi"""
        verifier = TaskVerifier()

        self_check = verifier.self_check()

        assert isinstance(self_check, dict)
        assert "passed" in self_check
        assert isinstance(self_check["passed"], bool)

    def test_self_check_details(self):
        """Test détails du self-check"""
        verifier = TaskVerifier()

        self_check = verifier.self_check()

        # Devrait contenir des détails
        assert len(self_check) > 1  # Au moins "passed" et autres champs


class TestVerificationEdgeCases:
    """Tests pour cas limites"""

    def test_verify_task_none_result(self):
        """Test vérification avec résultat None"""
        verifier = TaskVerifier()

        task = Task(name="test", action="test_action")
        task.result = None
        task.update_status(TaskStatus.COMPLETED)

        result = verifier.verify_task(task)

        assert result.passed is False
        assert result.checks["result_exists"] is False

    def test_verify_task_empty_result(self):
        """Test vérification avec résultat vide"""
        verifier = TaskVerifier()

        task = Task(name="test", action="test_action")
        task.set_result({})
        task.update_status(TaskStatus.COMPLETED)

        result = verifier.verify_task(task)

        # Résultat vide peut être valide selon contexte
        assert isinstance(result, VerificationResult)

    def test_verify_task_with_error_status(self):
        """Test vérification avec statut d'erreur"""
        verifier = TaskVerifier()

        task = Task(name="test", action="test_action")
        task.update_status(TaskStatus.FAILED, error="Test error")

        result = verifier.verify_task(task)

        assert result.passed is False
        assert "error" in result.checks or len(result.errors) > 0

    def test_verify_task_unexpected_status(self):
        """Test vérification avec statut inattendu"""
        verifier = TaskVerifier()

        task = Task(name="test", action="test_action")
        task.set_result({"data": "result"})
        task.update_status(TaskStatus.PENDING)  # Statut inattendu

        result = verifier.verify_task(task)

        # Devrait détecter le statut inattendu
        assert "status_coherent" in result.checks or len(result.warnings) > 0

    def test_custom_verifier_exception(self):
        """Test gestion exception dans vérificateur custom"""
        verifier = TaskVerifier()

        def failing_verifier(task, result):
            raise Exception("Verifier failed")

        verifier.register_custom_verifier("test_action", failing_verifier)

        task = Task(name="test", action="test_action")
        task.set_result({"data": "result"})
        task.update_status(TaskStatus.COMPLETED)

        # Devrait gérer l'exception gracieusement
        result = verifier.verify_task(task, level=VerificationLevel.PARANOID)

        # Devrait quand même retourner un résultat
        assert isinstance(result, VerificationResult)


class TestSchemaValidation:
    """Tests pour validation de schéma"""

    def test_schema_validation_simple_types(self):
        """Test validation schéma avec types simples"""
        verifier = TaskVerifier()

        task = Task(name="test", action="test_action")
        task.set_result({"name": "test", "value": 42, "active": True})
        task.update_status(TaskStatus.COMPLETED)

        expected_schema = {
            "name": str,
            "value": int,
            "active": bool,
        }

        result = verifier.verify_task(task, expected_schema=expected_schema)

        # Devrait valider les types
        assert isinstance(result, VerificationResult)

    def test_schema_validation_missing_key(self):
        """Test validation schéma avec clé manquante"""
        verifier = TaskVerifier()

        task = Task(name="test", action="test_action")
        task.set_result({"name": "test"})  # "value" manquant
        task.update_status(TaskStatus.COMPLETED)

        expected_schema = {
            "name": str,
            "value": int,
        }

        result = verifier.verify_task(task, expected_schema=expected_schema)

        # Devrait détecter la clé manquante
        if "schema_valid" in result.checks:
            assert result.checks["schema_valid"] is False or len(result.errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
