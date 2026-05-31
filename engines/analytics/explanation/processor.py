"""Processor entrypoint for explanation analytics."""
from engines.analytics.explanation.explainer import AgenticExplainer
from engines.analytics.explanation.structured_explanation import StructuredExplanationEngine

Processor = AgenticExplainer

__all__ = ["Processor", "AgenticExplainer", "StructuredExplanationEngine"]
