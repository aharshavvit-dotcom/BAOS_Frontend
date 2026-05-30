"""Simple in-process engine registry."""
from typing import Dict

from engines.base_engine import BaseEngine

_registry: Dict[str, BaseEngine] = {}


def register(engine: BaseEngine) -> None:
    """Register an engine instance by name."""
    _registry[engine.name] = engine


def get(name: str) -> BaseEngine:
    """Get a registered engine by name."""
    if name not in _registry:
        raise KeyError(f"Engine '{name}' not registered.")
    return _registry[name]


def all_engines() -> Dict[str, BaseEngine]:
    """Return a copy of the registered engines."""
    return dict(_registry)
