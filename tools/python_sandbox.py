"""
Sandbox Python pour exécution sûre de code Python
Limites CPU, mémoire, et filesystem
"""

import subprocess
import tempfile
import os
import time
import ast
import sys
from typing import Dict, Any, Optional, List

from .base import BaseTool, ToolResult, ToolStatus

# Import resource module for Unix systems
try:
    import resource
    RESOURCE_AVAILABLE = True
except ImportError:
    RESOURCE_AVAILABLE = False


class PythonSandboxTool(BaseTool):
    """
    Outil pour exécuter du code Python en sandbox
    Limites : CPU, mémoire, timeout
    """

    def __init__(self, dangerous_patterns: Optional[List[str]] = None):
        super().__init__(
            name="python_sandbox", description="Exécuter du code Python de manière sécurisée dans un sandbox"
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

    def _set_resource_limits(self):
        """
        Définir les limites de ressources pour le processus sandbox
        Appelé via preexec_fn dans subprocess (Unix uniquement)
        """
        if not RESOURCE_AVAILABLE:
            return

        try:
            # Limite CPU time (secondes)
            resource.setrlimit(resource.RLIMIT_CPU, (self.max_cpu_time, self.max_cpu_time))

            # Limite mémoire (bytes)
            max_memory_bytes = self.max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (max_memory_bytes, max_memory_bytes))

            # Limite nombre de processus/threads (empêcher fork bombs)
            resource.setrlimit(resource.RLIMIT_NPROC, (1, 1))

            # Limite taille de fichier (empêcher création de gros fichiers)
            resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))  # 10 MB

            # Limite nombre de fichiers ouverts
            resource.setrlimit(resource.RLIMIT_NOFILE, (10, 10))
        except Exception as e:
            # Si les limites échouent, on continue mais on log
            print(f"Warning: Failed to set resource limits: {e}")

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Exécuter le code Python"""
        # Valider les arguments
        is_valid, error = self.validate_arguments(arguments)
        if not is_valid:
            return ToolResult(status=ToolStatus.ERROR, output="", error=f"Invalid arguments: {error}")

        code = arguments["code"]

        try:
            # Créer un fichier temporaire
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(code)
                temp_file = f.name

            try:
                # Exécuter avec timeout et limites de ressources
                start_time = time.time()

                # Préparer l'environnement sécurisé
                env = os.environ.copy()
                env['PYTHONDONTWRITEBYTECODE'] = '1'  # Pas de fichiers .pyc

                # Exécuter avec limites de ressources (Unix) ou simple timeout (Windows)
                if RESOURCE_AVAILABLE and sys.platform != 'win32':
                    result = subprocess.run(
                        ["python3", temp_file],
                        capture_output=True,
                        text=True,
                        timeout=self.timeout,
                        cwd=os.path.dirname(temp_file),
                        env=env,
                        preexec_fn=self._set_resource_limits,  # Appliquer limites CPU/mémoire
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

                # Vérifier le résultat
                if result.returncode == 0:
                    output = result.stdout
                    if not output:
                        output = "[Code exécuté avec succès, pas de sortie]"

                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        output=output,
                        metadata={"returncode": result.returncode, "elapsed_time": elapsed_time, "timeout": False},
                    )
                else:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        output="",
                        error=f"Execution failed: {result.stderr}",
                        metadata={"returncode": result.returncode, "stderr": result.stderr},
                    )

            except subprocess.TimeoutExpired:
                return ToolResult(
                    status=ToolStatus.TIMEOUT,
                    output="",
                    error=f"Execution timeout after {self.timeout}s",
                    metadata={"timeout": True},
                )
            except Exception as e:
                return ToolResult(status=ToolStatus.ERROR, output="", error=f"Execution error: {str(e)}")
            finally:
                # Nettoyer le fichier temporaire
                try:
                    os.unlink(temp_file)
                except Exception:
                    pass

        except Exception as e:
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

    def validate_arguments(self, arguments: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Valider les arguments"""
        if not isinstance(arguments, dict):
            return False, "Arguments must be a dictionary"

        if "code" not in arguments:
            return False, "Missing required argument: 'code'"

        if not isinstance(arguments["code"], str):
            return False, "Argument 'code' must be a string"

        if len(arguments["code"]) > 50000:  # Limiter la taille
            return False, "Code too long (max 50000 characters)"

        # Validation AST (plus sûre que les patterns)
        is_valid, error = self._validate_ast(arguments["code"])
        if not is_valid:
            return False, error

        # Bloquer certaines opérations dangereuses (double vérification)
        code_lower = arguments["code"].lower()
        for pattern in self.dangerous_patterns:
            if pattern.lower() in code_lower:
                return False, f"Blocked dangerous operation: {pattern}"

        return True, None

    def _get_parameters_schema(self) -> Dict[str, Any]:
        """Schéma des paramètres"""
        return {
            "type": "object",
            "properties": {"code": {"type": "string", "description": "Code Python à exécuter"}},
            "required": ["code"],
        }
