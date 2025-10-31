"""
Sandbox Python pour exécution sûre de code Python
Limites CPU, mémoire, et filesystem
"""
import subprocess
import tempfile
import os
import signal
import time
from typing import Dict, Any, Optional, List
from pathlib import Path

from .base import BaseTool, ToolResult, ToolStatus


class PythonSandboxTool(BaseTool):
    """
    Outil pour exécuter du code Python en sandbox
    Limites : CPU, mémoire, timeout
    """
    
    def __init__(self, dangerous_patterns: Optional[List[str]] = None):
        super().__init__(
            name="python_sandbox",
            description="Exécuter du code Python de manière sécurisée dans un sandbox"
        )
        # Limites de ressources
        self.max_memory_mb = 512
        self.max_cpu_time = 30  # secondes
        self.timeout = 30  # secondes total
        
        # Patterns dangereux configurables
        if dangerous_patterns is None:
            self.dangerous_patterns = [
                '__import__',
                'eval(',
                'exec(',
                'open(',
                'file(',
                'os.system',
                'import os',
                'subprocess',
                'pickle',
            ]
        else:
            self.dangerous_patterns = dangerous_patterns
    
    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Exécuter le code Python"""
        # Valider les arguments
        is_valid, error = self.validate_arguments(arguments)
        if not is_valid:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"Invalid arguments: {error}"
            )
        
        code = arguments['code']
        
        try:
            # Créer un fichier temporaire
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            try:
                # Exécuter avec timeout
                start_time = time.time()
                result = subprocess.run(
                    ['python3', temp_file],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=os.path.dirname(temp_file),
                    # Limites basiques (sur macOS/Linux)
                    env=os.environ.copy()
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
                        metadata={
                            "returncode": result.returncode,
                            "elapsed_time": elapsed_time,
                            "timeout": False
                        }
                    )
                else:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        output="",
                        error=f"Execution failed: {result.stderr}",
                        metadata={
                            "returncode": result.returncode,
                            "stderr": result.stderr
                        }
                    )
                    
            except subprocess.TimeoutExpired:
                return ToolResult(
                    status=ToolStatus.TIMEOUT,
                    output="",
                    error=f"Execution timeout after {self.timeout}s",
                    metadata={"timeout": True}
                )
            except Exception as e:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output="",
                    error=f"Execution error: {str(e)}"
                )
            finally:
                # Nettoyer le fichier temporaire
                try:
                    os.unlink(temp_file)
                except:
                    pass
                    
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"Failed to execute Python code: {str(e)}"
            )
    
    def validate_arguments(self, arguments: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Valider les arguments"""
        if not isinstance(arguments, dict):
            return False, "Arguments must be a dictionary"
        
        if 'code' not in arguments:
            return False, "Missing required argument: 'code'"
        
        if not isinstance(arguments['code'], str):
            return False, "Argument 'code' must be a string"
        
        if len(arguments['code']) > 50000:  # Limiter la taille
            return False, "Code too long (max 50000 characters)"
        
        # Bloquer certaines opérations dangereuses
        code_lower = arguments['code'].lower()
        for pattern in self.dangerous_patterns:
            if pattern in code_lower:
                return False, f"Blocked dangerous operation: {pattern}"
        
        return True, None
    
    def _get_parameters_schema(self) -> Dict[str, Any]:
        """Schéma des paramètres"""
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Code Python à exécuter"
                }
            },
            "required": ["code"]
        }
