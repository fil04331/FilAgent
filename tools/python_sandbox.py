"""
Sandbox Python pour execution sure de code Python
Limites CPU, memoire, et filesystem
"""

from __future__ import annotations

import subprocess
import tempfile
import os
import time
import ast
import sys
from typing import Dict, List, Optional, Union

from .base import BaseTool, ToolResult, ToolStatus, ToolParamValue, ToolMetadataValue, ToolSchemaDict

# Import resource module for Unix systems
try:
    import resource
    RESOURCE_AVAILABLE = True
except ImportError:
    RESOURCE_AVAILABLE = False

# Types stricts pour le sandbox Python
ParameterSchemaValue = Union[str, Dict[str, str], List[str]]
SandboxMetadataValue = Union[str, int, float, bool]


class PythonSandboxTool(BaseTool):
    """
    Outil pour executer du code Python en sandbox
    Limites : CPU, memoire, timeout
    """

    max_memory_mb: int
    max_cpu_time: int
    timeout: int
    dangerous_patterns: List[str]

    def __init__(self, dangerous_patterns: Optional[List[str]] = None) -> None:
        super().__init__(
            name="python_sandbox", description="Executer du code Python de maniere securisee dans un sandbox"
        )
        # Limites de ressources
        self.max_memory_mb = 512
        self.max_cpu_time = 30  # secondes
        self.timeout = 30  # secondes total

        # Patterns dangereux configurables
        if dangerous_patterns is None:
            self.dangerous_patterns = [
                "__import__",
                "eval(",
                "exec(",
                "open(",
                "file(",
                "os.system",
                "import os",
                "subprocess",
                "pickle",
            ]
        else:
            self.dangerous_patterns = dangerous_patterns

    def _set_resource_limits(self) -> None:
        """
        Definir les limites de ressources pour le processus sandbox
        Appele via preexec_fn dans subprocess (Unix uniquement)
        """
        if not RESOURCE_AVAILABLE:
            return

        try:
            # Limite CPU time (secondes)
            resource.setrlimit(resource.RLIMIT_CPU, (self.max_cpu_time, self.max_cpu_time))

            # Limite memoire (bytes)
            max_memory_bytes = self.max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (max_memory_bytes, max_memory_bytes))

            # Limite nombre de processus/threads (empecher fork bombs)
            resource.setrlimit(resource.RLIMIT_NPROC, (1, 1))

            # Limite taille de fichier (empecher creation de gros fichiers)
            resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))  # 10 MB

            # Limite nombre de fichiers ouverts
            resource.setrlimit(resource.RLIMIT_NOFILE, (10, 10))
        except (ValueError, OSError) as e:
            # Si les limites echouent, on continue mais on log
            print(f"Warning: Failed to set resource limits: {e}")

    def execute(self, arguments: Dict[str, ToolParamValue]) -> ToolResult:
        """Executer le code Python"""
        # Valider les arguments
        is_valid, error = self.validate_arguments(arguments)
        if not is_valid:
            return ToolResult(status=ToolStatus.ERROR, output="", error=f"Invalid arguments: {error}")

        code = str(arguments["code"])

        try:
            # Creer un fichier temporaire
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(code)
                temp_file = f.name

            try:
                # Executer avec timeout et limites de ressources
                start_time = time.time()

                # Preparer l'environnement securise
                env = os.environ.copy()
                env['PYTHONDONTWRITEBYTECODE'] = '1'  # Pas de fichiers .pyc

                # Executer avec limites de ressources (Unix) ou simple timeout (Windows)
                if RESOURCE_AVAILABLE and sys.platform != 'win32':
                    result = subprocess.run(
                        ["python3", temp_file],
                        capture_output=True,
                        text=True,
                        timeout=self.timeout,
                        cwd=os.path.dirname(temp_file),
                        env=env,
                        preexec_fn=self._set_resource_limits,  # Appliquer limites CPU/memoire
                    )
                else:
                    # Windows ou resource non disponible - seulement timeout
                    result = subprocess.run(
                        ["python3", temp_file],
                        capture_output=True,
                        text=True,
                        timeout=self.timeout,
                        cwd=os.path.dirname(temp_file),
                        env=env,
                    )

                elapsed_time = time.time() - start_time

                # Verifier le resultat
                if result.returncode == 0:
                    output = result.stdout
                    if not output:
                        output = "[Code execute avec succes, pas de sortie]"

                    metadata: Dict[str, ToolMetadataValue] = {
                        "returncode": result.returncode,
                        "elapsed_time": str(round(elapsed_time, 3)),
                        "timeout": False,
                    }

                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        output=output,
                        metadata=metadata,
                    )
                else:
                    error_metadata: Dict[str, ToolMetadataValue] = {
                        "returncode": result.returncode,
                        "stderr": result.stderr,
                    }
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        output="",
                        error=f"Execution failed: {result.stderr}",
                        metadata=error_metadata,
                    )

            except subprocess.TimeoutExpired:
                timeout_metadata: Dict[str, ToolMetadataValue] = {"timeout": True}
                return ToolResult(
                    status=ToolStatus.TIMEOUT,
                    output="",
                    error=f"Execution timeout after {self.timeout}s",
                    metadata=timeout_metadata,
                )
            except OSError as e:
                return ToolResult(status=ToolStatus.ERROR, output="", error=f"Execution error: {str(e)}")
            finally:
                # Nettoyer le fichier temporaire
                try:
                    os.unlink(temp_file)
                except OSError:
                    pass

        except OSError as e:
            return ToolResult(status=ToolStatus.ERROR, output="", error=f"Failed to execute Python code: {str(e)}")

    def _validate_ast(self, code: str) -> tuple[bool, Optional[str]]:
        """
        Valider le code Python en analysant l'AST (Abstract Syntax Tree)
        Plus sûr que la validation par patterns car analyse la structure du code
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error: {e}"

        # Liste des noms de fonctions/modules dangereux
        dangerous_names = {
            'eval', 'exec', 'compile', '__import__', 'open', 'file',
            'input', 'raw_input', 'execfile', 'reload', 'vars', 'globals',
            'locals', 'dir', 'getattr', 'setattr', 'delattr', 'hasattr',
            '__builtins__', '__dict__', '__class__', '__bases__', '__subclasses__'
        }

        # Modules dangereux
        dangerous_modules = {
            'os', 'sys', 'subprocess', 'multiprocessing', 'threading',
            'socket', 'urllib', 'requests', 'pickle', 'shelve', 'marshal',
            'ctypes', 'imp', 'importlib', 'pty', 'commands'
        }

        # Parcourir l'AST
        for node in ast.walk(tree):
            # Bloquer les imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in dangerous_modules:
                        return False, f"Import of dangerous module blocked: {alias.name}"

            if isinstance(node, ast.ImportFrom):
                if node.module in dangerous_modules:
                    return False, f"Import from dangerous module blocked: {node.module}"

            # Bloquer les appels à fonctions dangereuses
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in dangerous_names:
                        return False, f"Call to dangerous function blocked: {node.func.id}"

                # Bloquer les accès via attributs (ex: __builtins__.eval)
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in dangerous_names:
                        return False, f"Attribute access to dangerous function blocked: {node.func.attr}"

            # Bloquer l'accès aux attributs sensibles
            if isinstance(node, ast.Attribute):
                if node.attr in dangerous_names:
                    return False, f"Access to dangerous attribute blocked: {node.attr}"

            # Bloquer l'utilisation de __dict__, __class__, etc.
            if isinstance(node, ast.Name):
                if node.id in dangerous_names:
                    return False, f"Reference to dangerous name blocked: {node.id}"

        return True, None

    def validate_arguments(self, arguments: Dict[str, ToolParamValue]) -> tuple[bool, Optional[str]]:
        """Valider les arguments"""
        if not isinstance(arguments, dict):
            return False, "Arguments must be a dictionary"

        if "code" not in arguments:
            return False, "Missing required argument: 'code'"

        if not isinstance(arguments["code"], str):
            return False, "Argument 'code' must be a string"

        if len(arguments["code"]) > 50000:  # Limiter la taille
            return False, "Code too long (max 50000 characters)"

        # Validation AST (plus sure que les patterns)
        is_valid, error = self._validate_ast(arguments["code"])
        if not is_valid:
            return False, error

        # Bloquer certaines operations dangereuses (double verification)
        code_lower = arguments["code"].lower()
        for pattern in self.dangerous_patterns:
            if pattern.lower() in code_lower:
                return False, f"Blocked dangerous operation: {pattern}"

        return True, None

    def _get_parameters_schema(self) -> ToolSchemaDict:
        """Schema des parametres"""
        return {
            "type": "object",
            "properties": {"code": {"type": "string", "description": "Code Python a executer"}},
            "required": ["code"],
        }
