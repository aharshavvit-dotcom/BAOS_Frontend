"""Root-level seed wrapper."""
from __future__ import annotations

from backend.database.seed import seed


if __name__ == "__main__":
    seed()
