from __future__ import annotations

import json
import os
import platform
from dataclasses import asdict, dataclass
from pathlib import Path

APP_ID = "3451980"
APP_DIR_NAME = "SoulRemnantFontManager"

FONT_SIZE_SETTINGS = (
    ("general_ui_scale", "一般 UI"),
    ("description_scale", "說明長文"),
    ("quest_scale", "任務文字"),
    ("hud_world_scale", "HUD／世界標籤"),
    ("chat_scale", "聊天文字"),
    ("popup_scale", "彈出提示"),
)
DEFAULT_FONT_SCALE = 1.0


def data_dir() -> Path:
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        native_steam = (Path.home() / ".steam" / "steam").exists() or (
            Path.home() / ".local" / "share" / "Steam"
        ).exists()
        flatpak_root = Path.home() / ".var" / "app" / "com.valvesoftware.Steam"
        if flatpak_root.exists() and not native_steam:
            # Keep the runner inside Steam Flatpak's visible per-app filesystem.
            base = flatpak_root / "data"
        else:
            base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / APP_DIR_NAME


@dataclass
class Settings:
    version: int = 1
    game_dir: str = ""
    pixel_font_file: str = ""
    traditional_font_file: str = ""
    general_ui_scale: float = DEFAULT_FONT_SCALE
    description_scale: float = DEFAULT_FONT_SCALE
    quest_scale: float = DEFAULT_FONT_SCALE
    hud_world_scale: float = DEFAULT_FONT_SCALE
    chat_scale: float = DEFAULT_FONT_SCALE
    popup_scale: float = DEFAULT_FONT_SCALE
    steam_user_config: str = ""
    installed_launch_options: str = ""
    previous_launch_options: str = ""

    @classmethod
    def load(cls) -> "Settings":
        path = data_dir() / "config.json"
        if not path.is_file():
            return cls()
        raw = json.loads(path.read_text(encoding="utf-8"))
        legacy_font = str(raw.get("font_file", ""))
        if legacy_font:
            raw.setdefault("pixel_font_file", legacy_font)
            raw.setdefault("traditional_font_file", legacy_font)
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{key: value for key, value in raw.items() if key in allowed})

    def save(self) -> None:
        root = data_dir()
        root.mkdir(parents=True, exist_ok=True)
        temporary = root / "config.json.writing"
        temporary.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, root / "config.json")

    def font_size_scales(self) -> dict[str, float]:
        return {
            field.removesuffix("_scale"): float(getattr(self, field))
            for field, _ in FONT_SIZE_SETTINGS
        }

    def has_custom_font_sizes(self) -> bool:
        return any(
            abs(float(getattr(self, field)) - DEFAULT_FONT_SCALE) > 0.0001
            for field, _ in FONT_SIZE_SETTINGS
        )
