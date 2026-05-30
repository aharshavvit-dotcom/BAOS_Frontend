"""Common interface for BAOS engines."""
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseEngine(ABC):
    """Base engine interface."""

    name: str = ""

    @abstractmethod
    def train(self, data: Any) -> Dict:
        """Train the engine and return a status dictionary."""
        ...

    @abstractmethod
    def predict(self, input_data: Any) -> Any:
        """Run inference."""
        ...

    def status(self) -> Dict:
        """Return engine health/readiness status."""
        return {"engine": self.name, "ready": True}
