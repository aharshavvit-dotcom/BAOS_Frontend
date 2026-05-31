"""Processor entrypoint for berth decisioning."""
from engines.core.decision.recommender import recommend_berth

Processor = recommend_berth

__all__ = ["Processor", "recommend_berth"]
