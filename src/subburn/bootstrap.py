from __future__ import annotations

import importlib
import os
from pathlib import Path
import subprocess
import sys
import threading

APP_NAME = "SubBurn"

CORE_REQUIREMENTS = (
    ("fontTools", "fonttools==4.63.0"),
    ("regex", "regex==2026.5.9"),
)

OPTIONAL_REQUIREMENTS = {
    "dragdrop": (("tkinterdnd2", "tkinterdnd2==0.6.3"),),
    "transcription": (
        ("faster_whisper", "faster-whisper==1.2.1"),
        ("ctranslate2", "ctranslate2==4.8.2"),
        ("huggingface_hub", "huggingface-hub==1.31.0"),
    ),
}

_INSTALL_LOCK = threading.RLock()


def _runtime_root() -> Path:
    home = Path.home()
    py_tag = f"py{sys.version_info.major}{sys.version_info.minor}"
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or (home / "AppData" / "Local"))
        return base / APP_NAME / "python" / py_tag
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / APP_NAME / "python" / py_tag
    base = Path(os.environ.get("XDG_DATA_HOME") or (home / ".local" / "share"))
    return base / "subburn" / "python" / py_tag


def activate_runtime_packages() -> Path:
    target = _runtime_root()
    target.mkdir(parents=True, exist_ok=True)
    text = str(target)
    if text not in sys.path:
        sys.path.insert(0, text)
    importlib.invalidate_caches()
    return target


def _module_available(name: str) -> bool:
    try:
        importlib.import_module(name)
        return True
    except Exception:
        return False


def _run_quiet(command: list[str]) -> subprocess.CompletedProcess:
    kwargs = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.PIPE,
        "text": True,
        "env": dict(os.environ, PIP_DISABLE_PIP_VERSION_CHECK="1", PIP_NO_INPUT="1", PIP_PROGRESS_BAR="off"),
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(command, **kwargs)


def _ensure_pip() -> None:
    check = _run_quiet([sys.executable, "-m", "pip", "--version"])
    if check.returncode == 0:
        return
    result = _run_quiet([sys.executable, "-m", "ensurepip", "--upgrade"])
    if result.returncode != 0:
        detail = (result.stderr or "").strip()[-1500:]
        raise RuntimeError("Python package installer is unavailable" + (f": {detail}" if detail else ""))


def ensure_requirements(requirements, *, required: bool = True) -> bool:
    try:
        activate_runtime_packages()
        missing = [(module, spec) for module, spec in requirements if not _module_available(module)]
        if not missing:
            return True
        with _INSTALL_LOCK:
            activate_runtime_packages()
            missing = [(module, spec) for module, spec in requirements if not _module_available(module)]
            if not missing:
                return True
            _ensure_pip()
            target = activate_runtime_packages()
            command = [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-input",
                "--quiet",
                "--retries",
                "1",
                "--timeout",
                "20",
                "--upgrade",
                "--target",
                str(target),
            ] + [spec for _, spec in missing]
            result = _run_quiet(command)
            if result.returncode != 0:
                detail = (result.stderr or "").strip()[-3000:]
                raise RuntimeError("Dependency setup failed" + (f": {detail}" if detail else ""))
            importlib.invalidate_caches()
            unresolved = [module for module, _ in missing if not _module_available(module)]
            if unresolved:
                raise RuntimeError("Dependency setup did not provide: " + ", ".join(unresolved))
            return True
    except Exception:
        if required:
            raise
        return False

def ensure_core_dependencies() -> bool:
    return ensure_requirements(CORE_REQUIREMENTS, required=True)


def ensure_optional_dependency_group(name: str, *, required: bool = False) -> bool:
    requirements = OPTIONAL_REQUIREMENTS.get(str(name), ())
    if not requirements:
        return True
    return ensure_requirements(requirements, required=required)


def ensure_all_dependencies(*, required: bool = False) -> bool:
    ok = ensure_requirements(CORE_REQUIREMENTS, required=required)
    for group in ("dragdrop", "transcription"):
        if not ensure_optional_dependency_group(group, required=required):
            ok = False
    return ok
