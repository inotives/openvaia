"""CLI utilities shared across all commands."""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from decimal import Decimal


class JSONEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal, date, datetime."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def output(data: dict | list) -> None:
    """Print JSON to stdout."""
    print(json.dumps(data, cls=JSONEncoder, indent=2))


def error(msg: str, code: int = 1) -> None:
    """Print error JSON and exit."""
    print(json.dumps({"error": msg}), file=sys.stderr)
    sys.exit(code)
