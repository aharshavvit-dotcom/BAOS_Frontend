"""Processor entrypoint for uncertainty simulation."""
from engines.simulation.uncertainty.monte_carlo import UncertaintyEngine

Processor = UncertaintyEngine

__all__ = ["Processor", "UncertaintyEngine"]
