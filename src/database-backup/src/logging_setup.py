"""
database-backup — logging & console.

Console mode renders through rich (``RichHandler``); ``json`` mode emits one
structured JSON object per line. A shared rich ``Console`` is exported for
banners/panels. No secrets are ever logged.
"""

from __future__ import annotations

import json
import logging

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel

console = Console(force_terminal=True)

logger = logging.getLogger("database-backup")
_initialized = False


class _JsonFormatter(logging.Formatter):
    """One compact JSON object per log line (ingestion-friendly)."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": int(record.created * 1000),
            "level": record.levelname,
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
            console=console, rich_tracebacks=True, show_path=False, markup=True
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
            f"[bold cyan]CS-IAM · Database-Backup[/]\n[dim]{subtitle}[/]",
            border_style="cyan",
            padding=(0, 2),
        )
    )
    console.print()


def format_size(n: int) -> str:
    """Human-readable byte size, e.g. ``12.3 MB``."""
    f = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if f < 1024:
            return f"{f:.1f} {unit}"
        f /= 1024
    return f"{f:.1f} TB"
