"""
directory-sync — logging & console.

Console mode renders through rich (``RichHandler``) for colored, aligned output;
``json`` mode emits one structured JSON object per line for central ingestion.
A shared rich ``Console`` is exported for banners/panels. No PII or secrets are
ever logged.
"""

from __future__ import annotations

import json
import logging

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel

# Shared console — force_terminal keeps colors in non-TTY contexts (Docker logs).
console = Console(force_terminal=True)

logger = logging.getLogger("directory-sync")
_initialized = False


class _JsonFormatter(logging.Formatter):
    """One compact JSON object per log line (ingestion-friendly)."""

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
    """Configure root logging once (idempotent). ``fmt`` is ``console`` or ``json``."""
    global _initialized
    if _initialized:
        return
    _initialized = True

    handler: logging.Handler
    if fmt == "json":
        handler = logging.StreamHandler()
        handler.setFormatter(_JsonFormatter())
    else:
        handler = RichHandler(
            console=console,
            rich_tracebacks=True,
            show_path=False,
            omit_repeated_times=False,
            markup=True,
        )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
    logger.setLevel(level.upper())


def print_banner(subtitle: str) -> None:
    """Print the service banner (console mode only)."""
    console.print(
        Panel.fit(
            f"[bold blue]CS-IAM · Directory-Sync[/]\n[dim]{subtitle}[/]",
            border_style="blue",
            padding=(0, 2),
        )
    )
    console.print()
