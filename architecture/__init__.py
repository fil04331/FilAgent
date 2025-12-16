"""
Architecture Components for FilAgent

This package contains architectural components that follow Clean Architecture 
and SOLID principles:

- Router: Strategic decision-making (Planning vs Direct execution)
- Component interfaces and contracts
"""

from .router import StrategyRouter, ExecutionStrategy

__all__ = ["StrategyRouter", "ExecutionStrategy"]
