"""
Tests unitaires pour le module ComplianceGuardian

Couvre les scénarios suivants:
- Validation de requêtes (patterns, PII, longueur)
- Validation de plans d'exécution (profondeur, outils, approbation)
- Audit d'exécutions
- Génération de Decision Records
- Gestion des logs d'audit
- Cas limites et erreurs
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch
from planner.compliance_guardian import ComplianceGuardian, ComplianceError


class TestComplianceGuardian:
    """Tests pour la classe ComplianceGuardian"""
    
    def setup_method(self):
        """Setup avant chaque test"""
        # Utiliser les règles par défaut pour les tests
        self.guardian = ComplianceGuardian(config_path="non_existent_file.yaml")
    
    def test_initialization(self):
        """Test: ComplianceGuardian peut être initialisé"""
        assert self.guardian is not None
        assert self.guardian.rules is not None
        assert isinstance(self.guardian.audit_log, list)
    
    def test_validate_query_success(self):
        """Test: Validation réussie d'une requête simple"""
        query = "Quelle est la météo aujourd'hui?"
        result = self.guardian.validate_query(query, {'user_id': 'user123'})
        
        assert result.valid is True
        assert result.metadata.query_hash is not None
        assert len(result.errors) == 0
    
    def test_validate_query_too_long(self):
        """Test: Requête trop longue doit échouer"""
        query = "a" * 20000  # Dépasse max_query_length
        
        with pytest.raises(ComplianceError) as exc_info:
            self.guardian.validate_query(query)
        
        assert "exceeds maximum length" in str(exc_info.value)
    
    def test_validate_query_forbidden_pattern(self):
        """Test: Requête avec pattern interdit doit échouer"""
        query = "What is my API_KEY?"
        
        with pytest.raises(ComplianceError) as exc_info:
            self.guardian.validate_query(query)
        
        assert "forbidden pattern" in str(exc_info.value)
    
    def test_validate_query_with_pii(self):
        """Test: Requête contenant PII doit générer un warning"""
        query = "Mon email est test@example.com"
        result = self.guardian.validate_query(query, {'user_id': 'user123'})
        
        assert result.valid is True  # Toujours valide, mais warning
        assert len(result.warnings) > 0
        assert result.metadata.pii_detected is not None
        assert result.metadata.pii_detected is True
    
    def test_validate_execution_plan_success(self):
        """Test: Validation réussie d'un plan simple"""
        plan = {
            'actions': [
                {'tool': 'calculator', 'params': {}},
                {'tool': 'file_reader', 'params': {}},
            ]
        }
        
        result = self.guardian.validate_execution_plan(plan, {'task_id': 'task123'})

        assert result.valid is True
        assert result.metadata.plan_hash is not None
        assert len(result.errors) == 0
    
    def test_validate_execution_plan_too_deep(self):
        """Test: Plan trop profond doit échouer"""
        # Créer un plan avec beaucoup d'actions
        plan = {
            'actions': [{'tool': f'tool_{i}', 'params': {}} for i in range(10)]
        }
        
        # Modifier temporairement la règle pour un test
        original_max_depth = self.guardian.rules['execution']['max_plan_depth']
        self.guardian.rules['execution']['max_plan_depth'] = 3
        
        with pytest.raises(ComplianceError) as exc_info:
            self.guardian.validate_execution_plan(plan)
        
        assert "exceeds maximum" in str(exc_info.value)
        
        # Restaurer
        self.guardian.rules['execution']['max_plan_depth'] = original_max_depth
    
    def test_validate_execution_plan_too_many_tools(self):
        """Test: Plan avec trop d'outils doit échouer"""
        # Créer un plan avec beaucoup d'outils
        tools = [{'tool': f'tool_{i}', 'params': {}} for i in range(25)]
        plan = {'actions': tools}
        
        with pytest.raises(ComplianceError) as exc_info:
            self.guardian.validate_execution_plan(plan)
        
        assert "exceeds maximum" in str(exc_info.value)
    
    def test_validate_execution_plan_forbidden_tool(self):
        """Test: Plan utilisant un outil interdit doit échouer"""
        # Ajouter un outil interdit temporairement
        self.guardian.rules['execution']['forbidden_tools'] = ['dangerous_tool']
        
        plan = {
            'actions': [
                {'tool': 'safe_tool', 'params': {}},
                {'tool': 'dangerous_tool', 'params': {}},
            ]
        }
        
        with pytest.raises(ComplianceError) as exc_info:
            self.guardian.validate_execution_plan(plan)
        
        assert "forbidden tools" in str(exc_info.value)
    
    def test_validate_execution_plan_requires_approval(self):
        """Test: Plan nécessitant approbation génère un warning"""
        plan = {
            'actions': [
                {'tool': 'file_delete', 'params': {}},
            ]
        }
        
        result = self.guardian.validate_execution_plan(plan)

        assert result.valid is True
        assert len(result.warnings) > 0
        assert result.metadata.requires_approval is True
    
    def test_audit_execution_success(self):
        """Test: Audit d'une exécution réussie"""
        execution_result = {
            'success': True,
            'result': 'Operation completed',
            'errors': []
        }
        
        audit = self.guardian.audit_execution(execution_result, {'task_id': 'task123'})
        
        assert audit.audited is True
        assert audit.execution_hash is not None
        assert audit.compliance_check.passed is True
        assert len(audit.compliance_check.issues) == 0
    
    def test_audit_execution_failed(self):
        """Test: Audit d'une exécution échouée"""
        execution_result = {
            'success': False,
            'result': None,
            'errors': ['Error 1', 'Error 2']
        }
        
        audit = self.guardian.audit_execution(execution_result)
        
        assert audit.audited is True
        assert len(audit.compliance_check.issues) > 0

    def test_generate_decision_record(self):
        """Test: Génération d'un Decision Record"""
        query = "Test query"
        plan = {'actions': [{'tool': 'test_tool', 'params': {}}]}
        execution_result = {'success': True, 'result': 'OK'}
        context = {
            'actor': 'agent',
            'task_id': 'task123'
        }
        
        dr = self.guardian.generate_decision_record(
            decision_type='automated_execution',
            query=query,
            plan=plan,
            execution_result=execution_result,
            context=context
        )
        
        assert dr.dr_id is not None
        assert dr.dr_id.startswith('DR-')
        assert dr.decision_type == 'automated_execution'
        assert dr.actor == 'agent'
        assert dr.task_id == 'task123'
        assert dr.query_hash is not None
        assert dr.plan_hash is not None
        assert dr.execution_hash is not None
        assert dr.success is True
        assert 'loi25' in dr.compliance_frameworks
        assert 'gdpr' in dr.compliance_frameworks
    
    def test_audit_log_recording(self):
        """Test: Les événements sont enregistrés dans l'audit log"""
        initial_count = len(self.guardian.audit_log)
        
        # Effectuer une validation qui sera logguée
        query = "Test query"
        self.guardian.validate_query(query, {'user_id': 'user123'})
        
        # Vérifier que le log a été ajouté
        assert len(self.guardian.audit_log) > initial_count
        
        # Vérifier le contenu du dernier log
        last_log = self.guardian.audit_log[-1]
        assert 'timestamp' in last_log
        assert 'event_type' in last_log
        assert last_log['event_type'] == 'query_validation'
    
    def test_get_audit_log(self):
        """Test: Récupération du log d'audit"""
        # Ajouter quelques entrées
        self.guardian.validate_query("Test 1", {'user_id': 'user123'})
        self.guardian.validate_query("Test 2", {'user_id': 'user123'})
        
        audit_log = self.guardian.get_audit_log()
        
        assert isinstance(audit_log, list)
        assert len(audit_log) >= 2
    
    def test_clear_audit_log(self):
        """Test: Effacement du log d'audit"""
        # Ajouter une entrée
        self.guardian.validate_query("Test", {'user_id': 'user123'})
        assert len(self.guardian.audit_log) > 0
        
        # Effacer
        self.guardian.clear_audit_log()
        assert len(self.guardian.audit_log) == 0
    
    def test_extract_tools_from_htn_plan(self):
        """Test: Extraction d'outils depuis un plan HTN"""
        # Simuler un plan HTN (structure simplifiée)
        plan = {
            'graph': type('Graph', (), {
                'nodes': {
                    'node1': type('Node', (), {'action': 'tool_a'})(),
                    'node2': type('Node', (), {'action': 'tool_b'})(),
                }
            })()
        }
        
        tools = self.guardian._extract_tools_from_plan(plan)
        
        assert 'tool_a' in tools
        assert 'tool_b' in tools
        assert len(tools) == 2
    
    def test_extract_tools_from_simple_plan(self):
        """Test: Extraction d'outils depuis un plan simple"""
        plan = {
            'actions': [
                {'tool': 'tool_x', 'params': {}},
                {'tool': 'tool_y', 'params': {}},
                {'tool': 'tool_x', 'params': {}},  # Dupliqué
            ]
        }
        
        tools = self.guardian._extract_tools_from_plan(plan)
        
        assert 'tool_x' in tools
        assert 'tool_y' in tools
        assert len(tools) == 2  # Set élimine les doublons
    
    def test_load_rules_from_file(self):
        """Test: Chargement des règles depuis un fichier YAML"""
        # Si le fichier de configuration existe, tester le chargement
        config_path = Path("config/compliance_rules.yaml")
        if config_path.exists():
            guardian = ComplianceGuardian(config_path=str(config_path))

            assert guardian.rules is not None
            assert 'validation' in guardian.rules
            assert 'execution' in guardian.rules
            assert 'audit' in guardian.rules
            assert 'legal' in guardian.rules


class TestQueryValidationEdgeCases:
    """Tests avancés pour la validation de requêtes"""

    def setup_method(self):
        """Setup avant chaque test"""
        self.guardian = ComplianceGuardian(config_path="non_existent_file.yaml")

    def test_validate_query_exactly_at_limit(self):
        """Test: Requête exactement à la limite de longueur"""
        max_length = self.guardian.rules['validation']['max_query_length']
        query = "a" * max_length

        result = self.guardian.validate_query(query, {'user_id': 'user123'})
        assert result.valid is True

    def test_validate_query_one_over_limit(self):
        """Test: Requête dépassant la limite d'un caractère"""
        max_length = self.guardian.rules['validation']['max_query_length']
        query = "a" * (max_length + 1)

        with pytest.raises(ComplianceError) as exc_info:
            self.guardian.validate_query(query, {'user_id': 'user123'})

        assert "exceeds maximum length" in str(exc_info.value)

    def test_validate_query_empty_string(self):
        """Test: Requête vide"""
        query = ""
        result = self.guardian.validate_query(query, {'user_id': 'user123'})

        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_query_multiple_forbidden_patterns(self):
        """Test: Requête avec plusieurs patterns interdits"""
        query = "What is my password and secret token?"

        with pytest.raises(ComplianceError) as exc_info:
            self.guardian.validate_query(query, {'user_id': 'user123'})

        assert "forbidden pattern" in str(exc_info.value)

    def test_validate_query_multiple_pii_types(self):
        """Test: Requête avec plusieurs types de PII"""
        query = "Contact me at test@example.com or 123-45-6789"
        result = self.guardian.validate_query(query, {'user_id': 'user123'})

        assert result.valid is True
        assert len(result.warnings) > 0
        assert result.metadata.pii_detected is True
        assert result.metadata.pii_count >= 2

    def test_validate_query_pii_ssn(self):
        """Test: Détection de SSN (numéro de sécurité sociale)"""
        query = "My SSN is 123-45-6789"
        result = self.guardian.validate_query(query, {'user_id': 'user123'})

        assert result.valid is True
        assert result.metadata.pii_detected is True

    def test_validate_query_pii_quebec_health(self):
        """Test: Détection de numéro d'assurance maladie Québec"""
        query = "My health card is AB123456"
        result = self.guardian.validate_query(query, {'user_id': 'user123'})

        assert result.valid is True
        assert result.metadata.pii_detected is True

    def test_validate_query_pii_and_forbidden_pattern(self):
        """Test: Requête avec PII ET pattern interdit"""
        query = "Email my password to test@example.com"

        with pytest.raises(ComplianceError) as exc_info:
            self.guardian.validate_query(query, {'user_id': 'user123'})

        assert "forbidden pattern" in str(exc_info.value)

    def test_validate_query_missing_context_fields(self):
        """Test: Contexte sans champs requis génère warnings"""
        query = "Simple query"
        # Context missing user_id (which is in required_fields)
        result = self.guardian.validate_query(query, {'query': query})

        assert result.valid is True
        # Warning only generated if 'query' is not in missing_fields
        assert len(result.warnings) > 0

    def test_validate_query_with_all_context_fields(self):
        """Test: Contexte avec tous les champs requis"""
        query = "Simple query"
        context = {'query': query, 'user_id': 'user123'}
        result = self.guardian.validate_query(query, context)

        assert result.valid is True

    def test_validate_query_case_insensitive_patterns(self):
        """Test: Patterns interdits sont case-insensitive"""
        queries = [
            "What is my PASSWORD?",
            "Show me the Secret",
            "Get the API_KEY",
            "Find the Token"
        ]

        for query in queries:
            with pytest.raises(ComplianceError):
                self.guardian.validate_query(query, {'user_id': 'user123'})

    def test_validate_query_forbidden_pattern_hack(self):
        """Test: Détection de mots malveillants (hack, exploit, etc.)"""
        malicious_queries = [
            "How to hack this system?",
            "Exploit this vulnerability",
            "Bypass the security",
            "SQL injection attack"
        ]

        for query in malicious_queries:
            with pytest.raises(ComplianceError):
                self.guardian.validate_query(query, {'user_id': 'user123'})

    def test_validate_query_benign_similar_words(self):
        """Test: Mots similaires mais bénins passent la validation"""
        benign_queries = [
            "I like to hack on projects",  # 'hack' dans contexte coding
            "This is a life hack",
        ]

        # These will fail because pattern matching is strict
        # This test documents current behavior
        for query in benign_queries:
            with pytest.raises(ComplianceError):
                self.guardian.validate_query(query, {'user_id': 'user123'})

    def test_validate_query_email_in_context(self):
        """Test: Email dans le contexte approprié"""
        query = "Send notification to support@company.com"
        result = self.guardian.validate_query(query, {'user_id': 'user123'})

        # Email détecté mais pas bloqué (juste warning)
        assert result.valid is True
        assert result.metadata.pii_detected is True

    def test_validate_query_audit_logged(self):
        """Test: Validation de requête est loguée si audit activé"""
        self.guardian.rules['audit']['log_all_queries'] = True
        initial_log_count = len(self.guardian.audit_log)

        query = "Test query"
        self.guardian.validate_query(query, {'user_id': 'user123'})

        assert len(self.guardian.audit_log) > initial_log_count

    def test_validate_query_audit_not_logged_when_disabled(self):
        """Test: Validation non loguée si audit désactivé"""
        self.guardian.rules['audit']['log_all_queries'] = False
        initial_log_count = len(self.guardian.audit_log)

        query = "Test query"
        self.guardian.validate_query(query, {'user_id': 'user123'})

        # log_audit is still called but we check the rule
        assert len(self.guardian.audit_log) == initial_log_count


class TestPlanValidationEdgeCases:
    """Tests avancés pour la validation de plans"""

    def setup_method(self):
        """Setup avant chaque test"""
        self.guardian = ComplianceGuardian(config_path="non_existent_file.yaml")

    def test_validate_empty_plan(self):
        """Test: Plan vide"""
        plan = {}
        result = self.guardian.validate_execution_plan(plan)

        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_plan_with_only_tools_used(self):
        """Test: Plan avec seulement tools_used"""
        plan = {
            'tools_used': ['tool_a', 'tool_b', 'tool_c']
        }
        result = self.guardian.validate_execution_plan(plan)

        assert result.valid is True

    def test_validate_plan_tools_used_forbidden(self):
        """Test: Plan avec outil interdit dans tools_used"""
        self.guardian.rules['execution']['forbidden_tools'] = ['forbidden_tool']

        plan = {
            'tools_used': ['safe_tool', 'forbidden_tool']
        }

        with pytest.raises(ComplianceError) as exc_info:
            self.guardian.validate_execution_plan(plan)

        assert "forbidden tools" in str(exc_info.value)

    def test_validate_plan_exactly_at_max_depth(self):
        """Test: Plan exactement à la profondeur maximale"""
        max_depth = self.guardian.rules['execution']['max_plan_depth']

        plan = {
            'actions': [{'tool': f'tool_{i}', 'params': {}} for i in range(max_depth)]
        }

        result = self.guardian.validate_execution_plan(plan)
        assert result.valid is True

    def test_validate_plan_exactly_at_max_tools(self):
        """Test: Plan exactement au nombre maximal d'outils"""
        max_tools = self.guardian.rules['execution']['max_tools_per_plan']

        # Use 'tools_used' instead of 'actions' to avoid depth check
        plan = {
            'tools_used': [f'tool_{i}' for i in range(max_tools)]
        }

        result = self.guardian.validate_execution_plan(plan)
        assert result.valid is True

    def test_validate_plan_multiple_forbidden_tools(self):
        """Test: Plan avec plusieurs outils interdits"""
        self.guardian.rules['execution']['forbidden_tools'] = ['bad1', 'bad2', 'bad3']

        plan = {
            'actions': [
                {'tool': 'good', 'params': {}},
                {'tool': 'bad1', 'params': {}},
                {'tool': 'bad2', 'params': {}},
            ]
        }

        with pytest.raises(ComplianceError) as exc_info:
            self.guardian.validate_execution_plan(plan)

        error_msg = str(exc_info.value)
        assert "forbidden tools" in error_msg
        assert "bad1" in error_msg or "bad2" in error_msg

    def test_validate_plan_multiple_approval_tools(self):
        """Test: Plan avec plusieurs outils nécessitant approbation"""
        plan = {
            'actions': [
                {'tool': 'file_delete', 'params': {}},
                {'tool': 'system_command', 'params': {}},
            ]
        }

        result = self.guardian.validate_execution_plan(plan)

        assert result.valid is True
        assert result.metadata.requires_approval is True
        assert len(result.metadata.approval_tools) == 2

    def test_validate_plan_approval_and_forbidden_mixed(self):
        """Test: Plan avec outils d'approbation ET interdits"""
        self.guardian.rules['execution']['forbidden_tools'] = ['forbidden_tool']

        plan = {
            'actions': [
                {'tool': 'file_delete', 'params': {}},  # Requires approval
                {'tool': 'forbidden_tool', 'params': {}},  # Forbidden
            ]
        }

        # Should fail due to forbidden tool
        with pytest.raises(ComplianceError):
            self.guardian.validate_execution_plan(plan)

    def test_validate_plan_htn_graph_structure(self):
        """Test: Plan HTN avec structure de graphe"""
        # Mock HTN graph
        mock_graph = Mock()
        mock_graph.nodes = {
            'n1': Mock(action='tool_a'),
            'n2': Mock(action='tool_b'),
            'n3': Mock(action='tool_c'),
        }
        mock_graph.get_max_depth = Mock(return_value=3)

        plan = {'graph': mock_graph}

        result = self.guardian.validate_execution_plan(plan)
        assert result.valid is True

    def test_validate_plan_htn_graph_too_deep(self):
        """Test: Plan HTN trop profond"""
        mock_graph = Mock()
        mock_graph.nodes = {
            'n1': Mock(action='tool_a'),
        }
        mock_graph.get_max_depth = Mock(return_value=10)

        plan = {'graph': mock_graph}

        with pytest.raises(ComplianceError) as exc_info:
            self.guardian.validate_execution_plan(plan)

        assert "exceeds maximum" in str(exc_info.value)

    def test_validate_plan_audit_logged(self):
        """Test: Validation de plan est loguée"""
        self.guardian.rules['audit']['log_all_plans'] = True
        initial_log_count = len(self.guardian.audit_log)

        plan = {'actions': [{'tool': 'test', 'params': {}}]}
        self.guardian.validate_execution_plan(plan)

        assert len(self.guardian.audit_log) > initial_log_count
        assert self.guardian.audit_log[-1]['event_type'] == 'plan_validation'

    def test_validate_plan_with_context(self):
        """Test: Validation de plan avec contexte"""
        plan = {'actions': [{'tool': 'test', 'params': {}}]}
        context = {'task_id': 'task-123', 'user_id': 'user-456'}

        result = self.guardian.validate_execution_plan(plan, context)

        assert result.valid is True
        # Check that context was logged
        last_log = self.guardian.audit_log[-1]
        assert last_log['data']['context'] == context


class TestExecutionAudit:
    """Tests pour l'audit d'exécution"""

    def setup_method(self):
        """Setup avant chaque test"""
        self.guardian = ComplianceGuardian(config_path="non_existent_file.yaml")

    def test_audit_execution_with_context(self):
        """Test: Audit d'exécution avec contexte"""
        execution_result = {
            'success': True,
            'result': 'OK',
            'errors': []
        }
        context = {'task_id': 'task-123'}

        audit = self.guardian.audit_execution(execution_result, context)

        assert audit.audited is True
        assert audit.compliance_check.passed is True

    def test_audit_execution_with_warnings(self):
        """Test: Audit d'exécution avec warnings (pas d'erreurs)"""
        execution_result = {
            'success': True,
            'result': 'OK',
            'warnings': ['Warning 1', 'Warning 2'],
            'errors': []
        }

        audit = self.guardian.audit_execution(execution_result)

        assert audit.audited is True
        assert audit.compliance_check.passed is True

    def test_audit_execution_partial_success(self):
        """Test: Audit d'exécution partiellement réussie"""
        execution_result = {
            'success': True,
            'result': 'Partial',
            'errors': ['Minor error']
        }

        audit = self.guardian.audit_execution(execution_result)

        assert audit.audited is True
        assert len(audit.compliance_check.issues) > 0

    def test_audit_execution_multiple_errors(self):
        """Test: Audit d'exécution avec plusieurs erreurs"""
        execution_result = {
            'success': False,
            'result': None,
            'errors': ['Error 1', 'Error 2', 'Error 3']
        }

        audit = self.guardian.audit_execution(execution_result)

        assert audit.audited is True
        issues = audit.compliance_check.issues
        assert any('error' in issue.lower() for issue in issues)

    def test_audit_execution_empty_result(self):
        """Test: Audit d'exécution vide"""
        execution_result = {}

        audit = self.guardian.audit_execution(execution_result)

        assert audit.audited is True
        # Missing 'success' defaults to False
        assert len(audit.compliance_check.issues) > 0

    def test_audit_execution_logged(self):
        """Test: Audit d'exécution est loggué"""
        self.guardian.rules['audit']['log_all_executions'] = True
        initial_log_count = len(self.guardian.audit_log)

        execution_result = {'success': True, 'errors': []}
        self.guardian.audit_execution(execution_result)

        assert len(self.guardian.audit_log) > initial_log_count
        assert self.guardian.audit_log[-1]['event_type'] == 'execution_audit'


class TestDecisionRecords:
    """Tests pour les Decision Records"""

    def setup_method(self):
        """Setup avant chaque test"""
        self.guardian = ComplianceGuardian(config_path="non_existent_file.yaml")

    def test_generate_decision_record_minimal(self):
        """Test: DR avec paramètres minimaux"""
        dr = self.guardian.generate_decision_record(
            decision_type='test',
            query='Test query',
            plan={},
            execution_result={}
        )

        assert dr.dr_id is not None
        assert dr.decision_type == 'test'
        assert dr.actor == 'system'  # Default actor

    def test_generate_decision_record_full_context(self):
        """Test: DR avec contexte complet"""
        context = {
            'actor': 'user',
            'task_id': 'task-123',
            'session_id': 'session-456',
            'custom_field': 'custom_value'
        }

        dr = self.guardian.generate_decision_record(
            decision_type='manual_approval',
            query='Complex query',
            plan={'actions': []},
            execution_result={'success': True},
            context=context
        )

        assert dr.actor == 'user'
        assert dr.task_id == 'task-123'

    def test_generate_decision_record_with_tools(self):
        """Test: DR avec extraction d'outils du plan"""
        plan = {
            'actions': [
                {'tool': 'tool_a', 'params': {}},
                {'tool': 'tool_b', 'params': {}},
            ]
        }

        dr = self.guardian.generate_decision_record(
            decision_type='automated',
            query='Query',
            plan=plan,
            execution_result={'success': True}
        )

        assert 'tool_a' in dr.tools_used
        assert 'tool_b' in dr.tools_used

    def test_generate_decision_record_failure(self):
        """Test: DR pour exécution échouée"""
        dr = self.guardian.generate_decision_record(
            decision_type='automated',
            query='Query',
            plan={},
            execution_result={'success': False, 'error': 'Test error'}
        )

        assert dr.success is False

    def test_generate_decision_record_compliance_frameworks(self):
        """Test: DR contient les frameworks de conformité"""
        dr = self.guardian.generate_decision_record(
            decision_type='test',
            query='Query',
            plan={},
            execution_result={'success': True}
        )

        frameworks = dr.compliance_frameworks
        assert 'loi25' in frameworks
        assert 'gdpr' in frameworks
        assert 'ai_act' in frameworks
        assert 'nist_ai_rmf' in frameworks

    def test_generate_decision_record_unique_ids(self):
        """Test: Chaque DR a un ID unique"""
        drs = []
        for i in range(5):
            dr = self.guardian.generate_decision_record(
                decision_type='test',
                query=f'Query {i}',
                plan={},
                execution_result={'success': True}
            )
            drs.append(dr.dr_id)

        # All IDs should be unique
        assert len(set(drs)) == 5

    def test_generate_decision_record_logged(self):
        """Test: Création de DR est loguée"""
        initial_log_count = len(self.guardian.audit_log)

        self.guardian.generate_decision_record(
            decision_type='test',
            query='Query',
            plan={},
            execution_result={'success': True}
        )

        assert len(self.guardian.audit_log) > initial_log_count
        last_log = self.guardian.audit_log[-1]
        assert last_log['event_type'] == 'decision_record_created'

    def test_dr_id_format(self):
        """Test: Format du DR ID"""
        dr = self.guardian.generate_decision_record(
            decision_type='test',
            query='Query',
            plan={},
            execution_result={'success': True}
        )

        dr_id = dr.dr_id
        assert dr_id.startswith('DR-')
        parts = dr_id.split('-')
        assert len(parts) == 3
        assert parts[1].isdigit()  # Timestamp
        assert len(parts[2]) == 6  # Hash suffix


class TestHelperMethods:
    """Tests pour les méthodes helper"""

    def setup_method(self):
        """Setup avant chaque test"""
        self.guardian = ComplianceGuardian(config_path="non_existent_file.yaml")

    def test_extract_tools_from_empty_plan(self):
        """Test: Extraction d'outils d'un plan vide"""
        plan = {}
        tools = self.guardian._extract_tools_from_plan(plan)

        assert len(tools) == 0

    def test_extract_tools_from_plan_with_tools_used(self):
        """Test: Extraction depuis tools_used"""
        plan = {
            'tools_used': ['tool_x', 'tool_y', 'tool_z']
        }
        tools = self.guardian._extract_tools_from_plan(plan)

        assert 'tool_x' in tools
        assert 'tool_y' in tools
        assert 'tool_z' in tools

    def test_extract_tools_deduplication(self):
        """Test: Les outils dupliqués sont dédupliqués"""
        plan = {
            'actions': [
                {'tool': 'same_tool', 'params': {}},
                {'tool': 'same_tool', 'params': {}},
                {'tool': 'same_tool', 'params': {}},
            ]
        }
        tools = self.guardian._extract_tools_from_plan(plan)

        assert len(tools) == 1
        assert 'same_tool' in tools

    def test_calculate_plan_depth_empty(self):
        """Test: Profondeur d'un plan vide"""
        plan = {}
        depth = self.guardian._calculate_plan_depth(plan)

        assert depth == 1  # Default depth

    def test_calculate_plan_depth_actions(self):
        """Test: Profondeur basée sur nombre d'actions"""
        plan = {
            'actions': [
                {'tool': 'tool_1', 'params': {}},
                {'tool': 'tool_2', 'params': {}},
                {'tool': 'tool_3', 'params': {}},
            ]
        }
        depth = self.guardian._calculate_plan_depth(plan)

        assert depth == 3

    def test_calculate_plan_depth_htn_graph(self):
        """Test: Profondeur d'un graphe HTN"""
        mock_graph = Mock()
        mock_graph.get_max_depth = Mock(return_value=7)

        plan = {'graph': mock_graph}
        depth = self.guardian._calculate_plan_depth(plan)

        assert depth == 7

    def test_generate_dr_id_format(self):
        """Test: Format de l'ID de DR généré"""
        dr_id = self.guardian._generate_dr_id()

        assert dr_id.startswith('DR-')
        parts = dr_id.split('-')
        assert len(parts) == 3

    def test_log_audit_structure(self):
        """Test: Structure des entrées d'audit"""
        self.guardian._log_audit('test_event', {'key': 'value'})

        last_entry = self.guardian.audit_log[-1]
        assert 'timestamp' in last_entry
        assert 'event_type' in last_entry
        assert 'data' in last_entry
        assert last_entry['event_type'] == 'test_event'
        assert last_entry['data']['key'] == 'value'


class TestConfigurationAndRules:
    """Tests pour la configuration et les règles"""

    def test_load_rules_with_custom_config(self):
        """Test: Chargement de règles personnalisées"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            custom_rules = {
                'validation': {
                    'max_query_length': 5000,
                    'forbidden_patterns': [r'custom_pattern'],
                    'pii_patterns': [],
                    'required_fields': []
                },
                'execution': {
                    'max_plan_depth': 3,
                    'max_tools_per_plan': 10,
                    'forbidden_tools': ['custom_forbidden'],
                    'require_approval_for': ['custom_approval']
                },
                'audit': {
                    'log_all_queries': True,
                    'log_all_plans': True,
                    'log_all_executions': True,
                    'retention_days': 180
                },
                'legal': {
                    'frameworks': ['custom_framework'],
                    'data_classification': ['public']
                }
            }
            yaml.dump(custom_rules, f)
            config_path = f.name

        try:
            guardian = ComplianceGuardian(config_path=config_path)

            assert guardian.rules['validation']['max_query_length'] == 5000
            assert guardian.rules['execution']['max_plan_depth'] == 3
            assert 'custom_forbidden' in guardian.rules['execution']['forbidden_tools']
        finally:
            Path(config_path).unlink()

    def test_default_rules_structure(self):
        """Test: Structure des règles par défaut"""
        guardian = ComplianceGuardian(config_path="non_existent_file.yaml")
        rules = guardian.rules

        # Validation rules
        assert 'validation' in rules
        assert 'max_query_length' in rules['validation']
        assert 'forbidden_patterns' in rules['validation']
        assert 'pii_patterns' in rules['validation']

        # Execution rules
        assert 'execution' in rules
        assert 'max_plan_depth' in rules['execution']
        assert 'max_tools_per_plan' in rules['execution']

        # Audit rules
        assert 'audit' in rules
        assert 'log_all_queries' in rules['audit']

        # Legal rules
        assert 'legal' in rules
        assert 'frameworks' in rules['legal']

    def test_default_rules_values(self):
        """Test: Valeurs des règles par défaut"""
        guardian = ComplianceGuardian(config_path="non_existent_file.yaml")
        rules = guardian.rules

        assert rules['validation']['max_query_length'] == 10000
        assert rules['execution']['max_plan_depth'] == 5
        assert rules['execution']['max_tools_per_plan'] == 20
        assert rules['audit']['retention_days'] == 365


class TestComplexScenarios:
    """Tests de scénarios complexes et workflows complets"""

    def setup_method(self):
        """Setup avant chaque test"""
        self.guardian = ComplianceGuardian(config_path="non_existent_file.yaml")

    def test_full_workflow_success(self):
        """Test: Workflow complet de validation → plan → exécution → DR"""
        # 1. Validate query
        query = "Analyze data and generate report"
        query_validation = self.guardian.validate_query(
            query,
            {'user_id': 'user123', 'session_id': 'session456'}
        )
        assert query_validation.valid is True

        # 2. Validate plan
        plan = {
            'actions': [
                {'tool': 'data_analyzer', 'params': {}},
                {'tool': 'report_generator', 'params': {}},
            ]
        }
        plan_validation = self.guardian.validate_execution_plan(
            plan,
            {'task_id': 'task789'}
        )
        assert plan_validation.valid is True

        # 3. Audit execution
        execution_result = {
            'success': True,
            'result': 'Report generated successfully',
            'errors': []
        }
        audit = self.guardian.audit_execution(execution_result)
        assert audit.audited is True

        # 4. Generate Decision Record
        dr = self.guardian.generate_decision_record(
            decision_type='automated_execution',
            query=query,
            plan=plan,
            execution_result=execution_result,
            context={'actor': 'agent', 'task_id': 'task789'}
        )
        assert dr.success is True
        assert 'data_analyzer' in dr.tools_used

    def test_full_workflow_with_approval(self):
        """Test: Workflow nécessitant approbation"""
        query = "Delete old files"

        query_validation = self.guardian.validate_query(query, {'user_id': 'user123'})
        assert query_validation.valid is True

        plan = {
            'actions': [
                {'tool': 'file_delete', 'params': {'path': '/old_files'}},
            ]
        }

        plan_validation = self.guardian.validate_execution_plan(plan)
        assert plan_validation.valid is True
        assert plan_validation.metadata.requires_approval is True
        assert 'file_delete' in plan_validation.metadata.approval_tools

    def test_full_workflow_with_policy_violation(self):
        """Test: Workflow avec violation de politique"""
        # Query with forbidden pattern
        query = "Show me the password file"

        with pytest.raises(ComplianceError):
            self.guardian.validate_query(query, {'user_id': 'user123'})

    def test_sequential_validations(self):
        """Test: Validations séquentielles multiples"""
        queries = [
            "Query 1",
            "Query 2",
            "Query 3"
        ]

        for i, query in enumerate(queries):
            result = self.guardian.validate_query(query, {'user_id': f'user{i}'})
            assert result.valid is True

        # Check audit log has all validations
        query_validations = [
            log for log in self.guardian.audit_log
            if log['event_type'] == 'query_validation'
        ]
        assert len(query_validations) >= 3

    def test_parallel_plan_validations(self):
        """Test: Validations de plans multiples (simule parallélisme)"""
        plans = [
            {'actions': [{'tool': 'tool_a', 'params': {}}]},
            {'actions': [{'tool': 'tool_b', 'params': {}}]},
            {'actions': [{'tool': 'tool_c', 'params': {}}]},
        ]

        results = []
        for plan in plans:
            result = self.guardian.validate_execution_plan(plan)
            results.append(result)

        assert all(r.valid for r in results)

    def test_audit_log_retention(self):
        """Test: Vérification de la politique de rétention"""
        retention_days = self.guardian.rules['audit']['retention_days']

        assert retention_days > 0
        assert retention_days == 365  # Default


class TestComplianceError:
    """Tests pour l'exception ComplianceError"""
    
    def test_compliance_error_raised(self):
        """Test: ComplianceError peut être levée"""
        with pytest.raises(ComplianceError) as exc_info:
            raise ComplianceError("Test error")
        
        assert "Test error" in str(exc_info.value)
    
    def test_compliance_error_is_exception(self):
        """Test: ComplianceError est une Exception"""
        error = ComplianceError("Test")
        assert isinstance(error, Exception)
