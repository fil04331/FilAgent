"""
Tests pour les outils
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.base import ToolResult, ToolStatus
from tools.python_sandbox import PythonSandboxTool
from tools.calculator import CalculatorTool
from tools.file_reader import FileReaderTool


def test_python_sandbox_basic():
    """Test basique du sandbox Python"""
    tool = PythonSandboxTool()

    # Test exécution simple
    result = tool.execute({"code": "print('Hello World')"})

    assert result.is_success()
    assert "Hello World" in result.output


def test_python_sandbox_calculation():
    """Test avec un calcul"""
    tool = PythonSandboxTool()

    result = tool.execute({"code": "x = 5\nprint(x * 2)"})

    assert result.is_success()
    assert "10" in result.output


def test_python_sandbox_blocked():
    """Test qu'un code dangereux est bloqué"""
    tool = PythonSandboxTool()

    # Code avec import dangereux
    result = tool.execute({"code": "import os\nprint('test')"})

    assert not result.is_success()
    assert result.status == ToolStatus.ERROR or result.status == ToolStatus.BLOCKED


def test_calculator_basic():
    """Test basique du calculateur"""
    tool = CalculatorTool()

    result = tool.execute({"expression": "2 + 2"})

    assert result.is_success()
    assert "4" in result.output


def test_calculator_functions():
    """Test avec fonctions mathématiques"""
    tool = CalculatorTool()

    result = tool.execute({"expression": "sqrt(16)"})

    assert result.is_success()


def test_calculator_invalid():
    """Test avec expression invalide"""
    tool = CalculatorTool()

    result = tool.execute({"expression": "invalid syntax"})

    # Peut réussir ou échouer selon l'implémentation
    # On vérifie juste qu'il n'y a pas de crash
    assert result is not None


def test_file_reader_schema():
    """Test du schéma du file reader"""
    tool = FileReaderTool()

    schema = tool.get_schema()

    assert schema["name"] == "file_read"
    assert "parameters" in schema
