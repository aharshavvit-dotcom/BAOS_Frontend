"""Processor entrypoint for model training."""
from engines.learning.training.trainer import train_port_models

Processor = train_port_models

__all__ = ["Processor", "train_port_models"]
