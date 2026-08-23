from __future__ import annotations

import os
import platform
import re
import shutil
from pathlib import Path

from .config import APP_ID


def steam_roots() -> list[Path]:
    candidates: list[Path] = []
    system = platform.system()
    if system == "Windows":
        try:
            import winreg

            for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                for key_name in (r"Software\Valve\Steam", r"Software\WOW6432Node\Valve\Steam"):
                    try:
                        with winreg.OpenKey(hive, key_name) as key:
                            for value_name in ("SteamPath", "InstallPath"):
                                try:
                                    candidates.append(Path(winreg.QueryValueEx(key, value_name)[0]))
                                except OSError:
                                    pass
                    except OSError:
                        pass
        except ImportError:
            pass
        candidates += [Path(r"C:\Program Files (x86)\Steam"), Path(r"C:\Program Files\Steam")]
    elif system == "Darwin":
        candidates.append(Path.home() / "Library" / "Application Support" / "Steam")
    else:
        candidates += [
            Path.home() / ".steam" / "steam",
            Path.home() / ".local" / "share" / "Steam",
            Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam",
        ]
    return _unique_existing(candidates)


def library_roots() -> list[Path]:
    libraries: list[Path] = []
    for steam in steam_roots():
        libraries.append(steam)
        vdf = steam / "steamapps" / "libraryfolders.vdf"
        if not vdf.is_file():
            continue
        text = vdf.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r'"path"\s+"((?:\\.|[^"\\])*)"', text):
            value = _vdf_unescape(match.group(1))
            libraries.append(Path(value))
    return _unique_existing(libraries)


def find_game_dir() -> Path | None:
    for library in library_roots():
        manifest = library / "steamapps" / f"appmanifest_{APP_ID}.acf"
        if not manifest.is_file():
            continue
        text = manifest.read_text(encoding="utf-8", errors="replace")
        match = re.search(r'"installdir"\s+"((?:\\.|[^"\\])*)"', text)
        if match:
            game = library / "steamapps" / "common" / _vdf_unescape(match.group(1))
            if game.is_dir():
                return game.resolve()
    return None


def user_configs() -> list[Path]:
    found: list[Path] = []
    for root in steam_roots():
        userdata = root / "userdata"
        if not userdata.is_dir():
            continue
        for config in userdata.glob("*/config/localconfig.vdf"):
            try:
                text = config.read_text(encoding="utf-8", errors="replace")
                _app_block(text)
            except (OSError, ValueError):
                continue
            found.append(config.resolve())
    return sorted(set(found), key=lambda item: item.stat().st_mtime, reverse=True)


def client_executable() -> Path | None:
    system = platform.system()
    if system == "Windows":
        for root in steam_roots():
            candidate = root / "steam.exe"
            if candidate.is_file():
                return candidate
    elif system == "Darwin":
        candidates = [
            Path("/Applications/Steam.app/Contents/MacOS/steam_osx"),
            Path.home() / "Applications" / "Steam.app" / "Contents" / "MacOS" / "steam_osx",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return candidate
    else:
        command = shutil.which("steam")
        if command:
            return Path(command)
        for root in steam_roots():
            for name in ("steam.sh", "steam"):
                candidate = root / name
                if candidate.is_file():
                    return candidate
    return None


def get_launch_options(config: Path) -> str:
    text = config.read_text(encoding="utf-8", errors="strict")
    start, end = _app_block(text)
    block = text[start:end]
    match = re.search(r'"LaunchOptions"\s+"((?:\\.|[^"\\])*)"', block)
    return _vdf_unescape(match.group(1)) if match else ""


def set_launch_options(config: Path, value: str) -> None:
    text = config.read_text(encoding="utf-8", errors="strict")
    start, end = _app_block(text)
    block = text[start:end]
    pattern = re.compile(r'("LaunchOptions"\s+")((?:\\.|[^"\\])*)(")')
    escaped = _vdf_escape(value)
    if pattern.search(block):
        block = pattern.sub(lambda match: match.group(1) + escaped + match.group(3), block, count=1)
    else:
        closing_line = block.rfind("}")
        line_start = block.rfind("\n", 0, closing_line) + 1
        closing_indent = re.match(r"[ \t]*", block[line_start:closing_line]).group(0)
        entry = f'{closing_indent}\t"LaunchOptions"\t\t"{escaped}"\n'
        block = block[:line_start] + entry + block[line_start:]
    updated = text[:start] + block + text[end:]
    backup = config.with_suffix(config.suffix + ".srfontmanager.bak")
    if not backup.exists():
        backup.write_bytes(config.read_bytes())
    temporary = config.with_suffix(config.suffix + ".writing")
    temporary.write_text(updated, encoding="utf-8", newline="")
    os.replace(temporary, config)


def _app_block(text: str) -> tuple[int, int]:
    match = re.search(rf'"{re.escape(APP_ID)}"\s*\{{', text)
    if not match:
        raise ValueError(f"Steam 帳號設定中找不到 App {APP_ID}")
    opening = text.find("{", match.start())
    depth = 0
    quoted = False
    escaped = False
    for index in range(opening, len(text)):
        char = text[index]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == '"':
            quoted = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return match.start(), index + 1
    raise ValueError("Steam localconfig.vdf 的括號不完整")


def _vdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _vdf_unescape(value: str) -> str:
    return value.replace('\\"', '"').replace("\\\\", "\\")


def _unique_existing(paths: list[Path]) -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        try:
            resolved = path.expanduser().resolve()
        except OSError:
            continue
        key = str(resolved).casefold()
        if resolved.is_dir() and key not in seen:
            seen.add(key)
            result.append(resolved)
    return result
