"""Processor entrypoint for commercial analytics."""
from engines.analytics.commercial.commercial_scorer import CommercialScorer

Processor = CommercialScorer

__all__ = ["Processor", "CommercialScorer"]
