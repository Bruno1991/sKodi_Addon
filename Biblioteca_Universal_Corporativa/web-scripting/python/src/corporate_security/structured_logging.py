from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any


class JsonFormatter(logging.Formatter):
    RESERVED = {"key", "token", "password", "secret", "cookie", "authorization", "plaintext", "envelope"}

    def format(self, record: logging.LogRecord) -> str:
        fields: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "event": getattr(record, "event", "application.log"),
            "message": record.getMessage(),
            "service": getattr(record, "service", "unknown"),
            "correlation_id": getattr(record, "correlation_id", "unassigned"),
            "outcome": getattr(record, "outcome", "success"),
        }
        for name, value in getattr(record, "structured", {}).items():
            fields[name] = "[REDACTED]" if name.lower() in self.RESERVED else value
        if record.exc_info:
            fields["error_type"] = record.exc_info[0].__name__ if record.exc_info[0] else "Exception"
        return json.dumps(fields, ensure_ascii=False, separators=(",", ":"), default=str)
