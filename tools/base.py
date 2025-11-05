"""
Interface de base pour les outils sandbox
Tous les outils doivent hériter de cette classe
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class ToolStatus(Enum):
    """Statut d'exécution d'un outil"""

    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"


@dataclass
class ToolResult:
    """Résultat de l'exécution d'un outil"""

    status: ToolStatus
    output: str  # Sortie de l'outil
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        # Harmoniser les alias error / error_message
        if self.error_message is not None and self.error is None:
            self.error = self.error_message
        elif self.error is not None and self.error_message is None:
            self.error_message = self.error

    def is_success(self) -> bool:
        """Vérifier si l'exécution a réussi"""
        return self.status == ToolStatus.SUCCESS


class BaseTool(ABC):
    """Classe de base pour tous les outils"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """
        Exécuter l'outil avec les arguments fournis

        Args:
            arguments: Dictionnaire des arguments de l'outil

        Returns:
            ToolResult avec le statut et la sortie
        """
        pass

    @abstractmethod
    def validate_arguments(self, arguments: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Valider les arguments avant exécution

        Returns:
            (is_valid, error_message)
        """
        pass

    def get_schema(self) -> Dict[str, Any]:
        """
        Retourner le schéma JSON pour cet outil
        Utilisé pour la documentation et la validation

        Returns:
            Dictionnaire avec 'name', 'description', 'parameters'
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self._get_parameters_schema(),
        }

    @abstractmethod
    def _get_parameters_schema(self) -> Dict[str, Any]:
        """Retourner le schéma JSON des paramètres"""
        pass
