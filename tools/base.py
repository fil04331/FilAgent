"""
Interface de base pour les outils sandbox
Tous les outils doivent hériter de cette classe
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum


class ToolStatus(Enum):
    """Statut d'exécution d'un outil"""

    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"


# Types stricts pour les valeurs de paramètres et métadonnées
ToolParamValue = Union[str, int, float, bool, None, List[str], Dict[str, str]]
ToolMetadataValue = Union[str, int, float, bool, List[str], Dict[str, str]]

# Type récursif pour JSON Schema (utilisé par get_schema et _get_parameters_schema)
JsonSchemaValue = Union[str, bool, List[str], Dict[str, "JsonSchemaValue"]]
ToolSchemaDict = Dict[str, JsonSchemaValue]


@dataclass
class ToolResult:
    """Résultat de l'exécution d'un outil"""

    status: ToolStatus
    output: str  # Sortie de l'outil
    error: Optional[str] = None
    metadata: Optional[Dict[str, ToolMetadataValue]] = field(default=None)
    error_message: Optional[str] = None

    def __post_init__(self) -> None:
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
    def execute(self, arguments: Dict[str, ToolParamValue]) -> ToolResult:
        """
        Exécuter l'outil avec les arguments fournis

        Args:
            arguments: Dictionnaire des arguments de l'outil

        Returns:
            ToolResult avec le statut et la sortie
        """

    @abstractmethod
    def validate_arguments(
        self, arguments: Dict[str, ToolParamValue]
    ) -> tuple[bool, Optional[str]]:
        """
        Valider les arguments avant exécution

        Returns:
            (is_valid, error_message)
        """

    def get_schema(self) -> ToolSchemaDict:
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
    def _get_parameters_schema(self) -> ToolSchemaDict:
        """Retourner le schéma JSON des paramètres"""
