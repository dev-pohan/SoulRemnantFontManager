from __future__ import annotations

import json
import os
import platform
import shutil
import stat
import sys
import time
from pathlib import Path

from .config import data_dir


def executable_name() -> str:
    return "SoulRemnantFontManager.exe" if platform.system() == "Windows" else "soul-remnant-font-manager"


def install_executable() -> Path:
    target_dir = data_dir() / "bin"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / executable_name()
    if getattr(sys, "frozen", False):
        source = Path(sys.executable).resolve()
        if source != target.resolve():
            _replace_managed_executable(source, target)
    else:
        # Development marker; packaged Releases always install a standalone binary.
        target = Path(sys.executable).resolve()
    _write_prelaunch_descriptor(target)
    return target


def _replace_managed_executable(source: Path, target: Path) -> None:
    """Replace the prelaunch runner, recovering from Windows file attributes and brief locks."""
    temporary = target.with_name(f"{target.name}.{os.getpid()}.writing")
    legacy_temporary = target.with_suffix(target.suffix + ".writing")
    try:
        _unlink_writable(temporary)
        shutil.copy2(source, temporary)
        _make_writable(temporary)

        for attempt in range(20):
            _make_writable(target)
            try:
                os.replace(temporary, target)
                break
            except PermissionError:
                if attempt == 19:
                    raise
                time.sleep(0.25)
        _make_writable(target)
        _unlink_writable(legacy_temporary)
    finally:
        _unlink_writable(temporary)


def _make_writable(path: Path) -> None:
    try:
        path.chmod(path.stat().st_mode | stat.S_IWRITE)
    except FileNotFoundError:
        pass


def _unlink_writable(path: Path) -> None:
    if not path.exists():
        return
    _make_writable(path)
    path.unlink()


def refresh_existing_install() -> bool:
    """Refresh the managed runner whenever a newer downloaded Manager is opened."""
    if not getattr(sys, "frozen", False):
        return False
    installed = data_dir() / "bin" / executable_name()
    current = Path(sys.executable).resolve()
    if not installed.is_file() or current == installed.resolve():
        return False
    install_executable()
    return True


def launch_options(executable: Path) -> str:
    if getattr(sys, "frozen", False):
        prefix = f'"{executable}"'
    else:
        package_root = Path(__file__).resolve().parents[1]
        prefix = f'"{executable}" -m srfontmanager'
        os.environ.setdefault("PYTHONPATH", str(package_root))
    return f"{prefix} --prelaunch -- %command%"


def _write_prelaunch_descriptor(executable: Path) -> None:
    descriptor = {
        "version": 1,
        "executable": str(executable),
        "arguments": ["--prelaunch", "--", "%command%"],
        "note": "Generated and managed by SoulRemnantFontManager",
    }
    path = data_dir() / "prelaunch.json"
    temporary = path.with_suffix(".json.writing")
    temporary.write_text(json.dumps(descriptor, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def remove_managed_files(keep_executable: Path | None = None) -> None:
    root = data_dir()
    if not root.exists():
        return
    for name in ("fonts", "logs", "prelaunch.json", "config.json"):
        target = root / name
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
    binary_dir = root / "bin"
    if binary_dir.is_dir() and keep_executable is None:
        shutil.rmtree(binary_dir)
