"""
Outil pour lire des fichiers de manière sécurisée
Avec allowlist et validation de chemins
"""

from typing import Dict, Any, Optional
from pathlib import Path

from .base import BaseTool, ToolResult, ToolStatus


class FileReaderTool(BaseTool):
    """
    Outil pour lire des fichiers
    Restrictions: allowlist de chemins, lecture seule
    """

    def __init__(self):
        super().__init__(name="file_read", description="Lire le contenu d'un fichier de manière sécurisée")
        # Chemins autorisés (peuvent être configurés via policies.yaml)
        self.allowed_paths = [
            "working_set/",
            "temp/",
            "memory/working_set/",
        ]
        self.max_file_size = 10 * 1024 * 1024  # 10 MB

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Lire un fichier"""
        # Valider les arguments
        is_valid, error = self.validate_arguments(arguments)
        if not is_valid:
            return ToolResult(status=ToolStatus.BLOCKED, output="", error=f"Invalid arguments: {error}")

        file_path = arguments["file_path"]

        try:
            path = Path(file_path).resolve()

            # Vérifier que le chemin est autorisé
            if not self._is_path_allowed(path):
                return ToolResult(status=ToolStatus.BLOCKED, output="", error=f"Path not allowed: {file_path}")

            # Vérifier que le fichier existe
            if not path.exists():
                return ToolResult(status=ToolStatus.ERROR, output="", error=f"File not found: {file_path}")

            # Vérifier que c'est un fichier (pas un dossier)
            if not path.is_file():
                return ToolResult(status=ToolStatus.ERROR, output="", error=f"Path is not a file: {file_path}")

            # Vérifier la taille du fichier
            file_size = path.stat().st_size
            if file_size > self.max_file_size:
                return ToolResult(
                    status=ToolStatus.BLOCKED,
                    output="",
                    error=f"File too large ({file_size} bytes, max {self.max_file_size})",
                )

            # Lire le fichier
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            return ToolResult(
                status=ToolStatus.SUCCESS, output=content, metadata={"file_path": str(path), "file_size": file_size}
            )

        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, output="", error=f"Failed to read file: {str(e)}")

    def _is_path_allowed(self, path: Path) -> bool:
        """Vérifier si un chemin est dans la liste autorisée"""
        # Vérifier chaque chemin autorisé
        for allowed in self.allowed_paths:
            allowed_path = Path(allowed).resolve()
            try:
                # Vérifier si le chemin est sous le chemin autorisé
                path.relative_to(allowed_path)
                return True
            except ValueError:
                continue
        return False

    def validate_arguments(self, arguments: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Valider les arguments"""
        if not isinstance(arguments, dict):
            return False, "Arguments must be a dictionary"

        if "file_path" not in arguments:
            return False, "Missing required argument: 'file_path'"

        if not isinstance(arguments["file_path"], str):
            return False, "Argument 'file_path' must be a string"

        # Vérifier qu'il n'y a pas de path traversal
        if ".." in arguments["file_path"]:
            return False, "Path traversal detected (..)"

        return True, None

    def _get_parameters_schema(self) -> Dict[str, Any]:
        """Schéma des paramètres"""
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Chemin du fichier à lire (doit être dans les chemins autorisés)",
                }
            },
            "required": ["file_path"],
        }
