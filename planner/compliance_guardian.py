"""
ComplianceGuardian - Module de conformite reglementaire pour FilAgent

Ce module assure la conformite avec:
- Loi 25 (Quebec)
- RGPD (Europe)
- AI Act (Europe)
- NIST AI RMF (USA)

Il valide les requetes, les plans d'execution et genere des enregistrements de conformite.
"""

from __future__ import annotations

import re
import hashlib
import time
from typing import Dict, List, Optional, Set, Union
from datetime import datetime
from pathlib import Path
from enum import Enum
import yaml

# Import metrics for observability
try:
    from runtime.metrics import get_agent_metrics

    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False

from pydantic import BaseModel, Field

__all__ = [
    "RiskLevel",
    "ValidationResult",
    "QueryValidationResult",
    "PlanValidationResult",
    "ExecutionAuditResult",
    "DecisionRecord",
    "ComplianceError",
    "ComplianceGuardian",
]


# =============================================================================
# Pydantic V2 Models for Strict Typing
# =============================================================================


class RiskLevel(str, Enum):
    """Niveaux de risque de conformite"""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ValidationMetadata(BaseModel):
    """Metadonnees de validation pour audit trail"""

    timestamp: str = Field(description="ISO timestamp de la validation")
    query_hash: Optional[str] = Field(default=None, description="SHA256 hash de la requete")
    plan_hash: Optional[str] = Field(default=None, description="SHA256 hash du plan")
    pii_detected: bool = Field(default=False, description="PII detecte dans la requete")
    pii_count: int = Field(default=0, ge=0, description="Nombre d'instances PII detectees")
    requires_approval: bool = Field(default=False, description="Approbation requise")
    approval_tools: List[str] = Field(
        default_factory=list, description="Outils necessitant approbation"
    )
    task_action: Optional[str] = Field(default=None, description="Action de la tache")
    context: Dict[str, Union[str, int, bool]] = Field(
        default_factory=dict, description="Contexte additionnel"
    )


class ValidationResult(BaseModel):
    """
    Resultat de validation de conformite pour une tache ou action (Pydantic V2)

    Utilise pour auditer les decisions de conformite selon Loi 25/PIPEDA.
    Tous les champs sont loggables pour tracabilite reglementaire.
    """

    is_compliant: bool = Field(description="True si la tache/action est conforme aux regles")
    violations: List[str] = Field(
        default_factory=list, description="Liste des violations detectees"
    )
    risk_level: RiskLevel = Field(default=RiskLevel.LOW, description="Niveau de risque")
    warnings: List[str] = Field(default_factory=list, description="Avertissements non-bloquants")
    metadata: Optional[ValidationMetadata] = Field(
        default=None, description="Metadonnees pour audit"
    )

    class Config:
        use_enum_values = True


class QueryValidationResult(BaseModel):
    """Resultat de validation d'une requete utilisateur (Pydantic V2)"""

    valid: bool = Field(description="True si la requete est valide")
    warnings: List[str] = Field(default_factory=list, description="Avertissements")
    errors: List[str] = Field(default_factory=list, description="Erreurs de validation")
    metadata: ValidationMetadata = Field(description="Metadonnees de validation")

    def to_dict(self) -> Dict[str, object]:
        """Conversion en dict pour compatibilite"""
        return self.model_dump()


class PlanValidationResult(BaseModel):
    """Resultat de validation d'un plan d'execution (Pydantic V2)"""

    valid: bool = Field(description="True si le plan est valide")
    warnings: List[str] = Field(default_factory=list, description="Avertissements")
    errors: List[str] = Field(default_factory=list, description="Erreurs de validation")
    metadata: ValidationMetadata = Field(description="Metadonnees de validation")

    def to_dict(self) -> Dict[str, object]:
        """Conversion en dict pour compatibilite"""
        return self.model_dump()


class ComplianceCheckResult(BaseModel):
    """Resultat de verification de conformite"""

    passed: bool = Field(default=True, description="True si la verification est passee")
    issues: List[str] = Field(default_factory=list, description="Problemes detectes")


class ExecutionAuditResult(BaseModel):
    """Resultat d'audit d'execution (Pydantic V2)"""

    audited: bool = Field(default=True, description="True si l'audit a ete effectue")
    timestamp: str = Field(description="ISO timestamp de l'audit")
    execution_hash: str = Field(description="SHA256 hash du resultat d'execution")
    compliance_check: ComplianceCheckResult = Field(
        description="Resultat de verification de conformite"
    )

    def to_dict(self) -> Dict[str, object]:
        """Conversion en dict pour compatibilite"""
        return self.model_dump()


class DecisionRecordMetadata(BaseModel):
    """Metadonnees d'un Decision Record"""

    guardian_version: str = Field(default="1.0.0", description="Version du guardian")
    rules_version: str = Field(default="1.0.0", description="Version des regles")


class DecisionRecord(BaseModel):
    """Decision Record pour tracabilite Loi 25/PIPEDA (Pydantic V2)"""

    dr_id: str = Field(description="ID unique du Decision Record")
    timestamp: str = Field(description="ISO timestamp de creation")
    decision_type: str = Field(description="Type de decision")
    actor: str = Field(default="system", description="Acteur ayant pris la decision")
    task_id: str = Field(default="", description="ID de la tache associee")
    query_hash: str = Field(description="SHA256 hash de la requete")
    plan_hash: str = Field(description="SHA256 hash du plan")
    execution_hash: str = Field(description="SHA256 hash de l'execution")
    tools_used: Set[str] = Field(default_factory=set, description="Outils utilises")
    success: bool = Field(description="True si l'execution a reussi")
    compliance_frameworks: List[str] = Field(
        default_factory=list, description="Frameworks de conformite"
    )
    metadata: DecisionRecordMetadata = Field(
        default_factory=DecisionRecordMetadata, description="Metadonnees"
    )

    class Config:
        arbitrary_types_allowed = True

    def to_dict(self) -> Dict[str, object]:
        """Conversion en dict pour compatibilite"""
        data = self.model_dump()
        data["tools_used"] = list(self.tools_used)  # Convert set to list for JSON
        return data


# =============================================================================
# Type Aliases (for internal use and backward compatibility)
# =============================================================================

RulesDict = Dict[str, Dict[str, Union[int, bool, List[str]]]]
# AuditEntryDict uses object for flexible nested data from various sources
AuditEntryDict = Dict[str, Union[str, object]]
ContextDict = Dict[str, Union[str, int, bool, List[str]]]
PlanDict = Dict[str, Union[str, List[Dict[str, str]], Set[str], object]]
ExecutionResultDict = Dict[str, Union[bool, List[str], Dict[str, str]]]
TaskDict = Dict[str, Union[str, Dict[str, str]]]


class ComplianceError(Exception):
    """Exception levee lors d'une violation de conformite"""



class ComplianceGuardian:
    """
    Gardien de conformite pour FilAgent

    Responsabilites:
    - Validation des requetes utilisateur
    - Validation des plans d'execution
    - Audit des executions
    - Generation de Decision Records
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        """
        Initialiser le ComplianceGuardian

        Args:
            config_path: Chemin vers le fichier compliance_rules.yaml
        """
        self.config_path = config_path or "config/compliance_rules.yaml"
        self.rules = self._load_rules()
        self.audit_log: List[AuditEntryDict] = []

        # Initialize metrics collector
        if METRICS_AVAILABLE:
            self.metrics = get_agent_metrics()
        else:
            self.metrics = None

    def _load_rules(self) -> RulesDict:
        """Charger les regles de conformite depuis le fichier YAML"""
        config_file = Path(self.config_path)

        if not config_file.exists():
            # Regles par defaut si le fichier n'existe pas
            return self._get_default_rules()

        with open(config_file, "r", encoding="utf-8") as f:
            loaded_rules = yaml.safe_load(f)
            if loaded_rules is None:
                return self._get_default_rules()
            # yaml.safe_load returns Any; we validate structure at runtime
            if isinstance(loaded_rules, dict):
                return loaded_rules
            return self._get_default_rules()

    def _get_default_rules(self) -> RulesDict:
        """Retourner les regles de conformite par defaut"""
        return {
            "validation": {
                "max_query_length": 10000,
                "forbidden_patterns": [
                    r"(?i)(password|secret|token|api[_-]?key)",  # Secrets
                    r"(?i)(hack|exploit|bypass|inject)",  # Mots malveillants
                ],
                "pii_patterns": [
                    r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
                    r"\b[A-Z]{2}\d{6}\b",  # Quebec Health Insurance
                    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
                ],
                "required_fields": ["query", "user_id"],
            },
            "execution": {
                "max_plan_depth": 5,
                "max_tools_per_plan": 20,
                "forbidden_tools": [],
                "require_approval_for": ["file_delete", "system_command"],
            },
            "audit": {
                "log_all_queries": True,
                "log_all_plans": True,
                "log_all_executions": True,
                "retention_days": 365,
            },
            "legal": {
                "frameworks": ["loi25", "gdpr", "ai_act", "nist_ai_rmf"],
                "data_classification": ["public", "internal", "confidential", "restricted"],
            },
        }

    def validate_query(
        self, query: str, context: Optional[ContextDict] = None
    ) -> QueryValidationResult:
        """
        Valider une requete utilisateur avant traitement

        Args:
            query: La requete utilisateur
            context: Contexte additionnel (user_id, session_id, etc.)

        Returns:
            QueryValidationResult avec resultat de validation

        Raises:
            ComplianceError: Si la requete viole les regles de conformite
        """
        start_time = time.time()
        context = context or {}

        # Initialize typed lists
        warnings_list: List[str] = []
        errors_list: List[str] = []
        is_valid = True

        # Initialize metadata
        metadata = ValidationMetadata(
            timestamp=datetime.utcnow().isoformat(),
            query_hash=hashlib.sha256(query.encode()).hexdigest(),
        )

        # Verifier la longueur
        validation_rules = self.rules.get("validation", {})
        max_length = validation_rules.get("max_query_length", 10000)
        if isinstance(max_length, int) and len(query) > max_length:
            is_valid = False
            errors_list.append(f"Query exceeds maximum length of {max_length} characters")
            # Record rejection metric
            if self.metrics:
                user_id = str(context.get("user_id", "anonymous"))
                self.metrics.record_compliance_rejection(
                    reason="max_length_exceeded", risk_level="MEDIUM", user_id=user_id
                )

        # Verifier les patterns interdits
        forbidden_patterns = validation_rules.get("forbidden_patterns", [])
        # Map patterns to their types for reliable categorization
        pii_pattern_types = {
            r"\b\d{3}-\d{2}-\d{4}\b": "ssn",
            r"\b[A-Z]{2}\d{6}\b": "health_insurance",
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b": "email",
        }
        if isinstance(forbidden_patterns, list):
            for pattern in forbidden_patterns:
                if isinstance(pattern, str):
                    pattern_triggered = any(
                        match.end() >= len(query) or query[match.end()] != "@"
                        for match in re.finditer(pattern, query)
                    )

                    if pattern_triggered:
                        is_valid = False
                        errors_list.append(f"Query contains forbidden pattern: {pattern}")
                        # Record rejection metric
                        if self.metrics:
                            user_id = str(context.get("user_id", "anonymous"))
                            self.metrics.record_compliance_rejection(
                                reason="forbidden_pattern", risk_level="HIGH", user_id=user_id
                            )
                            # Record as suspicious pattern for security monitoring
                            self.metrics.record_suspicious_pattern(
                                pattern_type="forbidden_keyword", action_taken="blocked"
                            )

        # Detecter les PII
        pii_patterns = validation_rules.get("pii_patterns", [])
        pii_found: List[str] = []
        pii_types_detected: List[str] = []
        if isinstance(pii_patterns, list):
            for pattern in pii_patterns:
                if isinstance(pattern, str):
                    matches = re.findall(pattern, query)
                    if matches:
                        pii_found.extend(matches)
                        # Determine PII type using mapping
                        pii_type = pii_pattern_types.get(pattern, "unknown")
                        pii_types_detected.append(pii_type)

        if pii_found:
            warnings_list.append(
                f"Query contains potential PII: {len(pii_found)} instance(s) detected"
            )
            metadata.pii_detected = True
            metadata.pii_count = len(pii_found)

            # Record PII detection metrics
            if self.metrics:
                for pii_type in set(pii_types_detected):
                    self.metrics.record_pii_detection(pii_type=pii_type, action_taken="logged")

        # Verifier les champs requis dans le contexte
        required_fields = validation_rules.get("required_fields", [])
        if isinstance(required_fields, list):
            missing_fields = [field for field in required_fields if field not in context]
            if missing_fields and "query" not in missing_fields:  # query is the query itself
                warnings_list.append(
                    f"Missing recommended context fields: {', '.join(missing_fields)}"
                )

        # Logger l'audit
        audit_rules = self.rules.get("audit", {})
        if audit_rules.get("log_all_queries", True):
            self._log_audit(
                "query_validation",
                {
                    "query_hash": metadata.query_hash or "",
                    "valid": is_valid,
                    "warnings_count": len(warnings_list),
                    "errors_count": len(errors_list),
                    "context": context,
                },
            )

        # Record validation metrics
        duration = time.time() - start_time
        if self.metrics:
            status = "rejected" if not is_valid else ("warning" if warnings_list else "passed")
            risk_level = "HIGH" if not is_valid else ("MEDIUM" if warnings_list else "LOW")
            self.metrics.record_compliance_validation(
                status=status, risk_level=risk_level, duration_seconds=duration
            )

        if not is_valid:
            raise ComplianceError(f"Query validation failed: {'; '.join(errors_list)}")

        return QueryValidationResult(
            valid=is_valid,
            warnings=warnings_list,
            errors=errors_list,
            metadata=metadata,
        )

    def validate_execution_plan(
        self, plan: PlanDict, context: Optional[ContextDict] = None
    ) -> PlanValidationResult:
        """
        Valider un plan d'execution avant son execution

        Args:
            plan: Le plan d'execution (graphe de taches HTN ou liste d'actions)
            context: Contexte additionnel

        Returns:
            PlanValidationResult avec resultat de validation

        Raises:
            ComplianceError: Si le plan viole les regles de conformite
        """
        context = context or {}

        # Initialize typed lists
        warnings_list: List[str] = []
        errors_list: List[str] = []
        is_valid = True

        # Initialize metadata
        metadata = ValidationMetadata(
            timestamp=datetime.utcnow().isoformat(),
            plan_hash=hashlib.sha256(str(plan).encode()).hexdigest(),
        )

        # Analyser le plan
        tools_used = self._extract_tools_from_plan(plan)
        plan_depth = self._calculate_plan_depth(plan)

        # Verifier la profondeur
        execution_rules = self.rules.get("execution", {})
        max_depth = execution_rules.get("max_plan_depth", 5)
        if isinstance(max_depth, int) and plan_depth > max_depth:
            is_valid = False
            errors_list.append(f"Plan depth {plan_depth} exceeds maximum of {max_depth}")

        # Verifier le nombre d'outils
        max_tools = execution_rules.get("max_tools_per_plan", 20)
        if isinstance(max_tools, int) and len(tools_used) > max_tools:
            is_valid = False
            errors_list.append(f"Plan uses {len(tools_used)} tools, exceeds maximum of {max_tools}")

        # Verifier les outils interdits
        forbidden_tools_list = execution_rules.get("forbidden_tools", [])
        if isinstance(forbidden_tools_list, list):
            forbidden_tools: Set[str] = set(str(t) for t in forbidden_tools_list)
            used_forbidden = forbidden_tools.intersection(tools_used)
            if used_forbidden:
                is_valid = False
                errors_list.append(f"Plan uses forbidden tools: {', '.join(used_forbidden)}")

        # Verifier les outils necessitant approbation
        require_approval_list = execution_rules.get("require_approval_for", [])
        if isinstance(require_approval_list, list):
            require_approval: Set[str] = set(str(t) for t in require_approval_list)
            needs_approval = require_approval.intersection(tools_used)
            if needs_approval:
                warnings_list.append(
                    f"Plan uses tools requiring approval: {', '.join(needs_approval)}"
                )
                metadata.requires_approval = True
                metadata.approval_tools = list(needs_approval)

        # Logger l'audit
        audit_rules = self.rules.get("audit", {})
        if audit_rules.get("log_all_plans", True):
            self._log_audit(
                "plan_validation",
                {
                    "plan_hash": metadata.plan_hash or "",
                    "valid": is_valid,
                    "tools_count": len(tools_used),
                    "plan_depth": plan_depth,
                    "warnings_count": len(warnings_list),
                    "errors_count": len(errors_list),
                    "context": context,
                },
            )

        if not is_valid:
            raise ComplianceError(f"Plan validation failed: {'; '.join(errors_list)}")

        return PlanValidationResult(
            valid=is_valid,
            warnings=warnings_list,
            errors=errors_list,
            metadata=metadata,
        )

    def audit_execution(
        self, execution_result: ExecutionResultDict, context: Optional[ContextDict] = None
    ) -> ExecutionAuditResult:
        """
        Auditer le resultat d'une execution

        Args:
            execution_result: Resultat de l'execution
            context: Contexte additionnel

        Returns:
            ExecutionAuditResult avec resultat de l'audit
        """
        context = context or {}

        # Initialize compliance check
        issues_list: List[str] = []
        execution_hash = hashlib.sha256(str(execution_result).encode()).hexdigest()

        # Verifier si l'execution a reussi
        success = execution_result.get("success", False)
        if not success:
            issues_list.append("Execution failed - review required")

        # Verifier les erreurs
        errors = execution_result.get("errors", [])
        errors_list = errors if isinstance(errors, list) else []
        if errors_list:
            issues_list.append(f"Execution had {len(errors_list)} error(s)")

        # Create compliance check result
        compliance_check = ComplianceCheckResult(
            passed=len(issues_list) == 0,
            issues=issues_list,
        )

        # Logger l'audit
        audit_rules = self.rules.get("audit", {})
        if audit_rules.get("log_all_executions", True):
            self._log_audit(
                "execution_audit",
                {
                    "execution_hash": execution_hash,
                    "success": bool(success),
                    "errors_count": len(errors_list),
                    "issues_count": len(issues_list),
                    "context": context,
                },
            )

        return ExecutionAuditResult(
            audited=True,
            timestamp=datetime.utcnow().isoformat(),
            execution_hash=execution_hash,
            compliance_check=compliance_check,
        )

    def generate_decision_record(
        self,
        decision_type: str,
        query: str,
        plan: PlanDict,
        execution_result: ExecutionResultDict,
        context: Optional[ContextDict] = None,
    ) -> DecisionRecord:
        """
        Generer un Decision Record pour tracabilite

        Args:
            decision_type: Type de decision (ex: 'automated_execution')
            query: Requete originale
            plan: Plan d'execution
            execution_result: Resultat de l'execution
            context: Contexte additionnel

        Returns:
            DecisionRecord pour tracabilite Loi 25/PIPEDA
        """
        context = context or {}

        legal_rules = self.rules.get("legal", {})
        frameworks = legal_rules.get("frameworks", [])
        frameworks_list = [str(f) for f in frameworks] if isinstance(frameworks, list) else []

        dr_id = self._generate_dr_id()
        tools_used = self._extract_tools_from_plan(plan)
        success = bool(execution_result.get("success", False))

        dr = DecisionRecord(
            dr_id=dr_id,
            timestamp=datetime.utcnow().isoformat(),
            decision_type=decision_type,
            actor=str(context.get("actor", "system")),
            task_id=str(context.get("task_id", "")),
            query_hash=hashlib.sha256(query.encode()).hexdigest(),
            plan_hash=hashlib.sha256(str(plan).encode()).hexdigest(),
            execution_hash=hashlib.sha256(str(execution_result).encode()).hexdigest(),
            tools_used=tools_used,
            success=success,
            compliance_frameworks=frameworks_list,
            metadata=DecisionRecordMetadata(
                guardian_version="1.0.0",
                rules_version=str(self.rules.get("version", "1.0.0")),
            ),
        )

        # Logger le DR
        self._log_audit(
            "decision_record_created",
            {
                "dr_id": dr_id,
                "decision_type": decision_type,
                "success": success,
            },
        )

        return dr

    def _extract_tools_from_plan(self, plan: PlanDict) -> Set[str]:
        """Extraire la liste des outils utilises dans un plan"""
        tools: Set[str] = set()

        # Si le plan a une structure HTN avec un graphe
        if "graph" in plan:
            graph = plan["graph"]
            if hasattr(graph, "nodes"):
                nodes = getattr(graph, "nodes", {})
                for node in nodes.values():
                    if hasattr(node, "action"):
                        tools.add(str(getattr(node, "action")))

        # Si le plan est une liste d'actions
        elif "actions" in plan:
            actions = plan["actions"]
            if isinstance(actions, list):
                for action in actions:
                    if isinstance(action, dict) and "tool" in action:
                        tools.add(str(action["tool"]))

        # Si le plan a des tools_used directement
        elif "tools_used" in plan:
            tools_used = plan["tools_used"]
            if isinstance(tools_used, set):
                tools.update(str(t) for t in tools_used)
            elif isinstance(tools_used, list):
                tools.update(str(t) for t in tools_used)

        return tools

    def _calculate_plan_depth(self, plan: PlanDict) -> int:
        """Calculer la profondeur d'un plan"""
        # Si le plan a une structure HTN
        if "graph" in plan:
            graph = plan["graph"]
            if hasattr(graph, "get_max_depth"):
                depth = getattr(graph, "get_max_depth")()
                return int(depth) if isinstance(depth, (int, float)) else 1

        # Si le plan est une liste d'actions
        elif "actions" in plan:
            actions = plan["actions"]
            if isinstance(actions, list):
                return len(actions)

        # Par defaut
        return 1

    def _generate_dr_id(self) -> str:
        """Generer un ID unique pour un Decision Record"""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        random_suffix = hashlib.md5(datetime.utcnow().isoformat().encode()).hexdigest()[:6]
        return f"DR-{timestamp}-{random_suffix}"

    def _log_audit(
        self, event_type: str, data: Dict[str, Union[str, bool, int, List[str], ContextDict]]
    ) -> None:
        """Logger un evenement d'audit"""
        audit_entry: AuditEntryDict = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "data": data,
        }
        self.audit_log.append(audit_entry)

    def get_audit_log(self) -> List[AuditEntryDict]:
        """Recuperer le log d'audit"""
        return self.audit_log

    def clear_audit_log(self) -> None:
        """Effacer le log d'audit (pour tests)"""
        self.audit_log = []

    def validate_task(
        self, task: TaskDict, context: Optional[ContextDict] = None
    ) -> ValidationResult:
        """
        Valider une tache individuelle avant execution (pour HTN)

        Args:
            task: Tache a valider (doit contenir au minimum 'action' ou 'tool')
            context: Contexte additionnel (user_id, session_id, etc.)

        Returns:
            ValidationResult avec resultat de validation

        Raises:
            ComplianceError: Si la tache viole gravement les regles de conformite
        """
        context = context or {}
        violations: List[str] = []
        warnings: List[str] = []
        risk_level = "LOW"

        # Extraire l'action/outil de la tache
        action_raw = task.get("action") or task.get("tool") or task.get("name", "")
        action = str(action_raw) if action_raw else ""
        task_params = task.get("parameters", {}) or task.get("arguments", {})
        task_params_dict = task_params if isinstance(task_params, dict) else {}

        # Verifier les outils interdits
        execution_rules = self.rules.get("execution", {})
        forbidden_tools_list = execution_rules.get("forbidden_tools", [])
        if isinstance(forbidden_tools_list, list):
            forbidden_tools: Set[str] = set(str(t) for t in forbidden_tools_list)
            if action in forbidden_tools:
                violations.append(f"Task uses forbidden tool: {action}")
                risk_level = "CRITICAL"

        # Verifier les outils necessitant approbation
        require_approval_list = execution_rules.get("require_approval_for", [])
        if isinstance(require_approval_list, list):
            require_approval: Set[str] = set(str(t) for t in require_approval_list)
            if action in require_approval:
                warnings.append(f"Task uses tool requiring approval: {action}")
                risk_level = "HIGH"

        # Verifier les patterns dangereux dans les parametres
        params_str = str(task_params_dict)
        validation_rules = self.rules.get("validation", {})
        forbidden_patterns = validation_rules.get("forbidden_patterns", [])
        if isinstance(forbidden_patterns, list):
            for pattern in forbidden_patterns:
                if isinstance(pattern, str) and re.search(pattern, params_str):
                    violations.append(f"Task parameters contain forbidden pattern: {pattern}")
                    risk_level = "HIGH"

        # Verifier les patterns PII
        pii_patterns = validation_rules.get("pii_patterns", [])
        pii_found: List[str] = []
        if isinstance(pii_patterns, list):
            for pattern in pii_patterns:
                if isinstance(pattern, str):
                    matches = re.findall(pattern, params_str)
                    if matches:
                        pii_found.extend(matches)

        if pii_found:
            warnings.append(f"Task parameters contain potential PII: {len(pii_found)} instance(s)")

        # Determiner si la tache est conforme
        is_compliant = len(violations) == 0

        # Convert string risk level to enum
        risk_level_enum = RiskLevel(risk_level)

        # Build context dict for metadata (filter to allowed types)
        context_filtered: Dict[str, Union[str, int, bool]] = {}
        for k, v in context.items():
            if isinstance(v, (str, int, bool)):
                context_filtered[k] = v

        # Creer le resultat avec Pydantic models
        result = ValidationResult(
            is_compliant=is_compliant,
            violations=violations,
            risk_level=risk_level_enum,
            warnings=warnings,
            metadata=ValidationMetadata(
                timestamp=datetime.utcnow().isoformat(),
                task_action=action,
                pii_detected=len(pii_found) > 0,
                pii_count=len(pii_found),
                context=context_filtered,
            ),
        )

        # Logger l'audit
        self._log_audit(
            "task_validation",
            {
                "action": action,
                "is_compliant": is_compliant,
                "violations_count": len(violations),
                "warnings_count": len(warnings),
                "risk_level": risk_level,
            },
        )

        # Lever une exception si violation critique
        if not is_compliant and risk_level_enum == RiskLevel.CRITICAL:
            raise ComplianceError(f"Task validation failed: {'; '.join(violations)}")

        return result
