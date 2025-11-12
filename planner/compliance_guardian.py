"""
ComplianceGuardian - Module de conformité réglementaire pour FilAgent

Ce module assure la conformité avec:
- Loi 25 (Québec)
- RGPD (Europe)
- AI Act (Europe)
- NIST AI RMF (USA)

Il valide les requêtes, les plans d'exécution et génère des enregistrements de conformité.
"""

import re
import hashlib
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from pathlib import Path
import yaml


class ComplianceError(Exception):
    """Exception levée lors d'une violation de conformité"""
    pass


class ComplianceGuardian:
    """
    Gardien de conformité pour FilAgent
    
    Responsabilités:
    - Validation des requêtes utilisateur
    - Validation des plans d'exécution
    - Audit des exécutions
    - Génération de Decision Records
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialiser le ComplianceGuardian
        
        Args:
            config_path: Chemin vers le fichier compliance_rules.yaml
        """
        self.config_path = config_path or "config/compliance_rules.yaml"
        self.rules = self._load_rules()
        self.audit_log: List[Dict[str, Any]] = []
        
    def _load_rules(self) -> Dict[str, Any]:
        """Charger les règles de conformité depuis le fichier YAML"""
        config_file = Path(self.config_path)
        
        if not config_file.exists():
            # Règles par défaut si le fichier n'existe pas
            return self._get_default_rules()
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _get_default_rules(self) -> Dict[str, Any]:
        """Retourner les règles de conformité par défaut"""
        return {
            'validation': {
                'max_query_length': 10000,
                'forbidden_patterns': [
                    r'(?i)(password|secret|token|api[_-]?key)',  # Secrets
                    r'(?i)(hack|exploit|bypass|inject)',  # Mots malveillants
                ],
                'pii_patterns': [
                    r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
                    r'\b[A-Z]{2}\d{6}\b',  # Québec Health Insurance
                    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
                ],
                'required_fields': ['query', 'user_id'],
            },
            'execution': {
                'max_plan_depth': 5,
                'max_tools_per_plan': 20,
                'forbidden_tools': [],
                'require_approval_for': ['file_delete', 'system_command'],
            },
            'audit': {
                'log_all_queries': True,
                'log_all_plans': True,
                'log_all_executions': True,
                'retention_days': 365,
            },
            'legal': {
                'frameworks': ['loi25', 'gdpr', 'ai_act', 'nist_ai_rmf'],
                'data_classification': ['public', 'internal', 'confidential', 'restricted'],
            }
        }
    
    def validate_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Valider une requête utilisateur avant traitement
        
        Args:
            query: La requête utilisateur
            context: Contexte additionnel (user_id, session_id, etc.)
            
        Returns:
            Dict avec résultat de validation
            
        Raises:
            ComplianceError: Si la requête viole les règles de conformité
        """
        context = context or {}
        validation_result = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'metadata': {
                'timestamp': datetime.utcnow().isoformat(),
                'query_hash': hashlib.sha256(query.encode()).hexdigest(),
            }
        }
        
        # Vérifier la longueur
        max_length = self.rules['validation']['max_query_length']
        if len(query) > max_length:
            validation_result['valid'] = False
            validation_result['errors'].append(
                f"Query exceeds maximum length of {max_length} characters"
            )
        
        # Vérifier les patterns interdits
        forbidden_patterns = self.rules['validation']['forbidden_patterns']
        for pattern in forbidden_patterns:
            pattern_triggered = any(
                match.end() >= len(query) or query[match.end()] != "@"
                for match in re.finditer(pattern, query)
            )

            if pattern_triggered:
                validation_result['valid'] = False
                validation_result['errors'].append(
                    f"Query contains forbidden pattern: {pattern}"
                )
        
        # Détecter les PII
        pii_patterns = self.rules['validation']['pii_patterns']
        pii_found = []
        for pattern in pii_patterns:
            matches = re.findall(pattern, query)
            if matches:
                pii_found.extend(matches)
        
        if pii_found:
            validation_result['warnings'].append(
                f"Query contains potential PII: {len(pii_found)} instance(s) detected"
            )
            validation_result['metadata']['pii_detected'] = True
            validation_result['metadata']['pii_count'] = len(pii_found)
        
        # Vérifier les champs requis dans le contexte
        required_fields = self.rules['validation'].get('required_fields', [])
        missing_fields = [field for field in required_fields if field not in context]
        if missing_fields and 'query' not in missing_fields:  # query is the query itself
            validation_result['warnings'].append(
                f"Missing recommended context fields: {', '.join(missing_fields)}"
            )
        
        # Logger l'audit
        if self.rules['audit']['log_all_queries']:
            self._log_audit('query_validation', {
                'query_hash': validation_result['metadata']['query_hash'],
                'valid': validation_result['valid'],
                'warnings_count': len(validation_result['warnings']),
                'errors_count': len(validation_result['errors']),
                'context': context,
            })
        
        if not validation_result['valid']:
            raise ComplianceError(
                f"Query validation failed: {'; '.join(validation_result['errors'])}"
            )
        
        return validation_result
    
    def validate_execution_plan(self, plan: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Valider un plan d'exécution avant son exécution
        
        Args:
            plan: Le plan d'exécution (graphe de tâches HTN ou liste d'actions)
            context: Contexte additionnel
            
        Returns:
            Dict avec résultat de validation
            
        Raises:
            ComplianceError: Si le plan viole les règles de conformité
        """
        context = context or {}
        validation_result = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'metadata': {
                'timestamp': datetime.utcnow().isoformat(),
                'plan_hash': hashlib.sha256(str(plan).encode()).hexdigest(),
            }
        }
        
        # Analyser le plan
        tools_used = self._extract_tools_from_plan(plan)
        plan_depth = self._calculate_plan_depth(plan)
        
        # Vérifier la profondeur
        max_depth = self.rules['execution']['max_plan_depth']
        if plan_depth > max_depth:
            validation_result['valid'] = False
            validation_result['errors'].append(
                f"Plan depth {plan_depth} exceeds maximum of {max_depth}"
            )
        
        # Vérifier le nombre d'outils
        max_tools = self.rules['execution']['max_tools_per_plan']
        if len(tools_used) > max_tools:
            validation_result['valid'] = False
            validation_result['errors'].append(
                f"Plan uses {len(tools_used)} tools, exceeds maximum of {max_tools}"
            )
        
        # Vérifier les outils interdits
        forbidden_tools = set(self.rules['execution']['forbidden_tools'])
        used_forbidden = forbidden_tools.intersection(tools_used)
        if used_forbidden:
            validation_result['valid'] = False
            validation_result['errors'].append(
                f"Plan uses forbidden tools: {', '.join(used_forbidden)}"
            )
        
        # Vérifier les outils nécessitant approbation
        require_approval = set(self.rules['execution']['require_approval_for'])
        needs_approval = require_approval.intersection(tools_used)
        if needs_approval:
            validation_result['warnings'].append(
                f"Plan uses tools requiring approval: {', '.join(needs_approval)}"
            )
            validation_result['metadata']['requires_approval'] = True
            validation_result['metadata']['approval_tools'] = list(needs_approval)
        
        # Logger l'audit
        if self.rules['audit']['log_all_plans']:
            self._log_audit('plan_validation', {
                'plan_hash': validation_result['metadata']['plan_hash'],
                'valid': validation_result['valid'],
                'tools_count': len(tools_used),
                'plan_depth': plan_depth,
                'warnings_count': len(validation_result['warnings']),
                'errors_count': len(validation_result['errors']),
                'context': context,
            })
        
        if not validation_result['valid']:
            raise ComplianceError(
                f"Plan validation failed: {'; '.join(validation_result['errors'])}"
            )
        
        return validation_result
    
    def audit_execution(self, execution_result: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Auditer le résultat d'une exécution
        
        Args:
            execution_result: Résultat de l'exécution
            context: Contexte additionnel
            
        Returns:
            Dict avec résultat de l'audit
        """
        context = context or {}
        audit_result = {
            'audited': True,
            'timestamp': datetime.utcnow().isoformat(),
            'execution_hash': hashlib.sha256(str(execution_result).encode()).hexdigest(),
            'compliance_check': {
                'passed': True,
                'issues': [],
            }
        }
        
        # Vérifier si l'exécution a réussi
        success = execution_result.get('success', False)
        if not success:
            audit_result['compliance_check']['issues'].append(
                'Execution failed - review required'
            )
        
        # Vérifier les erreurs
        errors = execution_result.get('errors', [])
        if errors:
            audit_result['compliance_check']['issues'].append(
                f"Execution had {len(errors)} error(s)"
            )
        
        # Logger l'audit
        if self.rules['audit']['log_all_executions']:
            self._log_audit('execution_audit', {
                'execution_hash': audit_result['execution_hash'],
                'success': success,
                'errors_count': len(errors),
                'issues_count': len(audit_result['compliance_check']['issues']),
                'context': context,
            })
        
        return audit_result
    
    def generate_decision_record(
        self,
        decision_type: str,
        query: str,
        plan: Dict[str, Any],
        execution_result: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Générer un Decision Record pour traçabilité
        
        Args:
            decision_type: Type de décision (ex: 'automated_execution')
            query: Requête originale
            plan: Plan d'exécution
            execution_result: Résultat de l'exécution
            context: Contexte additionnel
            
        Returns:
            Dict représentant le Decision Record
        """
        context = context or {}
        
        dr = {
            'dr_id': self._generate_dr_id(),
            'timestamp': datetime.utcnow().isoformat(),
            'decision_type': decision_type,
            'actor': context.get('actor', 'system'),
            'task_id': context.get('task_id', ''),
            'query_hash': hashlib.sha256(query.encode()).hexdigest(),
            'plan_hash': hashlib.sha256(str(plan).encode()).hexdigest(),
            'execution_hash': hashlib.sha256(str(execution_result).encode()).hexdigest(),
            'tools_used': self._extract_tools_from_plan(plan),
            'success': execution_result.get('success', False),
            'compliance_frameworks': self.rules['legal']['frameworks'],
            'metadata': {
                'guardian_version': '1.0.0',
                'rules_version': self.rules.get('version', '1.0.0'),
            }
        }
        
        # Logger le DR
        self._log_audit('decision_record_created', {
            'dr_id': dr['dr_id'],
            'decision_type': decision_type,
            'success': dr['success'],
        })
        
        return dr
    
    def _extract_tools_from_plan(self, plan: Dict[str, Any]) -> Set[str]:
        """Extraire la liste des outils utilisés dans un plan"""
        tools = set()
        
        # Si le plan a une structure HTN avec un graphe
        if 'graph' in plan:
            graph = plan['graph']
            if hasattr(graph, 'nodes'):
                for node in graph.nodes.values():
                    if hasattr(node, 'action'):
                        tools.add(node.action)
        
        # Si le plan est une liste d'actions
        elif 'actions' in plan:
            for action in plan['actions']:
                if isinstance(action, dict) and 'tool' in action:
                    tools.add(action['tool'])
        
        # Si le plan a des tools_used directement
        elif 'tools_used' in plan:
            tools.update(plan['tools_used'])
        
        return tools
    
    def _calculate_plan_depth(self, plan: Dict[str, Any]) -> int:
        """Calculer la profondeur d'un plan"""
        # Si le plan a une structure HTN
        if 'graph' in plan:
            graph = plan['graph']
            if hasattr(graph, 'get_max_depth'):
                return graph.get_max_depth()
        
        # Si le plan est une liste d'actions
        elif 'actions' in plan:
            return len(plan['actions'])
        
        # Par défaut
        return 1
    
    def _generate_dr_id(self) -> str:
        """Générer un ID unique pour un Decision Record"""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        random_suffix = hashlib.md5(datetime.utcnow().isoformat().encode()).hexdigest()[:6]
        return f"DR-{timestamp}-{random_suffix}"
    
    def _log_audit(self, event_type: str, data: Dict[str, Any]):
        """Logger un événement d'audit"""
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'data': data,
        }
        self.audit_log.append(audit_entry)
    
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Récupérer le log d'audit"""
        return self.audit_log
    
    def clear_audit_log(self):
        """Effacer le log d'audit (pour tests)"""
        self.audit_log = []
