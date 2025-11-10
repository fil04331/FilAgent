"""
Tests unitaires pour le module ComplianceGuardian
"""

import pytest
from pathlib import Path
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
        
        assert result['valid'] is True
        assert 'query_hash' in result['metadata']
        assert len(result['errors']) == 0
    
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
        
        assert result['valid'] is True  # Toujours valide, mais warning
        assert len(result['warnings']) > 0
        assert 'pii_detected' in result['metadata']
        assert result['metadata']['pii_detected'] is True
    
    def test_validate_execution_plan_success(self):
        """Test: Validation réussie d'un plan simple"""
        plan = {
            'actions': [
                {'tool': 'calculator', 'params': {}},
                {'tool': 'file_reader', 'params': {}},
            ]
        }
        
        result = self.guardian.validate_execution_plan(plan, {'task_id': 'task123'})
        
        assert result['valid'] is True
        assert 'plan_hash' in result['metadata']
        assert len(result['errors']) == 0
    
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
        
        assert result['valid'] is True
        assert len(result['warnings']) > 0
        assert result['metadata'].get('requires_approval') is True
    
    def test_audit_execution_success(self):
        """Test: Audit d'une exécution réussie"""
        execution_result = {
            'success': True,
            'result': 'Operation completed',
            'errors': []
        }
        
        audit = self.guardian.audit_execution(execution_result, {'task_id': 'task123'})
        
        assert audit['audited'] is True
        assert 'execution_hash' in audit
        assert audit['compliance_check']['passed'] is True
        assert len(audit['compliance_check']['issues']) == 0
    
    def test_audit_execution_failed(self):
        """Test: Audit d'une exécution échouée"""
        execution_result = {
            'success': False,
            'result': None,
            'errors': ['Error 1', 'Error 2']
        }
        
        audit = self.guardian.audit_execution(execution_result)
        
        assert audit['audited'] is True
        assert len(audit['compliance_check']['issues']) > 0
    
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
        
        assert 'dr_id' in dr
        assert dr['dr_id'].startswith('DR-')
        assert dr['decision_type'] == 'automated_execution'
        assert dr['actor'] == 'agent'
        assert dr['task_id'] == 'task123'
        assert 'query_hash' in dr
        assert 'plan_hash' in dr
        assert 'execution_hash' in dr
        assert dr['success'] is True
        assert 'loi25' in dr['compliance_frameworks']
        assert 'gdpr' in dr['compliance_frameworks']
    
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
