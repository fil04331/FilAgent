"""
Calculateur mathématique securise
Evalue des expressions mathematiques sans risque d'execution arbitraire
"""

from __future__ import annotations

import math
import operator
from typing import Callable, Dict, List, Optional, Union
import ast  # For safe expression evaluation

from .base import BaseTool, ToolResult, ToolStatus, ToolParamValue, ToolMetadataValue, ToolSchemaDict

# Types stricts pour le calculateur
MathOperation = Callable[[float, float], float]
MathFunction = Callable[..., float]
MathConstant = float
SafeFunctionValue = Union[MathFunction, MathConstant]
CalculatorMetadataValue = Union[str, int, float, bool]
ParameterSchemaValue = Union[str, Dict[str, str], List[str]]


class CalculatorTool(BaseTool):
    """
    Outil pour evaluer des expressions mathematiques
    Utilise seulement des operations mathematiques sures
    """

    safe_operations: Dict[str, MathOperation]
    safe_functions: Dict[str, SafeFunctionValue]

    def __init__(self) -> None:
        super().__init__(
            name="math_calculator", description="Evaluer des expressions mathematiques de maniere securisee"
        )

        # Operations autorisees
        self.safe_operations = {
            "+": operator.add,
            "-": operator.sub,
            "*": operator.mul,
            "/": operator.truediv,
            "//": operator.floordiv,
            "%": operator.mod,
            "**": operator.pow,
            "==": operator.eq,
            "!=": operator.ne,
            "<": operator.lt,
            "<=": operator.le,
            ">": operator.gt,
            ">=": operator.ge,
        }

        # Fonctions mathematiques autorisees
        self.safe_functions = {
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "sqrt": math.sqrt,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "log": math.log,
            "exp": math.exp,
            "pi": math.pi,
            "e": math.e,
        }

    def execute(self, arguments: Dict[str, ToolParamValue]) -> ToolResult:
        """Evaluer l'expression"""
        # Valider les arguments
        is_valid, error = self.validate_arguments(arguments)
        if not is_valid:
            return ToolResult(status=ToolStatus.ERROR, output="", error=f"Invalid arguments: {error}")

        expression = str(arguments["expression"])

        try:
            # Evaluer de maniere sure
            result = self._safe_eval(expression)

            # Convertir le resultat en string
            if isinstance(result, float):
                # Arrondir pour les floats proches d'entiers
                if abs(result - round(result)) < 1e-10:
                    result_str = str(int(round(result)))
                else:
                    result_str = f"{result:.10f}".rstrip("0").rstrip(".")
            else:
                result_str = str(result)

            metadata: Dict[str, ToolMetadataValue] = {
                "expression": expression,
                "result": float(result) if isinstance(result, (int, float)) else str(result),
                "result_type": type(result).__name__,
            }

            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=result_str,
                metadata=metadata,
            )

        except ValueError as e:
            return ToolResult(status=ToolStatus.ERROR, output="", error=f"Failed to evaluate expression: {str(e)}")
        except ZeroDivisionError:
            return ToolResult(status=ToolStatus.ERROR, output="", error="Division by zero")
        except OverflowError:
            return ToolResult(status=ToolStatus.ERROR, output="", error="Numeric overflow")

    def _safe_eval(self, expression: str) -> Union[int, float, bool]:
        """
        Evaluer de maniere SECURISEE sans utiliser eval()
        Utilise ast pour parser et evaluer des expressions mathematiques simples.
        Possibilites : nombres, operations arithmetiques, appels de fonctions sures.
        """
        # Autoriser uniquement les noms surs (fonctions et constantes)
        allowed_names: Dict[str, SafeFunctionValue] = {**self.safe_functions}
        allowed_func_names: set[str] = set(self.safe_functions.keys())
        allowed_ops = (
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.USub, ast.UAdd
        )

        # Parse l'expression en AST
        try:
            node = ast.parse(expression.strip(), mode='eval')
        except SyntaxError as exc:
            raise ValueError("Expression non valide") from exc

        def _eval(node: ast.AST) -> Union[int, float, bool]:
            if isinstance(node, ast.Expression):
                return _eval(node.body)
            elif isinstance(node, ast.Num):  # Python <=3.7
                if isinstance(node.n, (int, float)):
                    return node.n
                raise ValueError("Nombre non autorisé")
            elif isinstance(node, ast.Constant):  # Python >=3.8
                if isinstance(node.value, (int, float)):
                    return node.value
                else:
                    raise ValueError("Constante non autorisée")
            elif isinstance(node, ast.BinOp):
                if not isinstance(node.op, allowed_ops):
                    raise ValueError("Opérateur non autorisé")
                left = _eval(node.left)
                right = _eval(node.right)
                if isinstance(node.op, ast.Add):
                    return left + right
                elif isinstance(node.op, ast.Sub):
                    return left - right
                elif isinstance(node.op, ast.Mult):
                    return left * right
                elif isinstance(node.op, ast.Div):
                    return left / right
                elif isinstance(node.op, ast.Pow):
                    return left ** right
                elif isinstance(node.op, ast.Mod):
                    return left % right
            elif isinstance(node, ast.UnaryOp):
                if not isinstance(node.op, allowed_ops):
                    raise ValueError("Opérateur unaire non autorisé")
                operand = _eval(node.operand)
                if isinstance(node.op, ast.USub):
                    return -operand
                elif isinstance(node.op, ast.UAdd):
                    return +operand
            elif isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name):
                    raise ValueError("Appel de fonction non autorisé")
                func_name = node.func.id
                if func_name not in allowed_func_names:
                    raise ValueError(f"Fonction non autorisée: {func_name}")
                func = allowed_names[func_name]
                if not callable(func):
                    raise ValueError(f"Fonction non appelable: {func_name}")
                args = [_eval(arg) for arg in node.args]
                result = func(*args)
                if isinstance(result, (int, float)):
                    return result
                raise ValueError(f"Résultat non numérique: {func_name}")
            elif isinstance(node, ast.Name):
                name = node.id
                if name not in {'pi', 'e'}:
                    raise ValueError(f"Nom non autorisé: {name}")
                if name not in allowed_names:
                    raise ValueError(f"Constante non disponible: {name}")
                const_val = allowed_names[name]
                if isinstance(const_val, (int, float)):
                    return const_val
                raise ValueError(f"Constante non numérique: {name}")
            elif isinstance(node, ast.Compare):
                # Only allow single comparisons (no chaining)
                if len(node.ops) != 1 or len(node.comparators) != 1:
                    raise ValueError("Comparaisons multiples non autorisées")
                allowed_cmp_ops = (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)
                op = node.ops[0]
                if not isinstance(op, allowed_cmp_ops):
                    raise ValueError("Opérateur de comparaison non autorisé")
                left = _eval(node.left)
                right = _eval(node.comparators[0])
                if isinstance(op, ast.Eq):
                    return left == right
                elif isinstance(op, ast.NotEq):
                    return left != right
                elif isinstance(op, ast.Lt):
                    return left < right
                elif isinstance(op, ast.LtE):
                    return left <= right
                elif isinstance(op, ast.Gt):
                    return left > right
                elif isinstance(op, ast.GtE):
                    return left >= right
                else:
                    raise ValueError("Opérateur de comparaison non autorisé")
            else:
                raise ValueError("Expression non autorisée")

        return _eval(node)
    def validate_arguments(self, arguments: Dict[str, ToolParamValue]) -> tuple[bool, Optional[str]]:
        """Valider les arguments"""
        if not isinstance(arguments, dict):
            return False, "Arguments must be a dictionary"

        if "expression" not in arguments:
            return False, "Missing required argument: 'expression'"

        if not isinstance(arguments["expression"], str):
            return False, "Argument 'expression' must be a string"

        if len(arguments["expression"]) > 1000:
            return False, "Expression too long (max 1000 characters)"

        return True, None

    def _get_parameters_schema(self) -> ToolSchemaDict:
        """Schema des parametres"""
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Expression mathematique a evaluer (ex: '2 + 3 * 4', 'sqrt(16)')",
                }
            },
            "required": ["expression"],
        }
