#!/usr/bin/env python3
"""
generate-env.py — Create a `.env` file from `.env.example` with secure secrets.

Cross-platform (Windows / Linux / macOS), pure stdlib, no dependencies.

Replaces every `CHANGE_ME_*` placeholder for known secret keys with a fresh
random value:

  - hex secrets       → only [0-9a-f]; shell-, URL- and .env-safe.
  - the masterkey     → exactly 32 characters (Zitadel requirement).
  - the admin password→ a complex but .env-safe password (upper/lower/digit/
                        symbol from a conservative set) that satisfies the
                        default Zitadel password complexity policy.

Usage
-----
    python scripts/generate-env.py                # writes .env (refuses to overwrite)
    python scripts/generate-env.py --force        # overwrite (creates .env.bak first)
    python scripts/generate-env.py --dry-run      # show what would change
    python scripts/generate-env.py --print        # dump rendered file to stdout

Exit codes
----------
    0  success
    1  precondition failed (.env.example missing, .env exists without --force, ...)
    2  no replacements happened
"""

from __future__ import annotations

import argparse
import os
import re
import secrets
import shutil
import stat
import sys
from pathlib import Path

# --- Configuration -----------------------------------------------------------
# Each entry: name -> (kind, length, description)
#   kind "hex"      -> secrets.token_hex(length // 2)  → `length` hex chars
#   kind "password" -> complex .env-safe password of `length` chars
SECRETS: dict[str, tuple[str, int, str]] = {
    # Zitadel masterkey — MUST be exactly 32 chars (encrypts secrets at rest).
    "ZITADEL_MASTERKEY":      ("hex", 32, "Zitadel masterkey (32 chars, secrets-at-rest key)"),
    # PostgreSQL password for the zitadel DB user.
    "ZITADEL_DB_PASSWORD":    ("hex", 48, "PostgreSQL zitadel-user password"),
    # First admin console password — needs complexity (upper/lower/digit/symbol).
    "ZITADEL_ADMIN_PASSWORD": ("password", 24, "Zitadel first-admin console password"),
    # Optional self-contained demo user (opt-in; blank in .env to disable). Filled
    # so the shipped template never carries a known credential.
    "DEMO_USER_PASSWORD":     ("password", 20, "Demo user login password (optional demo)"),
}

PLACEHOLDER_RE = re.compile(r"CHANGE_ME_[A-Z0-9_]*")

# Conservative symbol set — safe inside an unquoted .env value (no quotes,
# spaces, $, #, backtick that could trip shell/.env parsers).
_PW_SYMBOLS = "-_.@%+="
_PW_LOWER = "abcdefghijkmnopqrstuvwxyz"   # no l
_PW_UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ"    # no I, O
_PW_DIGITS = "23456789"                   # no 0, 1


def make_secret(kind: str, length: int) -> str:
    if kind == "hex":
        # token_hex(n) → 2n hex chars; we want exactly `length` chars.
        return secrets.token_hex(length // 2)[:length]
    if kind == "password":
        return make_password(length)
    raise ValueError(f"unknown secret kind: {kind!r}")


def make_password(length: int) -> str:
    """A complex, .env-safe password guaranteeing all four character classes."""
    if length < 8:
        length = 8
    pools = [_PW_LOWER, _PW_UPPER, _PW_DIGITS, _PW_SYMBOLS]
    # One guaranteed char from each class, rest from the union.
    chars = [secrets.choice(p) for p in pools]
    union = _PW_LOWER + _PW_UPPER + _PW_DIGITS + _PW_SYMBOLS
    chars += [secrets.choice(union) for _ in range(length - len(chars))]
    # Shuffle without exposing index bias.
    for i in range(len(chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        chars[i], chars[j] = chars[j], chars[i]
    return "".join(chars)


# --- Core --------------------------------------------------------------------

def render(example_text: str) -> tuple[str, dict[str, str], list[str]]:
    rendered = example_text
    replaced: dict[str, str] = {}
    warnings: list[str] = []

    for name, (kind, length, _desc) in SECRETS.items():
        pattern = re.compile(rf"^({re.escape(name)}=)CHANGE_ME_[^\r\n]*$", re.MULTILINE)
        new_value = make_secret(kind, length)
        rendered, count = pattern.subn(lambda m, v=new_value: m.group(1) + v, rendered, count=1)
        if count == 0:
            if re.search(rf"^{re.escape(name)}=", rendered, re.MULTILINE):
                warnings.append(f"{name}: present but not a CHANGE_ME placeholder — left untouched")
            else:
                warnings.append(f"{name}: not found in example file")
        else:
            replaced[name] = preview(new_value)

    leftover_lines = [
        ln for ln in rendered.splitlines()
        if PLACEHOLDER_RE.search(ln) and not ln.lstrip().startswith("#")
    ]
    leftovers = sorted({m for ln in leftover_lines for m in PLACEHOLDER_RE.findall(ln)})
    if leftovers:
        warnings.append("remaining CHANGE_ME_* placeholders (review manually): " + ", ".join(leftovers))

    return rendered, replaced, warnings


def preview(secret: str) -> str:
    if len(secret) <= 12:
        return "*" * len(secret)
    return f"{secret[:4]}...{secret[-4:]} ({len(secret)} chars)"


# --- File handling -----------------------------------------------------------

def resolve_path(arg: str, base: Path) -> Path:
    p = Path(arg)
    return p if p.is_absolute() else (base / p)


def harden_permissions(path: Path) -> bool:
    if os.name == "nt":
        return False
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        return True
    except OSError:
        return False


# --- CLI ---------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="generate-env.py",
        description="Generate a .env file from .env.example with secure random secrets.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--example", default=".env.example", help="path to the example file")
    p.add_argument("--output", default=".env", help="path to write the generated file")
    p.add_argument("-f", "--force", action="store_true", help="overwrite existing output (creates .bak)")
    p.add_argument("--dry-run", action="store_true", help="show what would change, write nothing")
    p.add_argument("--print", action="store_true", dest="print_only", help="print rendered file to stdout")
    p.add_argument("--no-harden", action="store_true", help="skip chmod 600 (POSIX only)")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent
    example_path = resolve_path(args.example, repo_root)
    output_path = resolve_path(args.output, repo_root)

    if not example_path.exists():
        print(f"error: example file not found: {example_path}", file=sys.stderr)
        return 1

    if output_path.exists() and not (args.force or args.dry_run or args.print_only):
        print(
            f"error: {output_path} already exists. Use --force to overwrite "
            f"(a .bak will be created), --dry-run, or --print.",
            file=sys.stderr,
        )
        return 1

    example_text = example_path.read_text(encoding="utf-8")
    rendered, replaced, warnings = render(example_text)

    if not replaced:
        print("error: no known CHANGE_ME_* placeholders were replaced.", file=sys.stderr)
        for w in warnings:
            print(f"  - {w}", file=sys.stderr)
        return 2

    if args.print_only:
        sys.stdout.write(rendered)
        return 0

    if args.dry_run:
        print(f"would write: {output_path}")
        print(f"replacements ({len(replaced)}):")
        for name, prev in replaced.items():
            print(f"  {name:26s} {prev}")
        for w in warnings:
            print(f"  ! {w}")
        return 0

    if output_path.exists():
        backup = output_path.with_suffix(output_path.suffix + ".bak")
        shutil.copy2(output_path, backup)
        print(f"backup: {backup}")

    output_path.write_text(rendered, encoding="utf-8", newline="\n")

    hardened = False
    if not args.no_harden:
        hardened = harden_permissions(output_path)

    print(f"wrote:  {output_path}")
    print(f"secrets generated ({len(replaced)}):")
    for name, prev in replaced.items():
        print(f"  {name:26s} {prev}  # {SECRETS[name][2]}")
    if hardened:
        print("permissions: 0600 (owner read/write only)")
    elif os.name != "nt" and not args.no_harden:
        print("permissions: chmod failed — set them manually with `chmod 600 .env`")
    for w in warnings:
        print(f"  ! {w}")

    print()
    print("next: set IAM_HOSTNAME and AZURE_* in .env, then start the stack:")
    print("      docker compose -f docker-compose.development.yml up -d")
    return 0


def reconfigure_stdout_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, OSError):
            pass


if __name__ == "__main__":
    reconfigure_stdout_utf8()
    sys.exit(main())
