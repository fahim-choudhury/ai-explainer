"""Terminal output for xv, following https://clig.dev:

- stdout carries the primary result (paths written, reports, JSON); stderr carries progress, hints and errors
- -q/--quiet hides progress and hints; -d/--debug shows the commands xv runs and tracebacks
- colour only on a TTY, never with NO_COLOR, TERM=dumb or --no-color; FORCE_COLOR forces it
"""
import json, os, sys

QUIET = False
DEBUG = False
NO_COLOR_FLAG = False

# Exit codes, documented in `xv --help`.
OK, FAILED, USAGE, NOT_SET_UP, INTERRUPTED = 0, 1, 2, 3, 130


class XVError(Exception):
    """An expected failure: printed as `xv: error: <message>` plus an optional hint, exit code 1 (or `code`)."""

    def __init__(self, message, hint=None, code=FAILED):
        super().__init__(message)
        self.hint, self.code = hint, code


def color_on(stream):
    if NO_COLOR_FLAG or os.environ.get("NO_COLOR") or os.environ.get("XV_NO_COLOR") or os.environ.get("TERM") == "dumb":
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return stream.isatty()


CODES = {"red": "31", "green": "32", "yellow": "33", "bold": "1", "dim": "2"}


def paint(text, color, stream=sys.stdout):
    return f"\033[{CODES[color]}m{text}\033[0m" if color_on(stream) else text


def out(text=""):
    """Primary output: stdout, never suppressed."""
    print(text, flush=True)


def info(text=""):
    """Progress and context: stderr, hidden by --quiet."""
    if not QUIET:
        print(text, file=sys.stderr, flush=True)


def debug(text):
    if DEBUG:
        print(paint(text, "dim", sys.stderr), file=sys.stderr, flush=True)


def warn(text):
    print(f"{paint('warning', 'yellow', sys.stderr)}: {text}", file=sys.stderr, flush=True)


def hint(*commands):
    """Suggest the next command(s) in the workflow."""
    if not QUIET and commands:
        print(paint("next: ", "dim", sys.stderr) + "; ".join(commands), file=sys.stderr, flush=True)


def error(message, hint_text=None):
    print(f"xv: {paint('error', 'red', sys.stderr)}: {message}", file=sys.stderr, flush=True)
    if hint_text:
        print(f"  {hint_text}", file=sys.stderr, flush=True)


def emit_json(data):
    print(json.dumps(data, indent=2, ensure_ascii=False), flush=True)
