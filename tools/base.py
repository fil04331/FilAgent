"""
Interface de base pour les outils sandbox
Tous les outils doivent hériter de cette classe
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


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
            "parameters": self._get_parameters_schema()
        }
    
    @abstractmethod
    def _get_parameters_schema(self) -> Dict[str, Any]:
        """Retourner le schéma JSON des paramètres"""
        pass
