"""
Registre des outils disponibles
Permet de gérer et récupérer les outils de manière centralisée
"""

from typing import Dict, Optional
from .base import BaseTool
from .python_sandbox import PythonSandboxTool
from .file_reader import FileReaderTool
from .calculator import CalculatorTool


class ToolRegistry:
    """Registre centralisé pour tous les outils disponibles"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """Enregistrer les outils par défaut"""
        default_tools = [
            PythonSandboxTool(),
            FileReaderTool(),
            CalculatorTool(),
        ]

        for tool in default_tools:
            self.register(tool)

    def register(self, tool: BaseTool):
        """Enregistrer un outil"""
        self._tools[tool.name] = tool

    def get(self, tool_name: str) -> Optional[BaseTool]:
        """Récupérer un outil par son nom"""
        return self._tools.get(tool_name)

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Alias pour compatibilité avec anciens tests."""
        return self.get(tool_name)

    def list_all(self) -> Dict[str, BaseTool]:
        """Lister tous les outils disponibles"""
        return self._tools.copy()

    def get_all(self) -> list[BaseTool]:
        """
        Retourne une liste de tous les outils disponibles

        Returns:
            list[BaseTool]: Liste de tous les outils enregistrés
        """
        return list(self._tools.values())

    def get_schemas(self) -> Dict[str, dict]:
        """Obtenir tous les schémas JSON des outils"""
        return {name: tool.get_schema() for name, tool in self._tools.items()}


# Instance globale
_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """Récupérer le registre global"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def reload_registry():
    """Recharger le registre (utile pour les tests)"""
    global _registry
    _registry = ToolRegistry()
    return _registry
