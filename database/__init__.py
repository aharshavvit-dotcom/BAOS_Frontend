"""Compatibility package for root-level `python -m database.seed`."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
_BACKEND_DATABASE = _BACKEND / "database"

for _path in (_BACKEND, _ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

__path__ = [str(_BACKEND_DATABASE), *list(__path__)]
