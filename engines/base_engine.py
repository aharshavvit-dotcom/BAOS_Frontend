"""Common interface for BAOS engines."""
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseEngine(ABC):
    """
    All engines must implement train(), predict(), and status().
    The main implementation file in each engine folder is called processor.py.
    """

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
