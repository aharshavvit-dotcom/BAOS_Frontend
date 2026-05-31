"""Processor entrypoint for scenario simulation."""
from engines.simulation.scenario.scenario_manager import ScenarioManager

Processor = ScenarioManager

__all__ = ["Processor", "ScenarioManager"]
