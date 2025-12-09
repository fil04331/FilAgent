"""
FilAgent Custom Exceptions

Hiérarchie d'exceptions structurée pour une gestion d'erreurs robuste.
Toutes les exceptions FilAgent héritent de FilAgentError pour permettre
un catch global si nécessaire.

Usage:
    from runtime.exceptions import ConfigurationError, ModelError

    try:
        config = load_config()
    except ConfigurationError as e:
        logger.error("config_load_failed", error=str(e))
        raise
"""

from typing import Optional, Dict, Any


class FilAgentError(Exception):
    """
    Exception de base pour toutes les erreurs FilAgent.

    Permet de catcher toutes les erreurs FilAgent avec un seul except:
        except FilAgentError as e:
            handle_filagent_error(e)

    Attributes:
        message: Description de l'erreur
        details: Contexte additionnel structuré (optionnel)
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | details={self.details}"
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        """Sérialise l'exception pour logging structuré."""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


# =============================================================================
# Configuration Errors
# =============================================================================

class ConfigurationError(FilAgentError):
    """
    Erreur de configuration (YAML invalide, variable d'environnement manquante).

    Examples:
        - Fichier config/agent.yaml introuvable
        - Clé de configuration manquante
        - Valeur de configuration invalide
    """
    pass


class EnvironmentError(ConfigurationError):
    """
    Variable d'environnement requise manquante ou invalide.

    Examples:
        - PERPLEXITY_API_KEY non définie
        - MODEL_PATH pointe vers un fichier inexistant
    """

    def __init__(self, var_name: str, message: Optional[str] = None):
        msg = message or f"Environment variable '{var_name}' is required but not set"
        super().__init__(msg, details={"var_name": var_name})


# =============================================================================
# Model Errors
# =============================================================================

class ModelError(FilAgentError):
    """
    Erreur liée au modèle LLM (génération, timeout, initialisation).

    Examples:
        - Échec de chargement du modèle
        - Timeout de génération
        - Réponse malformée
    """
    pass


class ModelInitializationError(ModelError):
    """
    Échec d'initialisation du modèle.

    Examples:
        - Fichier de poids introuvable
        - Mémoire insuffisante
        - Backend non supporté
    """

    def __init__(self, backend: str, message: str, model_path: Optional[str] = None):
        super().__init__(message, details={"backend": backend, "model_path": model_path})


class GenerationError(ModelError):
    """
    Échec de génération de texte.

    Examples:
        - Timeout de génération
        - Réponse vide
        - Erreur de tokenization
    """
    pass


class ProviderUnavailableError(ModelError):
    """
    Provider LLM externe non disponible (API down, rate limit).

    Examples:
        - API Perplexity non joignable
        - Rate limit atteint
        - Erreur d'authentification API
    """

    def __init__(self, provider: str, message: str, status_code: Optional[int] = None):
        super().__init__(message, details={"provider": provider, "status_code": status_code})


class RateLimitError(ProviderUnavailableError):
    """
    Rate limit atteint sur un provider externe.

    Attributes:
        retry_after: Secondes avant de pouvoir réessayer (si connu)
    """

    def __init__(self, provider: str, retry_after: Optional[int] = None):
        msg = f"Rate limit exceeded for provider '{provider}'"
        if retry_after:
            msg += f", retry after {retry_after}s"
        super().__init__(provider, msg)
        self.retry_after = retry_after
        self.details["retry_after"] = retry_after


# =============================================================================
# Validation Errors
# =============================================================================

class ValidationError(FilAgentError):
    """
    Erreur de validation des entrées utilisateur ou données.

    Examples:
        - Format de message invalide
        - Paramètre manquant
        - Type de données incorrect
    """

    def __init__(self, field: str, message: str, value: Any = None):
        super().__init__(message, details={"field": field, "value": str(value) if value else None})


class FileValidationError(ValidationError):
    """
    Erreur de validation de fichier.

    Examples:
        - Extension non supportée
        - Fichier trop volumineux
        - Fichier corrompu
    """

    def __init__(self, filename: str, message: str, reason: Optional[str] = None):
        super().__init__("file", message, value=filename)
        self.details["reason"] = reason


# =============================================================================
# Execution Errors
# =============================================================================

class ExecutionError(FilAgentError):
    """
    Erreur d'exécution d'une tâche ou action.

    Examples:
        - Échec d'exécution d'un outil
        - Action non trouvée
        - Timeout d'exécution
    """
    pass


class ToolExecutionError(ExecutionError):
    """
    Erreur d'exécution d'un outil spécifique.

    Examples:
        - Outil non trouvé
        - Paramètres invalides
        - Timeout de l'outil
    """

    def __init__(self, tool_name: str, message: str, arguments: Optional[Dict] = None):
        super().__init__(message, details={"tool_name": tool_name, "arguments": arguments})


class TaskExecutionError(ExecutionError):
    """
    Erreur d'exécution d'une tâche HTN.

    Examples:
        - Tâche échouée
        - Dépendance non satisfaite
        - Timeout de tâche
    """

    def __init__(self, task_id: str, message: str, task_name: Optional[str] = None):
        super().__init__(message, details={"task_id": task_id, "task_name": task_name})


class TimeoutError(ExecutionError):
    """
    Dépassement du temps d'exécution alloué.

    Attributes:
        timeout_seconds: Timeout configuré
        elapsed_seconds: Temps écoulé avant interruption
    """

    def __init__(self, operation: str, timeout_seconds: float, elapsed_seconds: Optional[float] = None):
        msg = f"Operation '{operation}' timed out after {timeout_seconds}s"
        super().__init__(msg, details={
            "operation": operation,
            "timeout_seconds": timeout_seconds,
            "elapsed_seconds": elapsed_seconds,
        })


# =============================================================================
# Compliance Errors
# =============================================================================

class ComplianceError(FilAgentError):
    """
    Violation des règles de conformité (Loi 25, RGPD, etc.).

    Examples:
        - PII détecté dans la sortie
        - Action non autorisée par RBAC
        - Violation de contrainte de sécurité
    """

    def __init__(self, rule: str, message: str, context: Optional[Dict] = None):
        super().__init__(message, details={"rule": rule, "context": context})


class ComplianceViolationError(ComplianceError):
    """
    Violation explicite d'une règle de conformité.

    Examples:
        - Tentative d'accès non autorisée
        - Données sensibles dans les logs
    """
    pass


class RBACError(ComplianceError):
    """
    Erreur de contrôle d'accès basé sur les rôles.

    Examples:
        - Utilisateur non autorisé
        - Rôle insuffisant pour l'action
    """

    def __init__(self, action: str, required_role: str, user_role: Optional[str] = None):
        msg = f"Action '{action}' requires role '{required_role}'"
        if user_role:
            msg += f", but user has role '{user_role}'"
        super().__init__("rbac", msg, context={"required_role": required_role, "user_role": user_role})


# =============================================================================
# Planning Errors
# =============================================================================

class PlanningError(FilAgentError):
    """
    Erreur de planification HTN.

    Examples:
        - Décomposition impossible
        - Cycle de dépendances
        - Contrainte non satisfaite
    """
    pass


class TaskDecompositionError(PlanningError):
    """
    Erreur de décomposition de tâche.

    Examples:
        - Tâche non décomposable
        - Profondeur maximale atteinte
    """

    def __init__(self, task_name: str, message: str, depth: Optional[int] = None):
        super().__init__(message, details={"task_name": task_name, "depth": depth})


class DependencyCycleError(PlanningError):
    """
    Cycle détecté dans le graphe de dépendances.
    """

    def __init__(self, cycle_path: list):
        msg = f"Dependency cycle detected: {' -> '.join(cycle_path)}"
        super().__init__(msg, details={"cycle_path": cycle_path})


# =============================================================================
# Memory Errors
# =============================================================================

class MemoryError(FilAgentError):
    """
    Erreur liée au système de mémoire (épisodique, sémantique).

    Examples:
        - Échec de persistance
        - Corruption de données
        - Base de données inaccessible
    """
    pass


class PersistenceError(MemoryError):
    """
    Échec de persistance des données.
    """

    def __init__(self, operation: str, message: str, entity: Optional[str] = None):
        super().__init__(message, details={"operation": operation, "entity": entity})


# =============================================================================
# Utility: Exception mapping for external errors
# =============================================================================

def wrap_external_error(exc: Exception, context: str) -> FilAgentError:
    """
    Enveloppe une exception externe dans une exception FilAgent.

    Usage:
        try:
            external_api_call()
        except RequestException as e:
            raise wrap_external_error(e, "api_call") from e

    Args:
        exc: Exception originale
        context: Contexte de l'opération

    Returns:
        FilAgentError appropriée
    """
    error_type = type(exc).__name__
    return ExecutionError(
        f"{context} failed: {error_type}: {str(exc)}",
        details={"original_type": error_type, "context": context}
    )
