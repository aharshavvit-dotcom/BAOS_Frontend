"""Processor entrypoint for reinforcement learning."""
from engines.learning.rl.weight_agent import BerthingRLAgent

Processor = BerthingRLAgent

__all__ = ["Processor", "BerthingRLAgent"]
