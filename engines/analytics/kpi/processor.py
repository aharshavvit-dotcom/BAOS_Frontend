"""Processor entrypoint for KPI analytics."""
from engines.analytics.kpi.kpi_calculator import KPICalculator

Processor = KPICalculator

__all__ = ["Processor", "KPICalculator"]
