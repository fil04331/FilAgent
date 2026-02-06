"""
Sandbox Python pour exécution sûre de code Python dans un conteneur Docker isolé
Limites CPU, mémoire, réseau et filesystem
Zero Trust: tout code est considéré comme potentiellement malveillant
"""

from __future__ import annotations

import tempfile
import os
import time
import ast
from pathlib import Path
from typing import Dict, List, Optional, Union
import logging

from .base import (
    BaseTool,
    ToolResult,
    ToolStatus,
    ToolParamValue,
    ToolSchemaDict,
)

# Import Docker SDK
try:
    import docker
    from docker.errors import DockerException, ContainerError, ImageNotFound

    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False

logger = logging.getLogger(__name__)

# Types stricts pour le sandbox Python
ParameterSchemaValue = Union[str, Dict[str, str], List[str]]
SandboxMetadataValue = Union[str, int, float, bool]


class PythonSandboxTool(BaseTool):
    """
    Outil pour exécuter du code Python en sandbox Docker isolé

    Principes de sécurité Zero Trust:
    - Conteneur éphémère détruit après exécution
    - User non-root (nobody:nogroup / 65534:65534)
    - Réseau désactivé (network_mode='none')
    - Limites strictes: 512MB RAM, 0.5 CPU
    - Timeout 5 secondes
    - Pas d'accès au système hôte (volume temporaire read-only uniquement)
    - Filesystem read-only avec petit tmpfs
    - Toutes les Linux capabilities retirées
    - Pas d'escalade de privilèges
    - Double validation: AST parsing + Docker isolation
    """

    def __init__(
        self, dangerous_patterns: Optional[List[str]] = None, docker_image: str = "python:3.12-slim"
    ) -> None:
        super().__init__(
            name="python_sandbox",
            description="Exécuter du code Python de manière sécurisée dans un conteneur Docker isolé",
        )

        # Configuration Docker
        self.docker_image = docker_image
        self.max_memory_mb = 512
        self.cpu_quota = 50000  # 0.5 CPU (50% d'un core)
        self.cpu_period = 100000  # Période standard
        self.timeout = 5  # secondes (réduit à 5s pour sécurité)

        # Vérifier disponibilité Docker
        if not DOCKER_AVAILABLE:
            logger.error("Docker SDK not available. Install with: pip install docker")
            raise RuntimeError("Docker SDK is required for PythonSandboxTool")

        # Initialiser le client Docker
        try:
            self.docker_client = docker.from_env()
            # Vérifier que Docker daemon est accessible
            self.docker_client.ping()
        except DockerException as e:
            logger.error(f"Failed to connect to Docker daemon: {e}")
            raise RuntimeError(f"Docker daemon not accessible: {e}")

        # Patterns dangereux configurables (pour double validation)
        if dangerous_patterns is None:
            patterns = [
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
            # Pre-compute lowercased patterns for performance
            self.dangerous_patterns = patterns
            self.dangerous_patterns_lower = [p.lower() for p in patterns]
        else:
            self.dangerous_patterns = dangerous_patterns
            self.dangerous_patterns_lower = [p.lower() for p in dangerous_patterns]

        # Essayer de pull l'image si nécessaire
        self._ensure_docker_image()

    def _ensure_docker_image(self) -> None:
        """
        S'assurer que l'image Docker est disponible localement
        Pull l'image si nécessaire
        """
        try:
            self.docker_client.images.get(self.docker_image)
            logger.info(f"Docker image {self.docker_image} already available")
        except ImageNotFound:
            logger.info(f"Pulling Docker image {self.docker_image}...")
            try:
                self.docker_client.images.pull(self.docker_image)
                logger.info(f"Successfully pulled {self.docker_image}")
            except DockerException as e:
                logger.error(f"Failed to pull Docker image: {e}")
                raise RuntimeError(f"Cannot pull Docker image {self.docker_image}: {e}")

    def execute(self, arguments: Dict[str, ToolParamValue]) -> ToolResult:
        """
        Exécuter le code Python dans un conteneur Docker isolé

        Sécurité Zero Trust:
        - Conteneur éphémère créé et détruit pour chaque exécution
        - User non-root
        - Pas de réseau
        - Limites strictes CPU/RAM
        - Timeout 5s
        """
        # Valider les arguments
        is_valid, error = self.validate_arguments(arguments)
        if not is_valid:
            return ToolResult(
                status=ToolStatus.ERROR, output="", error=f"Invalid arguments: {error}"
            )

        code = str(arguments["code"])

        # Créer un répertoire temporaire pour l'exécution
        temp_dir = None
        container = None

        try:
            temp_dir = tempfile.mkdtemp(prefix="sandbox_")
            code_file = Path(temp_dir) / "code.py"

            # Écrire le code dans le fichier
            code_file.write_text(code)

            # Rendre le fichier lisible par tous (nécessaire pour l'user nobody)
            os.chmod(code_file, 0o644)
            os.chmod(temp_dir, 0o755)

            # Mesurer le temps d'exécution
            start_time = time.time()

            # Configuration du conteneur Docker
            container_config = {
                "image": self.docker_image,
                "command": ["python3", "/workspace/code.py"],
                "volumes": {
                    temp_dir: {
                        "bind": "/workspace",
                        "mode": "ro",  # Read-only pour éviter modifications
                    }
                },
                "working_dir": "/workspace",
                "network_mode": "none",  # Pas de réseau
                "mem_limit": f"{self.max_memory_mb}m",  # Limite RAM
                "cpu_quota": self.cpu_quota,  # Limite CPU
                "cpu_period": self.cpu_period,
                "detach": True,  # Detached mode for manual wait control
                "user": "65534:65534",  # User non-root (nobody:nogroup)
                "environment": {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1"},
                # Restrictions supplémentaires
                "cap_drop": ["ALL"],  # Retirer toutes les capabilities
                "security_opt": ["no-new-privileges"],  # Empêcher escalade de privilèges
                "read_only": True,  # Filesystem read-only
                "tmpfs": {"/tmp": "size=10m,mode=1777"},  # Petit tmpfs pour /tmp si besoin
            }

            try:
                # Créer et démarrer le conteneur en mode détaché pour contrôle manuel
                container = self.docker_client.containers.run(**container_config)

                # Attendre que le conteneur se termine avec un timeout
                try:
                    exit_code = container.wait(timeout=self.timeout)

                    # Récupérer les logs
                    output = container.logs().decode("utf-8")

                    elapsed_time = time.time() - start_time

                    # Nettoyer le conteneur
                    try:
                        container.remove(force=True)
                    except Exception:
                        pass

                    # Extraire le code de sortie (Docker SDK retourne un dict avec 'StatusCode')
                    if isinstance(exit_code, dict):
                        status_code = exit_code.get("StatusCode", 0)
                    elif isinstance(exit_code, int):
                        status_code = exit_code
                    else:
                        status_code = 0

                    if status_code == 0:
                        # Succès
                        if not output.strip():
                            output = "[Code exécuté avec succès, pas de sortie]"

                        return ToolResult(
                            status=ToolStatus.SUCCESS,
                            output=output,
                            metadata={
                                "elapsed_time": elapsed_time,
                                "timeout": False,
                                "isolation": "docker",
                                "memory_limit_mb": self.max_memory_mb,
                            },
                        )
                    else:
                        # Erreur d'exécution
                        return ToolResult(
                            status=ToolStatus.ERROR,
                            output="",
                            error=f"Container execution failed: {output}",
                            metadata={"exit_code": status_code, "elapsed_time": elapsed_time},
                        )

                except Exception as wait_error:
                    # Timeout ou erreur durant l'attente
                    elapsed_time = time.time() - start_time

                    # Arrêter et supprimer le conteneur
                    try:
                        container.stop(timeout=1)
                        container.remove(force=True)
                    except Exception:
                        pass

                    # Vérifier si c'est un timeout
                    if "timeout" in str(wait_error).lower() or elapsed_time >= self.timeout:
                        return ToolResult(
                            status=ToolStatus.TIMEOUT,
                            output="",
                            error=f"Execution timeout after {self.timeout}s",
                            metadata={"timeout": True, "elapsed_time": elapsed_time},
                        )
                    else:
                        return ToolResult(
                            status=ToolStatus.ERROR,
                            output="",
                            error=f"Container wait error: {str(wait_error)}",
                            metadata={"elapsed_time": elapsed_time},
                        )

            except ContainerError as e:
                # Erreur d'exécution dans le conteneur
                elapsed_time = time.time() - start_time
                stderr = e.stderr.decode("utf-8") if isinstance(e.stderr, bytes) else str(e.stderr)

                return ToolResult(
                    status=ToolStatus.ERROR,
                    output="",
                    error=f"Container execution failed: {stderr}",
                    metadata={"exit_code": e.exit_status, "elapsed_time": elapsed_time},
                )

            except Exception as e:
                # Autre erreur Docker
                elapsed_time = time.time() - start_time

                return ToolResult(
                    status=ToolStatus.ERROR,
                    output="",
                    error=f"Docker execution error: {str(e)}",
                    metadata={"elapsed_time": elapsed_time},
                )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR, output="", error=f"Failed to execute Python code: {str(e)}"
            )

        finally:
            # Nettoyer le répertoire temporaire
            if temp_dir and os.path.exists(temp_dir):
                try:
                    import shutil

                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"Failed to clean up temp directory {temp_dir}: {e}")

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
            "eval",
            "exec",
            "compile",
            "__import__",
            "open",
            "file",
            "input",
            "raw_input",
            "execfile",
            "reload",
            "vars",
            "globals",
            "locals",
            "dir",
            "getattr",
            "setattr",
            "delattr",
            "hasattr",
            "__builtins__",
            "__dict__",
            "__class__",
            "__bases__",
            "__subclasses__",
        }

        # Modules dangereux
        dangerous_modules = {
            "os",
            "sys",
            "subprocess",
            "multiprocessing",
            "threading",
            "socket",
            "urllib",
            "requests",
            "pickle",
            "shelve",
            "marshal",
            "ctypes",
            "imp",
            "importlib",
            "pty",
            "commands",
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
                        return (
                            False,
                            f"Attribute access to dangerous function blocked: {node.func.attr}",
                        )

            # Bloquer l'accès aux attributs sensibles
            if isinstance(node, ast.Attribute):
                if node.attr in dangerous_names:
                    return False, f"Access to dangerous attribute blocked: {node.attr}"

            # Bloquer l'utilisation de __dict__, __class__, etc.
            if isinstance(node, ast.Name):
                if node.id in dangerous_names:
                    return False, f"Reference to dangerous name blocked: {node.id}"

        return True, None

    def validate_arguments(
        self, arguments: Dict[str, ToolParamValue]
    ) -> tuple[bool, Optional[str]]:
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
        for pattern, pattern_lower in zip(self.dangerous_patterns, self.dangerous_patterns_lower):
            if pattern_lower in code_lower:
                return False, f"Blocked dangerous operation: {pattern}"

        return True, None

    def _get_parameters_schema(self) -> ToolSchemaDict:
        """Schema des parametres"""
        return {
            "type": "object",
            "properties": {"code": {"type": "string", "description": "Code Python a executer"}},
            "required": ["code"],
        }
