"""Package pour l'évaluation et les benchmarks"""

# Lazy imports to avoid heavy dependencies when only using metrics
__all__ = ["HumanEvalHarness", "MBPPHarness"]


def __getattr__(name):
    """Lazy import heavy dependencies"""
    if name == "HumanEvalHarness":
        from .humaneval import HumanEvalHarness
        return HumanEvalHarness
    elif name == "MBPPHarness":
        from .mbpp import MBPPHarness
        return MBPPHarness
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
