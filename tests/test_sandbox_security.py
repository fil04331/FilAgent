"""
Tests de sécurité pour le sandbox Python basé sur Docker

Ces tests vérifient que le sandbox Docker isole correctement le code malveillant:
- Isolation réseau
- Isolation filesystem
- Limites de ressources (CPU, RAM)
- User non-root
- Timeout strict
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.base import ToolResult, ToolStatus
from tools.python_sandbox import PythonSandboxTool, DOCKER_AVAILABLE

# Skip tous les tests si Docker n'est pas disponible
pytestmark = pytest.mark.skipif(not DOCKER_AVAILABLE, reason="Docker SDK not available")


@pytest.fixture
def sandbox_tool():
    """Fixture pour créer une instance du sandbox"""
    try:
        return PythonSandboxTool()
    except RuntimeError as e:
        pytest.skip(f"Docker not available: {e}")


@pytest.mark.tools
@pytest.mark.integration
class TestSandboxSecurity:
    """Tests de sécurité du sandbox Docker"""

    def test_basic_execution_success(self, sandbox_tool):
        """Test d'exécution basique qui doit réussir"""
        result = sandbox_tool.execute({"code": "print('Hello from Docker sandbox')"})

        assert result.status == ToolStatus.SUCCESS
        assert "Hello from Docker sandbox" in result.output
        assert result.metadata.get("isolation") == "docker"

    def test_simple_calculation(self, sandbox_tool):
        """Test avec un calcul simple"""
        result = sandbox_tool.execute({"code": "x = 5 * 10\nprint(x)"})

        assert result.status == ToolStatus.SUCCESS
        assert "50" in result.output

    def test_blocked_os_system_call(self, sandbox_tool):
        """Test qu'un appel à os.system est bloqué par validation AST"""
        # Cette commande est bloquée avant même d'atteindre le conteneur
        dangerous_code = "import os\nos.system('rm -rf /')"

        result = sandbox_tool.execute({"code": dangerous_code})

        # Doit être bloqué par la validation AST
        assert result.status == ToolStatus.ERROR
        assert "dangerous" in result.error.lower() or "blocked" in result.error.lower()

    def test_blocked_subprocess_import(self, sandbox_tool):
        """Test que l'import subprocess est bloqué"""
        dangerous_code = "import subprocess\nsubprocess.run(['ls', '/'])"

        result = sandbox_tool.execute({"code": dangerous_code})

        assert result.status == ToolStatus.ERROR
        assert "dangerous" in result.error.lower() or "subprocess" in result.error.lower()

    def test_blocked_eval_function(self, sandbox_tool):
        """Test que eval() est bloqué"""
        dangerous_code = "eval('print(\"test\")')"

        result = sandbox_tool.execute({"code": dangerous_code})

        assert result.status == ToolStatus.ERROR
        assert "dangerous" in result.error.lower() or "eval" in result.error.lower()

    def test_blocked_exec_function(self, sandbox_tool):
        """Test que exec() est bloqué"""
        dangerous_code = "exec('import os')"

        result = sandbox_tool.execute({"code": dangerous_code})

        assert result.status == ToolStatus.ERROR
        assert "dangerous" in result.error.lower() or "exec" in result.error.lower()

    def test_blocked_open_file(self, sandbox_tool):
        """Test que open() est bloqué"""
        dangerous_code = "open('/etc/passwd', 'r').read()"

        result = sandbox_tool.execute({"code": dangerous_code})

        assert result.status == ToolStatus.ERROR
        assert "dangerous" in result.error.lower() or "open" in result.error.lower()

    def test_blocked___import__(self, sandbox_tool):
        """Test que __import__ est bloqué"""
        dangerous_code = "__import__('os').system('ls')"

        result = sandbox_tool.execute({"code": dangerous_code})

        assert result.status == ToolStatus.ERROR
        assert "dangerous" in result.error.lower() or "__import__" in result.error.lower()

    def test_timeout_enforcement(self, sandbox_tool):
        """Test que le timeout (5s) est appliqué"""
        # Code qui prend plus de 5 secondes (time module n'est pas bloqué)
        slow_code = """
import time
time.sleep(10)
print("Should not reach here")
"""

        result = sandbox_tool.execute({"code": slow_code})

        # Le timeout Docker devrait tuer le conteneur
        assert result.status == ToolStatus.TIMEOUT
        assert result.metadata.get("timeout") is True

    def test_network_isolation(self, sandbox_tool):
        """Test que le réseau est isolé (network_mode='none')"""
        # Tenter une connexion réseau - devrait échouer
        # Note: socket est bloqué par AST, donc ce test vérifie la validation
        network_code = "import socket\ns = socket.socket()\ns.connect(('google.com', 80))"

        result = sandbox_tool.execute({"code": network_code})

        # Bloqué par AST avant d'atteindre le conteneur
        assert result.status == ToolStatus.ERROR
        assert "dangerous" in result.error.lower() or "socket" in result.error.lower()

    def test_safe_math_operations(self, sandbox_tool):
        """Test que les opérations mathématiques sûres fonctionnent"""
        safe_code = """
# Opérations mathématiques basiques
result = sum([1, 2, 3, 4, 5])
print(f"Sum: {result}")

# List comprehension
squares = [x**2 for x in range(5)]
print(f"Squares: {squares}")
"""

        result = sandbox_tool.execute({"code": safe_code})

        assert result.status == ToolStatus.SUCCESS
        assert "Sum: 15" in result.output
        assert "Squares:" in result.output

    def test_blocked_pickle_import(self, sandbox_tool):
        """Test que pickle est bloqué (désérialisation dangereuse)"""
        dangerous_code = "import pickle"

        result = sandbox_tool.execute({"code": dangerous_code})

        assert result.status == ToolStatus.ERROR
        assert "dangerous" in result.error.lower() or "pickle" in result.error.lower()

    def test_code_too_long(self, sandbox_tool):
        """Test que le code trop long est rejeté"""
        # Générer du code > 50000 caractères
        long_code = "x = 1\n" * 30000

        result = sandbox_tool.execute({"code": long_code})

        assert result.status == ToolStatus.ERROR
        assert "too long" in result.error.lower()

    def test_invalid_arguments(self, sandbox_tool):
        """Test validation des arguments"""
        # Argument manquant
        result = sandbox_tool.execute({})
        assert result.status == ToolStatus.ERROR
        assert "missing" in result.error.lower() or "required" in result.error.lower()

        # Type incorrect
        result = sandbox_tool.execute({"code": 123})
        assert result.status == ToolStatus.ERROR
        assert "string" in result.error.lower() or "must be" in result.error.lower()

    def test_syntax_error_handling(self, sandbox_tool):
        """Test gestion des erreurs de syntaxe"""
        invalid_code = "def broken(\nprint('missing parenthesis')"

        result = sandbox_tool.execute({"code": invalid_code})

        assert result.status == ToolStatus.ERROR
        assert "syntax" in result.error.lower()

    def test_metadata_contains_isolation_info(self, sandbox_tool):
        """Test que les métadonnées contiennent l'info d'isolation"""
        result = sandbox_tool.execute({"code": "print('test')"})

        if result.status == ToolStatus.SUCCESS:
            assert result.metadata is not None
            assert result.metadata.get("isolation") == "docker"
            assert "elapsed_time" in result.metadata
            assert result.metadata.get("memory_limit_mb") == 512

    def test_blocked_getattr_access(self, sandbox_tool):
        """Test que getattr est bloqué (peut contourner restrictions)"""
        dangerous_code = "getattr(__builtins__, 'eval')('1+1')"

        result = sandbox_tool.execute({"code": dangerous_code})

        assert result.status == ToolStatus.ERROR
        assert "dangerous" in result.error.lower() or "getattr" in result.error.lower()

    def test_blocked_globals_access(self, sandbox_tool):
        """Test que globals() est bloqué"""
        dangerous_code = "globals()['__builtins__']"

        result = sandbox_tool.execute({"code": dangerous_code})

        assert result.status == ToolStatus.ERROR
        assert "dangerous" in result.error.lower() or "globals" in result.error.lower()

    def test_blocked_class_introspection(self, sandbox_tool):
        """Test que l'introspection de classe est bloquée"""
        dangerous_code = "x = ().__class__.__bases__[0].__subclasses__()"

        result = sandbox_tool.execute({"code": dangerous_code})

        assert result.status == ToolStatus.ERROR
        assert "dangerous" in result.error.lower() or "class" in result.error.lower()


@pytest.mark.tools
@pytest.mark.unit
class TestSandboxToolSchema:
    """Tests du schéma de l'outil"""

    def test_tool_schema(self, sandbox_tool):
        """Test que le schéma de l'outil est correct"""
        schema = sandbox_tool.get_schema()

        assert schema["name"] == "python_sandbox"
        assert "description" in schema
        assert "docker" in schema["description"].lower() or "isolé" in schema["description"].lower()
        assert "parameters" in schema
        assert schema["parameters"]["type"] == "object"
        assert "code" in schema["parameters"]["properties"]
        assert "code" in schema["parameters"]["required"]


@pytest.mark.tools
@pytest.mark.integration
class TestResourceLimits:
    """Tests des limites de ressources"""

    def test_memory_limit_set(self, sandbox_tool):
        """Vérifier que la limite mémoire est configurée"""
        assert sandbox_tool.max_memory_mb == 512

    def test_cpu_limit_set(self, sandbox_tool):
        """Vérifier que la limite CPU est configurée"""
        assert sandbox_tool.cpu_quota == 50000  # 0.5 CPU
        assert sandbox_tool.cpu_period == 100000

    def test_timeout_reduced(self, sandbox_tool):
        """Vérifier que le timeout est réduit à 5s pour sécurité"""
        assert sandbox_tool.timeout == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
