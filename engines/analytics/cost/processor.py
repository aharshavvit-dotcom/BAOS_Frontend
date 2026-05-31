"""Processor entrypoint for cost analytics."""
from engines.analytics.cost.cost_model import CostEngine

Processor = CostEngine

__all__ = ["Processor", "CostEngine"]
