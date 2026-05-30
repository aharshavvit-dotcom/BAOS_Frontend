"""Root-level backend launcher.

Run from the repository root:
    python run.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_BACKEND = _ROOT / "backend"
for _path in (_BACKEND, _ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from backend.run import main


if __name__ == "__main__":
    asyncio.run(main())
