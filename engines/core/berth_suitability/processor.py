"""Processor entrypoint for berth suitability."""
from engines.learning.training.ml_models import BerthSuitabilityModel

Processor = BerthSuitabilityModel

__all__ = ["Processor", "BerthSuitabilityModel"]
