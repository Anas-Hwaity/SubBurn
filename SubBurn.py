from __future__ import annotations

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _fatal(message: str) -> None:
    text = str(message or "SubBurn could not start.")
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, text, "SubBurn", 0x10)
            return
        except Exception:
            pass
    try:
        print(text, file=sys.stderr)
    except Exception:
        pass


def main() -> None:
    if not ((3, 10) <= sys.version_info[:2] < (3, 14)):
        _fatal("SubBurn requires Python 3.10, 3.11, 3.12, or 3.13.")
        return
    try:
        import tkinter  # noqa: F401
    except Exception:
        _fatal("This Python installation does not include Tk/Tcl. Install the standard Python build with Tcl/Tk support.")
        return
    try:
        from subburn.app import main as run_subburn
    except Exception as exc:
        _fatal(str(exc))
        return
    try:
        run_subburn()
    except Exception as exc:
        _fatal(str(exc))


if __name__ == "__main__":
    main()
