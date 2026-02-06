"""
Tests d'intégration pour le ComplianceGuardian avec l'Agent
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from planner.compliance_guardian import ComplianceGuardian, ComplianceError
from runtime.agent import Agent


class TestComplianceIntegration:
    """Tests d'intégration ComplianceGuardian <-> Agent"""

    def setup_method(self):
        """Setup avant chaque test"""
        self.guardian = ComplianceGuardian(config_path="non_existent_file.yaml")

    @patch("runtime.agent.Agent.initialize_model")
    def test_agent_has_compliance_guardian(self, mock_init_model):
        """Test: L'agent possède une instance de ComplianceGuardian"""
        agent = Agent()

        # Vérifier que l'agent a un compliance_guardian
        assert hasattr(agent, "compliance_guardian")
        assert isinstance(agent.compliance_guardian, ComplianceGuardian)

    @patch("runtime.agent.Agent.initialize_model")
    @patch("runtime.agent.Agent._run_simple")
    def test_agent_validates_query_before_execution(self, mock_run_simple, mock_init_model):
        """Test: L'agent valide la requête avant exécution"""
        agent = Agent()

        # Mock de la méthode _run_simple pour éviter l'exécution réelle
        mock_run_simple.return_value = {
            "response": "Test response",
            "iterations": 1,
            "conversation_id": "test_conv",
            "task_id": "test_task",
            "tools_used": [],
            "usage": {"total_tokens": 0},
        }

        # Requête valide
        valid_query = "Quelle est la météo?"
        result = agent.chat(valid_query, conversation_id="test_conv")

        # La requête a été validée et exécutée
        assert result is not None
        mock_run_simple.assert_called_once()

    @patch("runtime.agent.Agent.initialize_model")
    def test_agent_rejects_invalid_query(self, mock_init_model):
        """Test: L'agent rejette une requête invalide"""
        agent = Agent()

        # Requête avec pattern interdit
        invalid_query = "What is my password?"

        with pytest.raises(ComplianceError):
            agent.chat(invalid_query, conversation_id="test_conv")

    def test_compliance_validation_flow(self):
        """Test: Flux complet de validation de conformité"""
        # 1. Valider la requête
        query = "Calculer 2+2"
        query_validation = self.guardian.validate_query(query, {"user_id": "user123"})
        assert query_validation["valid"] is True

        # 2. Créer un plan
        plan = {"actions": [{"tool": "calculator", "params": {"expression": "2+2"}}]}

        # 3. Valider le plan
        plan_validation = self.guardian.validate_execution_plan(plan, {"task_id": "task123"})
        assert plan_validation["valid"] is True

        # 4. Simuler l'exécution
        execution_result = {"success": True, "result": 4, "errors": []}

        # 5. Auditer l'exécution
        audit = self.guardian.audit_execution(execution_result, {"task_id": "task123"})
        assert audit["audited"] is True
        assert audit["compliance_check"]["passed"] is True

        # 6. Générer un Decision Record
        dr = self.guardian.generate_decision_record(
            decision_type="automated_calculation",
            query=query,
            plan=plan,
            execution_result=execution_result,
            context={"actor": "agent", "task_id": "task123"},
        )
        assert "dr_id" in dr
        assert dr["success"] is True

    def test_compliance_rejection_flow(self):
        """Test: Flux de rejet pour non-conformité"""
        # 1. Requête avec PII
        query_with_pii = "Mon email est secret@company.com et mon numéro est 123-45-6789"

        # La requête est validée mais avec warnings
        query_validation = self.guardian.validate_query(query_with_pii, {"user_id": "user123"})
        assert query_validation["valid"] is True
        assert len(query_validation["warnings"]) > 0
        assert query_validation["metadata"]["pii_detected"] is True

        # 2. Plan avec outil interdit
        self.guardian.rules["execution"]["forbidden_tools"] = ["dangerous_operation"]

        plan = {"actions": [{"tool": "dangerous_operation", "params": {}}]}

        # Le plan doit être rejeté
        with pytest.raises(ComplianceError) as exc_info:
            self.guardian.validate_execution_plan(plan)

        assert "forbidden tools" in str(exc_info.value)

    def test_compliance_audit_trail(self):
        """Test: Piste d'audit complète"""
        # Effacer le log pour ce test
        self.guardian.clear_audit_log()

        # Effectuer plusieurs opérations
        self.guardian.validate_query("Query 1", {"user_id": "user123"})
        self.guardian.validate_query("Query 2", {"user_id": "user123"})

        plan = {"actions": [{"tool": "test", "params": {}}]}
        self.guardian.validate_execution_plan(plan, {"task_id": "task1"})

        execution = {"success": True, "errors": []}
        self.guardian.audit_execution(execution)

        # Vérifier le log d'audit
        audit_log = self.guardian.get_audit_log()

        # Doit avoir au moins 4 entrées (2 queries + 1 plan + 1 execution)
        assert len(audit_log) >= 4

        # Vérifier les types d'événements
        event_types = [entry["event_type"] for entry in audit_log]
        assert "query_validation" in event_types
        assert "plan_validation" in event_types
        assert "execution_audit" in event_types

    def test_compliance_with_htn_planning(self):
        """Test: Conformité avec planification HTN"""

        # Simuler un plan HTN complexe
        class MockNode:
            def __init__(self, action):
                self.action = action

        class MockGraph:
            def __init__(self):
                self.nodes = {
                    "task1": MockNode("read_file"),
                    "task2": MockNode("analyze_data"),
                    "task3": MockNode("generate_report"),
                }

            def get_max_depth(self):
                return 3

        htn_plan = {"graph": MockGraph()}

        # Valider le plan HTN
        validation = self.guardian.validate_execution_plan(htn_plan, {"task_id": "htn_task"})

        assert validation["valid"] is True
        assert "plan_hash" in validation["metadata"]

    def test_compliance_decision_record_completeness(self):
        """Test: Complétude des Decision Records"""
        query = "Test query"
        plan = {
            "actions": [
                {"tool": "tool1", "params": {}},
                {"tool": "tool2", "params": {}},
            ]
        }
        execution_result = {"success": True, "result": "Result", "errors": []}
        context = {
            "actor": "agent.core",
            "task_id": "task_abc123",
            "user_id": "user_xyz",
        }

        dr = self.guardian.generate_decision_record(
            decision_type="multi_tool_execution",
            query=query,
            plan=plan,
            execution_result=execution_result,
            context=context,
        )

        # Vérifier tous les champs requis
        required_fields = [
            "dr_id",
            "timestamp",
            "decision_type",
            "actor",
            "task_id",
            "query_hash",
            "plan_hash",
            "execution_hash",
            "tools_used",
            "success",
            "compliance_frameworks",
            "metadata",
        ]

        for field in required_fields:
            assert field in dr, f"Missing required field: {field}"

        # Vérifier les tools_used
        assert "tool1" in dr["tools_used"]
        assert "tool2" in dr["tools_used"]

        # Vérifier les frameworks de conformité
        assert "loi25" in dr["compliance_frameworks"]
        assert "gdpr" in dr["compliance_frameworks"]
        assert "ai_act" in dr["compliance_frameworks"]
        assert "nist_ai_rmf" in dr["compliance_frameworks"]

    def test_compliance_guardian_thread_safety(self):
        """Test: Thread safety du ComplianceGuardian"""
        import threading

        results = []
        errors = []

        def validate_query(query_id):
            try:
                result = self.guardian.validate_query(
                    f"Query {query_id}", {"user_id": f"user_{query_id}"}
                )
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Créer plusieurs threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=validate_query, args=(i,))
            threads.append(thread)
            thread.start()

        # Attendre la fin de tous les threads
        for thread in threads:
            thread.join()

        # Vérifier qu'il n'y a pas eu d'erreurs
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Vérifier que tous les résultats sont présents
        assert len(results) == 10

    def test_compliance_with_multiple_frameworks(self):
        """Test: Conformité avec plusieurs frameworks simultanément"""
        # Vérifier que tous les frameworks sont supportés
        frameworks = self.guardian.rules["legal"]["frameworks"]

        assert "loi25" in frameworks, "Loi 25 should be supported"
        assert "gdpr" in frameworks, "GDPR should be supported"
        assert "ai_act" in frameworks, "AI Act should be supported"
        assert "nist_ai_rmf" in frameworks, "NIST AI RMF should be supported"

        # Générer un DR et vérifier qu'il inclut tous les frameworks
        dr = self.guardian.generate_decision_record(
            decision_type="test",
            query="test",
            plan={"actions": []},
            execution_result={"success": True},
            context={"actor": "test", "task_id": "test"},
        )

        assert set(frameworks).issubset(set(dr["compliance_frameworks"]))


class TestComplianceEdgeCases:
    """Tests des cas limites de conformité"""

    def setup_method(self):
        """Setup avant chaque test"""
        self.guardian = ComplianceGuardian(config_path="non_existent_file.yaml")

    def test_empty_query(self):
        """Test: Requête vide"""
        query = ""
        result = self.guardian.validate_query(query, {"user_id": "user123"})

        # Une requête vide est techniquement valide
        assert result["valid"] is True

    def test_empty_plan(self):
        """Test: Plan vide"""
        plan = {"actions": []}
        result = self.guardian.validate_execution_plan(plan)

        # Un plan vide est valide
        assert result["valid"] is True

    def test_unicode_in_query(self):
        """Test: Caractères Unicode dans la requête"""
        query = "Quel est le temps à Montréal? 🌞"
        result = self.guardian.validate_query(query, {"user_id": "user123"})

        assert result["valid"] is True

    def test_special_characters_in_query(self):
        """Test: Caractères spéciaux dans la requête"""
        query = "Calculate: 2 + 2 = ?"
        result = self.guardian.validate_query(query, {"user_id": "user123"})

        assert result["valid"] is True

    def test_very_long_query_hash(self):
        """Test: Hash de requête très longue"""
        query = "a" * 5000
        result = self.guardian.validate_query(query, {"user_id": "user123"})

        # Le hash doit toujours avoir une longueur fixe (SHA-256 = 64 chars hex)
        assert len(result["metadata"]["query_hash"]) == 64
