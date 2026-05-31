"""Processor entrypoint for delay prediction."""
from engines.learning.training.ml_models import DelayPredictor

Processor = DelayPredictor

__all__ = ["Processor", "DelayPredictor"]
