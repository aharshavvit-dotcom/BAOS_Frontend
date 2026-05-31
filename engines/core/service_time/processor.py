"""Processor entrypoint for service time prediction."""
from engines.learning.training.ml_models import ServiceTimePredictor

Processor = ServiceTimePredictor

__all__ = ["Processor", "ServiceTimePredictor"]
