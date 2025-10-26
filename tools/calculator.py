"""
Calculateur mathématique sécurisé
Évalue des expressions mathématiques sans risque d'exécution arbitraire
"""
import math
import operator
from typing import Dict, Any, Optional
import re

from .base import BaseTool, ToolResult, ToolStatus


class CalculatorTool(BaseTool):
    """
    Outil pour évaluer des expressions mathématiques
    Utilise seulement des opérations mathématiques sûres
    """
    
    def __init__(self):
        super().__init__(
            name="math_calculator",
            description="Évaluer des expressions mathématiques de manière sécurisée"
        )
        
        # Opérations autorisées
        self.safe_operations = {
            '+': operator.add,
            '-': operator.sub,
            '*': operator.mul,
            '/': operator.truediv,
            '//': operator.floordiv,
            '%': operator.mod,
            '**': operator.pow,
            '==': operator.eq,
            '!=': operator.ne,
            '<': operator.lt,
            '<=': operator.le,
            '>': operator.gt,
            '>=': operator.ge,
        }
        
        # Fonctions mathématiques autorisées
        self.safe_functions = {
            'abs': abs,
            'round': round,
            'min': min,
            'max': max,
            'sum': sum,
            'sqrt': math.sqrt,
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'log': math.log,
            'exp': math.exp,
            'pi': math.pi,
            'e': math.e,
        }
    
    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Évaluer l'expression"""
        # Valider les arguments
        is_valid, error = self.validate_arguments(arguments)
        if not is_valid:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"Invalid arguments: {error}"
            )
        
        expression = arguments['expression']
        
        try:
            # Évaluer de manière sûre
            result = self._safe_eval(expression)
            
            # Convertir le résultat en string
            if isinstance(result, float):
                # Arrondir pour les floats proches d'entiers
                if abs(result - round(result)) < 1e-10:
                    result_str = str(int(round(result)))
                else:
                    result_str = f"{result:.10f}".rstrip('0').rstrip('.')
            else:
                result_str = str(result)
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=result_str,
                metadata={
                    "expression": expression,
                    "result": result,
                    "result_type": type(result).__name__
                }
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"Failed to evaluate expression: {str(e)}"
            )
    
    def _safe_eval(self, expression: str):
        """
        Évaluer de manière sûre en utilisant seulement les opérations autorisées
        Note: Cette approche est basique. Une vraie implémentation nécessiterait
        un parser AST plus sophistiqué.
        """
        # Nettoyer l'expression
        expression = expression.strip()
        
        # Bloquer les appels de fonctions dangereux
        if any(func in expression for func in ['eval', 'exec', '__', 'import']):
            raise ValueError("Unsafe expression detected")
        
        # Remplacer les fonctions mathématiques par des appels Python
        for func_name, func in self.safe_functions.items():
            if func_name in expression:
                # Remplacer les appels de fonction
                pattern = rf'\b{func_name}\s*\('
                if re.search(pattern, expression):
                    # Créer un contexte d'exécution
                    context = self.safe_functions.copy()
                    
                    # Évaluer dans un contexte limité
                    result = eval(expression, {"__builtins__": {}}, context)
                    return result
        
        # Pour les expressions simples (arithmétique basique)
        # Créer un contexte vide (pas de builtins)
        context = {"__builtins__": {}}
        context.update(self.safe_operations)
        context.update(self.safe_functions)
        
        # Évaluer
        result = eval(expression, context, {})
        return result
    
    def validate_arguments(self, arguments: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Valider les arguments"""
        if not isinstance(arguments, dict):
            return False, "Arguments must be a dictionary"
        
        if 'expression' not in arguments:
            return False, "Missing required argument: 'expression'"
        
        if not isinstance(arguments['expression'], str):
            return False, "Argument 'expression' must be a string"
        
        if len(arguments['expression']) > 1000:
            return False, "Expression too long (max 1000 characters)"
        
        return True, None
    
    def _get_parameters_schema(self) -> Dict[str, Any]:
        """Schéma des paramètres"""
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Expression mathématique à évaluer (ex: '2 + 3 * 4', 'sqrt(16)')"
                }
            },
            "required": ["expression"]
        }
