"""
Additional tests for Calculator AST validation coverage
Targets uncovered branches in tools/calculator.py lines 159-185

Tests cover:
- Comparison operations (==, !=, <, <=, >, >=)
- ast.Name validation with unauthorized names
- Multiple comparisons (chained comparisons)
- Edge cases in AST evaluation
"""

import pytest
from tools.calculator import CalculatorTool
from tools.base import ToolStatus


@pytest.fixture
def calculator():
    """Create CalculatorTool instance"""
    return CalculatorTool()


class TestComparisonOperations:
    """Test comparison operations in AST evaluation"""

    def test_equality_comparison(self, calculator):
        """Test equality comparison (==)"""
        result = calculator.execute({"expression": "5 == 5"})

        assert result.status == ToolStatus.SUCCESS
        assert result.output == "True"

    def test_inequality_comparison(self, calculator):
        """Test inequality comparison (!=)"""
        result = calculator.execute({"expression": "5 != 3"})

        assert result.status == ToolStatus.SUCCESS
        assert result.output == "True"

    def test_less_than_comparison(self, calculator):
        """Test less than comparison (<)"""
        result = calculator.execute({"expression": "3 < 5"})

        assert result.status == ToolStatus.SUCCESS
        assert result.output == "True"

    def test_less_than_or_equal_comparison(self, calculator):
        """Test less than or equal comparison (<=)"""
        result = calculator.execute({"expression": "5 <= 5"})

        assert result.status == ToolStatus.SUCCESS
        assert result.output == "True"

    def test_greater_than_comparison(self, calculator):
        """Test greater than comparison (>)"""
        result = calculator.execute({"expression": "7 > 3"})

        assert result.status == ToolStatus.SUCCESS
        assert result.output == "True"

    def test_greater_than_or_equal_comparison(self, calculator):
        """Test greater than or equal comparison (>=)"""
        result = calculator.execute({"expression": "5 >= 5"})

        assert result.status == ToolStatus.SUCCESS
        assert result.output == "True"

    def test_comparison_false_result(self, calculator):
        """Test comparison that evaluates to False"""
        result = calculator.execute({"expression": "5 > 10"})

        assert result.status == ToolStatus.SUCCESS
        assert result.output == "False"


class TestConstantValidation:
    """Test validation of constants"""

    def test_valid_constant_pi(self, calculator):
        """Test that pi constant is allowed"""
        result = calculator.execute({"expression": "pi"})

        assert result.status == ToolStatus.SUCCESS
        # Should return value of pi
        assert "3.14" in result.output

    def test_valid_constant_e(self, calculator):
        """Test that e constant is allowed"""
        result = calculator.execute({"expression": "e"})

        assert result.status == ToolStatus.SUCCESS
        # Should return value of e
        assert "2.71" in result.output

    def test_unauthorized_name(self, calculator):
        """Test that unauthorized variable names are blocked"""
        result = calculator.execute({"expression": "x"})

        assert result.status == ToolStatus.ERROR
        assert "non autorisé" in result.error or "non autorisée" in result.error


class TestChainedComparisons:
    """Test validation of chained/multiple comparisons"""

    def test_chained_comparison_blocked(self, calculator):
        """Test that chained comparisons are blocked (security)"""
        # Expression like "1 < 2 < 3" should be blocked
        result = calculator.execute({"expression": "1 < 2 < 3"})

        assert result.status == ToolStatus.ERROR
        # Should contain error about multiple comparisons
        assert "Comparaisons multiples" in result.error or "non autorisé" in result.error


class TestFloordivOperator:
    """Test floor division operator"""

    def test_floordiv_operation_blocked(self, calculator):
        """Test floor division (//) is blocked for security"""
        result = calculator.execute({"expression": "10 // 3"})

        # Floor division is not in allowed operators for security
        assert result.status == ToolStatus.ERROR
        assert "non autorisé" in result.error


class TestModuloOperator:
    """Test modulo operator"""

    def test_modulo_operation(self, calculator):
        """Test modulo (%)"""
        result = calculator.execute({"expression": "10 % 3"})

        assert result.status == ToolStatus.SUCCESS
        assert result.output == "1"


class TestNonConstantAST:
    """Test ast.Constant with non-numeric values"""

    def test_string_constant_blocked(self, calculator):
        """Test that string constants are blocked"""
        # Try to evaluate a string (should be blocked)
        result = calculator.execute({"expression": "'hello'"})

        assert result.status == ToolStatus.ERROR
        # Should contain error about unauthorized constant
        assert "Constante non autorisée" in result.error or "non autorisé" in result.error


class TestComplexExpressions:
    """Test complex expressions with multiple operations"""

    def test_comparison_with_arithmetic(self, calculator):
        """Test comparison combined with arithmetic"""
        result = calculator.execute({"expression": "(2 + 3) > 4"})

        assert result.status == ToolStatus.SUCCESS
        assert result.output == "True"

    def test_function_in_comparison(self, calculator):
        """Test function call in comparison"""
        result = calculator.execute({"expression": "abs(-5) == 5"})

        assert result.status == ToolStatus.SUCCESS
        assert result.output == "True"

    def test_nested_comparisons(self, calculator):
        """Test comparisons with nested expressions"""
        result = calculator.execute({"expression": "(10 / 2) >= 5"})

        assert result.status == ToolStatus.SUCCESS
        assert result.output == "True"


class TestBooleanResults:
    """Test that boolean results are properly formatted"""

    def test_true_boolean_output(self, calculator):
        """Test that True is properly formatted"""
        result = calculator.execute({"expression": "1 == 1"})

        assert result.status == ToolStatus.SUCCESS
        assert result.output == "True"
        assert isinstance(result.metadata.get("result"), bool)

    def test_false_boolean_output(self, calculator):
        """Test that False is properly formatted"""
        result = calculator.execute({"expression": "1 == 2"})

        assert result.status == ToolStatus.SUCCESS
        assert result.output == "False"
        assert isinstance(result.metadata.get("result"), bool)


class TestUnauthorizedFunctions:
    """Test that unauthorized functions are blocked"""

    def test_unauthorized_function_call(self, calculator):
        """Test that functions not in safe list are blocked"""
        result = calculator.execute({"expression": "print('test')"})

        assert result.status == ToolStatus.ERROR
        assert "Fonction non autorisée" in result.error or "non autorisé" in result.error
