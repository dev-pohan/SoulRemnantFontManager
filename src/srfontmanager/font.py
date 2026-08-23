from __future__ import annotations

import os
import shutil
import struct
from pathlib import Path

from .config import data_dir

SUPPORTED_SUFFIXES = {".ttf", ".otf"}


def validate_font(path: Path) -> None:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"找不到字型：{path}")
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValueError("目前僅支援 .ttf 與 .otf")
    size = path.stat().st_size
    if size < 12 or size > 128 * 1024 * 1024:
        raise ValueError("字型檔案大小不合理")
    with path.open("rb") as stream:
        signature = stream.read(4)
        if signature not in {b"\x00\x01\x00\x00", b"OTTO", b"true", b"ttcf"}:
            raise ValueError("檔案不是有效的 TrueType/OpenType 字型")
        if signature == b"ttcf":
            stream.seek(8)
            if len(stream.read(4)) != 4:
                raise ValueError("TrueType Collection 已損毀")
        elif signature in {b"\x00\x01\x00\x00", b"OTTO", b"true"}:
            table_count = struct.unpack(">H", stream.read(2))[0]
            if not 1 <= table_count <= 4096:
                raise ValueError("字型資料表數量不合理")


def install_font(source: Path, slot: str) -> Path:
    if slot not in {"pixel", "traditional"}:
        raise ValueError("未知的字型設定欄位")
    source = source.expanduser().resolve()
    validate_font(source)
    target_dir = data_dir() / "fonts"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / (slot + source.suffix.lower())
    temporary = target.with_suffix(target.suffix + ".writing")
    shutil.copyfile(source, temporary)
    os.replace(temporary, target)
    for stale in target_dir.glob(slot + ".*"):
        if stale != target:
            stale.unlink(missing_ok=True)
    return target


def clear_font(slot: str) -> None:
    if slot not in {"pixel", "traditional"}:
        raise ValueError("未知的字型設定欄位")
    target_dir = data_dir() / "fonts"
    if target_dir.is_dir():
        for target in target_dir.glob(slot + ".*"):
            target.unlink(missing_ok=True)
