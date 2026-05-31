"""Processor entrypoint for digital twin simulation."""
from engines.simulation.digital_twin import PortDigitalTwin

Processor = PortDigitalTwin

__all__ = ["Processor", "PortDigitalTwin"]
