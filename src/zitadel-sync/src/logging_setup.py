"""
zitadel-sync — logging (stdlib, console or JSON lines). No PII/secrets logged.
"""

from __future__ import annotations

import json
import logging
import sys

logger = logging.getLogger("zitadel-sync")
_initialized = False


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": int(record.created * 1000),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: str = "INFO", fmt: str = "console") -> None:
    global _initialized
    if _initialized:
        return
    _initialized = True

    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    if fmt == "json":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(message)s"))
    handler.setLevel(level.upper())
    root.addHandler(handler)
    root.setLevel(level.upper())
    logger.setLevel(level.upper())
