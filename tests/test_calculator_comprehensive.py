"""
Comprehensive tests for CalculatorTool

Tests cover:
- Basic arithmetic operations
- Math functions
- Float formatting
- Error handling
- Unsafe expression detection
"""
import pytest
from tools.calculator import CalculatorTool
from tools.base import ToolStatus


@pytest.fixture
def calculator():
    """Create CalculatorTool instance"""
    return CalculatorTool()


class TestBasicOperations:
    """Test basic calculator operations"""

    def test_simple_addition(self, calculator):
        """Test simple addition"""
        result = calculator.execute({"expression": "2 + 2"})

        assert result.status == ToolStatus.SUCCESS
        assert result.output == "4"

    def test_float_result_formatting(self, calculator):
        """Test float result formatting with trailing zeros"""
        result = calculator.execute({"expression": "1.5 + 2.5"})

        assert result.status == ToolStatus.SUCCESS
        # Should format nicely without trailing zeros
        assert result.output == "4"

    def test_float_with_decimals(self, calculator):
        """Test float formatting with actual decimals"""
        result = calculator.execute({"expression": "10 / 3"})

        assert result.status == ToolStatus.SUCCESS
        # Should have decimal places
        assert "3.3" in result.output


class TestArgumentValidation:
    """Test argument validation"""

    def test_missing_expression(self, calculator):
        """Test missing expression argument"""
        result = calculator.execute({})

        assert result.status == ToolStatus.ERROR
        assert "expression" in result.error

    def test_invalid_expression_type(self, calculator):
        """Test non-string expression"""
        result = calculator.execute({"expression": 123})

        assert result.status == ToolStatus.ERROR

    def test_empty_expression(self, calculator):
        """Test empty expression"""
        result = calculator.execute({"expression": ""})

        assert result.status == ToolStatus.ERROR

    def test_expression_too_long(self, calculator):
        """Test expression that is too long"""
        long_expr = "1 + 2 + " * 500  # Over 1000 characters
        result = calculator.execute({"expression": long_expr})

        assert result.status == ToolStatus.ERROR
        assert "too long" in result.error

    def test_arguments_not_dict(self, calculator):
        """Test that non-dict arguments are rejected"""
        is_valid, error = calculator.validate_arguments("not a dict")

        assert is_valid is False
        assert "dictionary" in error


class TestUnsafeExpressionDetection:
    """Test unsafe expression detection"""

    def test_eval_blocked(self, calculator):
        """Test that eval is blocked"""
        result = calculator.execute({"expression": "eval('2+2')"})

        assert result.status == ToolStatus.ERROR
        assert "Unsafe" in result.error or "Failed" in result.error

    def test_exec_blocked(self, calculator):
        """Test that exec is blocked"""
        result = calculator.execute({"expression": "exec('print(1)')"})

        assert result.status == ToolStatus.ERROR

    def test_dunder_blocked(self, calculator):
        """Test that dunder methods are blocked"""
        result = calculator.execute({"expression": "__import__('os')"})

        assert result.status == ToolStatus.ERROR

    def test_import_blocked(self, calculator):
        """Test that import is blocked"""
        result = calculator.execute({"expression": "import os"})

        assert result.status == ToolStatus.ERROR


class TestMathFunctions:
    """Test mathematical functions"""

    def test_sqrt_function(self, calculator):
        """Test square root function"""
        result = calculator.execute({"expression": "sqrt(16)"})

        assert result.status == ToolStatus.SUCCESS
        assert "4" in result.output

    def test_power_operator(self, calculator):
        """Test power operator"""
        result = calculator.execute({"expression": "2 ** 3"})

        assert result.status == ToolStatus.SUCCESS
        assert "8" in result.output

    def test_sin_function(self, calculator):
        """Test sine function"""
        result = calculator.execute({"expression": "sin(0)"})

        assert result.status == ToolStatus.SUCCESS
        assert "0" in result.output


class TestComplexExpressions:
    """Test complex mathematical expressions"""

    def test_complex_arithmetic(self, calculator):
        """Test complex arithmetic expression"""
        result = calculator.execute({"expression": "(10 + 5) * 2 - 8"})

        assert result.status == ToolStatus.SUCCESS
        assert result.output == "22"

    def test_division_by_zero(self, calculator):
        """Test division by zero handling"""
        result = calculator.execute({"expression": "10 / 0"})

        assert result.status == ToolStatus.ERROR


class TestMetadata:
    """Test metadata in results"""

    def test_metadata_contains_expression(self, calculator):
        """Test that metadata contains original expression"""
        result = calculator.execute({"expression": "2 + 2"})

        assert result.status == ToolStatus.SUCCESS
        assert "expression" in result.metadata
        assert result.metadata["expression"] == "2 + 2"

    def test_metadata_contains_result(self, calculator):
        """Test that metadata contains result"""
        result = calculator.execute({"expression": "5 + 3"})

        assert result.status == ToolStatus.SUCCESS
        assert "result" in result.metadata
        assert result.metadata["result"] == 8

    def test_metadata_contains_result_type(self, calculator):
        """Test that metadata contains result type"""
        result = calculator.execute({"expression": "10"})

        assert result.status == ToolStatus.SUCCESS
        assert "result_type" in result.metadata


class TestAstNameRestrictions:
    """Test that ast.Name is restricted to constants only (Issue #178)"""

    def test_bare_sqrt_rejected(self, calculator):
        """Test that bare function name 'sqrt' is rejected"""
        result = calculator.execute({"expression": "sqrt"})

        assert result.status == ToolStatus.ERROR
        assert "Nom non autorisé: sqrt" in result.error

    def test_bare_sin_rejected(self, calculator):
        """Test that bare function name 'sin' is rejected"""
        result = calculator.execute({"expression": "sin"})

        assert result.status == ToolStatus.ERROR
        assert "Nom non autorisé: sin" in result.error

    def test_bare_cos_rejected(self, calculator):
        """Test that bare function name 'cos' is rejected"""
        result = calculator.execute({"expression": "cos"})

        assert result.status == ToolStatus.ERROR
        assert "Nom non autorisé: cos" in result.error

    def test_bare_abs_rejected(self, calculator):
        """Test that bare function name 'abs' is rejected"""
        result = calculator.execute({"expression": "abs"})

        assert result.status == ToolStatus.ERROR
        assert "Nom non autorisé: abs" in result.error

    def test_constant_pi_allowed(self, calculator):
        """Test that constant 'pi' is still allowed"""
        result = calculator.execute({"expression": "pi"})

        assert result.status == ToolStatus.SUCCESS
        assert "3.14" in result.output

    def test_constant_e_allowed(self, calculator):
        """Test that constant 'e' is still allowed"""
        result = calculator.execute({"expression": "e"})

        assert result.status == ToolStatus.SUCCESS
        assert "2.71" in result.output

    def test_pi_in_expression(self, calculator):
        """Test that pi works in mathematical expressions"""
        result = calculator.execute({"expression": "2 * pi"})

        assert result.status == ToolStatus.SUCCESS
        assert "6.28" in result.output

    def test_e_in_expression(self, calculator):
        """Test that e works in mathematical expressions"""
        result = calculator.execute({"expression": "e ** 2"})

        assert result.status == ToolStatus.SUCCESS
        # e^2 ≈ 7.389
        assert "7.38" in result.output or "7.39" in result.output

    def test_function_calls_still_work(self, calculator):
        """Test that function calls (not bare names) still work"""
        result = calculator.execute({"expression": "sqrt(16)"})

        assert result.status == ToolStatus.SUCCESS
        assert "4" in result.output

    def test_nested_function_calls_work(self, calculator):
        """Test that nested function calls still work"""
        result = calculator.execute({"expression": "sqrt(abs(-16))"})

        assert result.status == ToolStatus.SUCCESS
        assert "4" in result.output
