from __future__ import annotations

import hashlib
import io
import json
import os
import struct
import zipfile
from dataclasses import dataclass
from pathlib import Path

HEADER_SIZE = 40
ALIGNMENT = 16
PCK_NAME = "Soul's Remnant.pck"
JOURNAL_NAME = "Soul's Remnant.pck.srfontmod-rollback.zip"
TEMP_NAME = "Soul's Remnant.pck.srfontmod-installing"


@dataclass
class PckInfo:
    header: bytearray
    version: tuple[int, int, int]
    file_base: int
    directory_offset: int
    directory: bytearray
    entries: dict[str, tuple[int, int]]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_exact(source: io.BufferedReader, destination: io.BufferedWriter, length: int) -> None:
    remaining = length
    while remaining:
        chunk = source.read(min(8 * 1024 * 1024, remaining))
        if not chunk:
            raise EOFError(f"PCK 提前結束，仍缺少 {remaining} bytes")
        destination.write(chunk)
        remaining -= len(chunk)


def parse_pck(path: Path) -> PckInfo:
    with path.open("rb") as stream:
        header = bytearray(stream.read(HEADER_SIZE))
        if len(header) != HEADER_SIZE or header[:4] != b"GDPC":
            raise ValueError(f"不是 Godot PCK：{path}")
        pack_format, major, minor, patch, flags = struct.unpack_from("<5I", header, 4)
        if pack_format != 4:
            raise ValueError(f"僅支援 PCK format 4，目前為 {pack_format}")
        if flags & 1:
            raise ValueError("不支援加密的 PCK 目錄")
        file_base, directory_offset = struct.unpack_from("<2Q", header, 24)
        if directory_offset < HEADER_SIZE or directory_offset >= path.stat().st_size:
            raise ValueError("PCK 目錄位置無效")
        stream.seek(directory_offset)
        directory = bytearray(stream.read())

    return _info_from_parts(header, directory_offset, directory)


def _info_from_parts(header: bytearray, directory_offset: int, directory: bytearray) -> PckInfo:
    if len(directory) < 4:
        raise ValueError("PCK 目錄已損毀")
    pack_format, major, minor, patch, flags = struct.unpack_from("<5I", header, 4)
    if pack_format != 4 or flags & 1:
        raise ValueError("不支援的 PCK header")
    file_base = struct.unpack_from("<Q", header, 24)[0]
    cursor = 0
    count = struct.unpack_from("<I", directory, cursor)[0]
    cursor += 4
    entries: dict[str, tuple[int, int]] = {}
    for _ in range(count):
        if cursor + 4 > len(directory):
            raise ValueError("PCK 目錄已截斷")
        path_length = struct.unpack_from("<I", directory, cursor)[0]
        cursor += 4
        if path_length > len(directory) - cursor:
            raise ValueError("PCK 路徑長度無效")
        internal = bytes(directory[cursor : cursor + path_length]).rstrip(b"\0").decode("utf-8")
        cursor += path_length
        if cursor + 36 > len(directory):
            raise ValueError("PCK 項目已截斷")
        flags = struct.unpack_from("<I", directory, cursor + 32)[0]
        entries[internal] = (cursor, flags)
        cursor += 36
    return PckInfo(header, (major, minor, patch), file_base, directory_offset, directory, entries)


def read_base_entries(game_dir: Path, names: list[str]) -> dict[str, bytes]:
    """Read entries from the unmodified base, including while our delta is installed."""
    pck, journal, _ = _paths(game_dir)
    info: PckInfo
    if journal.is_file():
        metadata, header, directory = _read_journal(journal)
        current = sha256_file(pck)
        if current in {metadata.get("patched_sha256"), metadata.get("original_sha256")}:
            info = _info_from_parts(
                bytearray(header),
                int(metadata["original_directory_offset"]),
                bytearray(directory),
            )
        else:
            info = parse_pck(pck)
    else:
        info = parse_pck(pck)
    result: dict[str, bytes] = {}
    with pck.open("rb") as stream:
        for name in names:
            if name not in info.entries:
                raise ValueError(f"遊戲版本不相容，缺少：{name}")
            fields, flags = info.entries[name]
            if flags & 1:
                raise ValueError(f"不支援加密項目：{name}")
            relative_offset, size = struct.unpack_from("<2Q", info.directory, fields)
            stream.seek(info.file_base + relative_offset)
            data = stream.read(size)
            if len(data) != size:
                raise EOFError(f"PCK 項目已截斷：{name}")
            result[name] = data
    return result


def base_entry_names(game_dir: Path) -> list[str]:
    pck, journal, _ = _paths(game_dir)
    if journal.is_file():
        metadata, header, directory = _read_journal(journal)
        current = sha256_file(pck)
        if current in {metadata.get("patched_sha256"), metadata.get("original_sha256")}:
            return sorted(
                _info_from_parts(
                    bytearray(header),
                    int(metadata["original_directory_offset"]),
                    bytearray(directory),
                ).entries
            )
    return sorted(parse_pck(pck).entries)


def _payload_digest(payload: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for name, data in sorted(payload.items()):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(data)
    return digest.hexdigest()


def _write_journal(path: Path, metadata: dict, info: PckInfo) -> None:
    temporary = path.with_suffix(path.suffix + ".writing")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2))
        archive.writestr("header.bin", info.header)
        archive.writestr("directory.bin", info.directory)
    os.replace(temporary, path)


def _read_journal(path: Path) -> tuple[dict, bytes, bytes]:
    with zipfile.ZipFile(path, "r") as archive:
        return (
            json.loads(archive.read("metadata.json")),
            archive.read("header.bin"),
            archive.read("directory.bin"),
        )


def _paths(game_dir: Path) -> tuple[Path, Path, Path]:
    root = game_dir.expanduser().resolve()
    paths = (root / PCK_NAME, root / JOURNAL_NAME, root / TEMP_NAME)
    if any(not path.resolve().is_relative_to(root) for path in paths):
        raise ValueError("不安全的遊戲路徑")
    return paths


def _build_patched(base: Path, output: Path, payload: dict[str, bytes]) -> PckInfo:
    info = parse_pck(base)
    for internal_path in payload:
        if internal_path not in info.entries:
            raise ValueError(f"遊戲版本不相容，缺少：{internal_path}")
        _, flags = info.entries[internal_path]
        if flags & 1:
            raise ValueError(f"不支援加密項目：{internal_path}")

    with base.open("rb") as source, output.open("wb") as destination:
        _copy_exact(source, destination, info.directory_offset)
        for internal_path, data in payload.items():
            relative_offset = destination.tell() - info.file_base
            destination.write(data)
            destination.write(b"\0" * ((-destination.tell()) % ALIGNMENT))
            fields, _ = info.entries[internal_path]
            struct.pack_into("<Q", info.directory, fields, relative_offset)
            struct.pack_into("<Q", info.directory, fields + 8, len(data))
            info.directory[fields + 16 : fields + 32] = hashlib.md5(data).digest()
        new_directory_offset = destination.tell()
        destination.write(info.directory)
        struct.pack_into("<Q", info.header, 32, new_directory_offset)
        destination.seek(0)
        destination.write(info.header)
        destination.flush()
        os.fsync(destination.fileno())
    return info


def _restore_to(pck: Path, temporary: Path, metadata: dict, header: bytes, directory: bytes) -> None:
    with pck.open("rb") as source, temporary.open("wb") as destination:
        _copy_exact(source, destination, int(metadata["original_directory_offset"]))
        destination.write(directory)
        destination.seek(0)
        destination.write(header)
        destination.truncate(int(metadata["original_size"]))
        destination.flush()
        os.fsync(destination.fileno())
    if sha256_file(temporary) != metadata["original_sha256"]:
        temporary.unlink(missing_ok=True)
        raise RuntimeError("還原檔雜湊驗證失敗")


def install(game_dir: Path, payload: dict[str, bytes]) -> str:
    pck, journal, temporary = _paths(game_dir)
    if not pck.is_file():
        raise FileNotFoundError(f"找不到遊戲 PCK：{pck}")
    desired_digest = _payload_digest(payload)
    current_hash = sha256_file(pck)

    if journal.is_file():
        old_metadata, old_header, old_directory = _read_journal(journal)
        if current_hash == old_metadata.get("patched_sha256"):
            if old_metadata.get("payload_sha256") == desired_digest:
                return "already-installed"
            temporary.unlink(missing_ok=True)
            _restore_to(pck, temporary, old_metadata, old_header, old_directory)
            os.replace(temporary, pck)
            current_hash = old_metadata["original_sha256"]
        elif current_hash != old_metadata.get("original_sha256"):
            # Steam supplied a new PCK. Its directory becomes the new rollback base.
            journal.unlink()

    temporary.unlink(missing_ok=True)
    original_info = parse_pck(pck)
    original_hash = sha256_file(pck)
    _build_patched(pck, temporary, payload)
    patched_hash = sha256_file(temporary)
    metadata = {
        "format": 1,
        "payload_sha256": desired_digest,
        "godot_version": list(original_info.version),
        "original_sha256": original_hash,
        "patched_sha256": patched_hash,
        "original_size": pck.stat().st_size,
        "original_directory_offset": original_info.directory_offset,
    }
    _write_journal(journal, metadata, original_info)
    os.replace(temporary, pck)
    if sha256_file(pck) != patched_hash:
        raise RuntimeError("安裝後的 PCK 雜湊驗證失敗")
    return "installed"


def uninstall(game_dir: Path) -> str:
    pck, journal, temporary = _paths(game_dir)
    if not journal.is_file():
        return "not-installed"
    metadata, header, directory = _read_journal(journal)
    current_hash = sha256_file(pck)
    if current_hash == metadata["original_sha256"]:
        journal.unlink(missing_ok=True)
        return "already-restored"
    if current_hash != metadata["patched_sha256"]:
        raise ValueError("目前 PCK 並非本工具安裝的版本，為安全起見拒絕還原")
    temporary.unlink(missing_ok=True)
    _restore_to(pck, temporary, metadata, header, directory)
    os.replace(temporary, pck)
    journal.unlink()
    return "restored"


def status(game_dir: Path) -> str:
    pck, journal, _ = _paths(game_dir)
    if not pck.is_file():
        return "game-not-found"
    if not journal.is_file():
        return "not-installed"
    metadata, _, _ = _read_journal(journal)
    current = sha256_file(pck)
    if current == metadata.get("patched_sha256"):
        return "installed"
    if current == metadata.get("original_sha256"):
        return "restored"
    return "steam-update-detected"
