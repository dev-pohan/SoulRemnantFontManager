from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import webbrowser
from contextlib import contextmanager
from pathlib import Path

from . import __version__
from .config import DEFAULT_FONT_SCALE, FONT_SIZE_SETTINGS, Settings, data_dir
from .console import ensure_console
from .font import clear_font, install_font, validate_font
from .payload import build_payload, payload_paths
from . import pck, steam
from .runtime import (
    executable_name,
    install_executable,
    launch_options,
    refresh_existing_install,
    remove_managed_files,
)

FREE_FONT_URL = "https://font.emtech.cc/"


def main() -> None:
    if "--prelaunch" in sys.argv:
        raise SystemExit(_prelaunch_entry(sys.argv))
    ensure_console()
    startup_notice = ""
    try:
        if refresh_existing_install():
            startup_notice = "已自動更新 Steam 使用的 prelaunch Manager。"
    except OSError as exc:
        startup_notice = f"警告：無法更新已安裝的 Manager：{exc}"
    parser = argparse.ArgumentParser(description="Soul's Remnant 字型管理器")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--status", action="store_true", help="顯示目前狀態")
    args = parser.parse_args()
    try:
        if args.status:
            print_status(Settings.load())
        else:
            menu(startup_notice)
    except KeyboardInterrupt:
        print("\n已取消。")
    except Exception as exc:
        print(f"\n錯誤：{exc}")
        _pause()


def menu(startup_notice: str = "") -> None:
    first_screen = True
    while True:
        _clear_screen()
        settings = Settings.load()
        print("\nSoul's Remnant 字型管理器")
        print(f"版本 {__version__}")
        print("=" * 34)
        if first_screen and startup_notice:
            print(startup_notice)
            print()
        first_screen = False
        print("1. 快速安裝／修復")
        print("2. 設定點陣模式字型（遊戲選項：字體＝點陣）")
        print("3. 設定傳統模式字型（遊戲選項：字體＝傳統）")
        print("4. 設定字體大小")
        print("5. 開啟免費字型網站")
        print("6. 狀態檢查")
        print("7. 解除安裝")
        print("0. 離開")
        choice = input("\n請選擇：").strip()
        try:
            if choice == "1":
                interactive_install(settings)
            elif choice == "2":
                configure_font(settings, "pixel", "點陣")
            elif choice == "3":
                configure_font(settings, "traditional", "傳統")
            elif choice == "4":
                configure_font_sizes(settings)
                continue
            elif choice == "5":
                open_free_font_site()
            elif choice == "6":
                print_status(settings)
            elif choice == "7":
                interactive_uninstall(settings)
            elif choice == "0":
                return
            else:
                print("無效的選項。")
        except Exception as exc:
            print(f"\n操作失敗：{exc}")
        _pause()


def configure_font(settings: Settings, slot: str, label: str) -> None:
    field = f"{slot}_font_file"
    current = getattr(settings, field)
    print(f"{label}模式目前字型：{current or '遊戲內建'}")
    raw = input("請輸入 .ttf／.otf 完整路徑；留空使用遊戲內建：").strip().strip('"')
    if raw:
        installed = install_font(Path(raw), slot)
        setattr(settings, field, str(installed))
        print(f"{label}模式字型已複製至：{installed}")
    else:
        clear_font(slot)
        setattr(settings, field, "")
        print(f"{label}模式已改用遊戲內建字型。")
    settings.save()
    print(f"點陣（遊戲選項：字體＝點陣）：{settings.pixel_font_file or '遊戲內建'}")
    print(f"傳統（遊戲選項：字體＝傳統）：{settings.traditional_font_file or '遊戲內建'}")
    if settings.game_dir and pck.status(Path(settings.game_dir)) == "installed":
        result = _apply_patch(settings)
        print(f"遊戲補丁已更新：{result}")


def open_free_font_site() -> None:
    print(f"正在使用預設瀏覽器開啟：{FREE_FONT_URL}")
    if not webbrowser.open(FREE_FONT_URL, new=2):
        print("無法自動開啟瀏覽器，請複製上方網址手動開啟。")


def configure_font_sizes(settings: Settings) -> None:
    while True:
        _clear_screen()
        print("\n字體大小設定")
        print("預設倍率：1.00×（保留遊戲原始大小）")
        print("=" * 42)
        for index, (field, label) in enumerate(FONT_SIZE_SETTINGS, 1):
            print(f"{index}. {label}：目前 {float(getattr(settings, field)):.2f}×／預設 1.00×")
        print("7. 全部設定為相同倍率")
        print("8. 全部恢復預設")
        print("0. 返回主選單")
        choice = input("\n請選擇：").strip()
        if choice == "0":
            return
        if choice == "7":
            current_values = {float(getattr(settings, field)) for field, _ in FONT_SIZE_SETTINGS}
            current_text = (
                f"{next(iter(current_values)):.2f}×"
                if len(current_values) == 1
                else "各分類不同"
            )
            print("\n全部字體大小")
            print(f"目前大小：{current_text}")
            print(f"預設大小：{DEFAULT_FONT_SCALE:.2f}×")
            raw = input("輸入共同倍率（0.10～3.00）；D 恢復預設；留空取消：").strip().lower()
            if not raw:
                continue
            try:
                value = DEFAULT_FONT_SCALE if raw == "d" else float(raw)
            except ValueError:
                print("請輸入數字、D 或留空。")
                _pause()
                continue
            if not 0.10 <= value <= 3.00:
                print("倍率必須介於 0.10～3.00。")
                _pause()
                continue
            for field, _ in FONT_SIZE_SETTINGS:
                setattr(settings, field, value)
            settings.save()
            _refresh_patch_after_setting(settings)
            print(f"六類字體大小已全部設定為 {value:.2f}×（預設 1.00×）。")
            _pause()
            continue
        if choice == "8":
            for field, _ in FONT_SIZE_SETTINGS:
                setattr(settings, field, DEFAULT_FONT_SCALE)
            settings.save()
            _refresh_patch_after_setting(settings)
            print("所有字體大小已恢復預設 1.00×。")
            _pause()
            continue
        try:
            index = int(choice) - 1
        except ValueError:
            print("無效的選項。")
            _pause()
            continue
        if not 0 <= index < len(FONT_SIZE_SETTINGS):
            print("無效的選項。")
            _pause()
            continue
        field, label = FONT_SIZE_SETTINGS[index]
        current = float(getattr(settings, field))
        print(f"\n{label}")
        print(f"目前大小：{current:.2f}×")
        print(f"預設大小：{DEFAULT_FONT_SCALE:.2f}×")
        raw = input("輸入新倍率（0.10～3.00）；D 恢復預設；留空取消：").strip().lower()
        if not raw:
            continue
        try:
            value = DEFAULT_FONT_SCALE if raw == "d" else float(raw)
        except ValueError:
            print("請輸入數字、D 或留空。")
            _pause()
            continue
        if not 0.10 <= value <= 3.00:
            print("倍率必須介於 0.10～3.00。")
            _pause()
            continue
        setattr(settings, field, value)
        settings.save()
        _refresh_patch_after_setting(settings)
        print(f"{label}已設定為 {value:.2f}×（預設 {DEFAULT_FONT_SCALE:.2f}×）。")
        _pause()


def _refresh_patch_after_setting(settings: Settings) -> None:
    if settings.game_dir and pck.status(Path(settings.game_dir)) == "installed":
        result = _apply_patch(settings)
        print(f"遊戲補丁已更新：{result}")


def interactive_install(settings: Settings) -> None:
    for configured in (settings.pixel_font_file, settings.traditional_font_file):
        if configured:
            validate_font(Path(configured))

    detected = steam.find_game_dir()
    game = Path(settings.game_dir) if settings.game_dir else detected
    if game is None or not (game / pck.PCK_NAME).is_file():
        default = str(detected or "")
        raw = input(f"遊戲資料夾{f' [{default}]' if default else ''}：").strip().strip('"')
        game = Path(raw or default).expanduser().resolve()
    if not (game / pck.PCK_NAME).is_file():
        raise FileNotFoundError(f"資料夾內找不到 {pck.PCK_NAME}")

    configs = steam.user_configs()
    if not configs:
        raise FileNotFoundError("找不到包含此遊戲的 Steam localconfig.vdf")
    config = _choose_config(configs)
    restart_steam = _close_steam_for_operation()
    try:
        settings.game_dir = str(game)
        settings.steam_user_config = str(config)
        settings.save()
        result = _apply_patch(settings)
        installed_executable = install_executable()
        new_options = launch_options(installed_executable)
        previous = steam.get_launch_options(config)
        if previous != new_options:
            settings.previous_launch_options = previous
            steam.set_launch_options(config, new_options)
        settings.installed_launch_options = new_options
        settings.save()
    finally:
        if restart_steam:
            _start_steam(restart_steam)
    print(f"安裝完成（PCK：{result}）")
    print(f"Steam 啟動選項：{new_options}")
    if restart_steam:
        print("Steam 已重新開啟。")
    else:
        print("現在可開啟 Steam，之後每次啟動都會先檢查並套用字型。")


def interactive_uninstall(settings: Settings) -> None:
    if input("確定解除安裝？輸入 YES：").strip() != "YES":
        print("已取消。")
        return
    restart_steam = _close_steam_for_operation()
    try:
        if settings.steam_user_config:
            config = Path(settings.steam_user_config)
            if config.is_file():
                current = steam.get_launch_options(config)
                if current == settings.installed_launch_options:
                    steam.set_launch_options(config, settings.previous_launch_options)
                else:
                    print("Steam 啟動選項已被其他程式或使用者修改，因此保留不動。")
        if settings.game_dir:
            print(f"PCK：{pck.uninstall(Path(settings.game_dir))}")
        _remove_installation()
    finally:
        if restart_steam:
            _start_steam(restart_steam)
    print("解除安裝完成。")


def print_status(settings: Settings) -> None:
    state = pck.status(Path(settings.game_dir)) if settings.game_dir else "not-configured"
    print(f"管理資料夾：{data_dir()}")
    print(f"遊戲資料夾：{settings.game_dir or '尚未設定'}")
    print(f"點陣模式字型（遊戲選項：字體＝點陣）：{settings.pixel_font_file or '遊戲內建'}")
    print(f"傳統模式字型（遊戲選項：字體＝傳統）：{settings.traditional_font_file or '遊戲內建'}")
    print("字體大小：")
    for field, label in FONT_SIZE_SETTINGS:
        print(f"  {label}：{float(getattr(settings, field)):.2f}×（預設 1.00×）")
    print(f"PCK 狀態：{state}")


def _apply_patch(settings: Settings) -> str:
    game_dir = Path(settings.game_dir)
    pixel = Path(settings.pixel_font_file) if settings.pixel_font_file else None
    traditional = Path(settings.traditional_font_file) if settings.traditional_font_file else None
    for configured in (pixel, traditional):
        if configured is not None:
            validate_font(configured)
    if pixel is None and traditional is None and not settings.has_custom_font_sizes():
        return "built-in-fonts:" + pck.uninstall(game_dir)
    source = pck.read_base_entries(game_dir, payload_paths())
    payload = build_payload(source, pixel, traditional, settings.font_size_scales())
    return pck.install(Path(settings.game_dir), payload)


def _prelaunch_entry(argv: list[str]) -> int:
    log_dir = data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log = log_dir / "prelaunch.log"
    separator = argv.index("--") if "--" in argv else len(argv)
    command = argv[separator + 1 :] if separator < len(argv) else []
    try:
        settings = Settings.load()
        with _single_instance_lock():
            result = _apply_patch(settings)
        _log(log, f"PCK={result}")
        if not command:
            raise ValueError("Steam 未提供遊戲啟動命令")
        return subprocess.run(command, check=False).returncode
    except Exception:
        _log(log, traceback.format_exc())
        return 1


@contextmanager
def _single_instance_lock():
    lock = data_dir() / "prelaunch.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        if time.time() - lock.stat().st_mtime > 600:
            lock.unlink(missing_ok=True)
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        else:
            raise RuntimeError("另一個 prelaunch 正在執行")
    try:
        os.write(descriptor, str(os.getpid()).encode("ascii"))
        os.close(descriptor)
        yield
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass
        lock.unlink(missing_ok=True)


def _choose_config(configs: list[Path]) -> Path:
    if len(configs) == 1:
        return configs[0]
    print("找到多個曾執行此遊戲的 Steam 帳號：")
    for index, config in enumerate(configs, 1):
        print(f"{index}. {config}")
    choice = int(input("請選擇帳號 [1]：").strip() or "1")
    if not 1 <= choice <= len(configs):
        raise ValueError("帳號選項無效")
    return configs[choice - 1]


def _steam_running() -> bool:
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq steam.exe", "/NH"],
                capture_output=True,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return "steam.exe" in result.stdout.lower()
        names = ("steam_osx",) if platform.system() == "Darwin" else ("steam",)
        return any(
            subprocess.run(["pgrep", "-x", name], capture_output=True).returncode == 0
            for name in names
        )
    except OSError:
        return False


def _close_steam_for_operation() -> Path | None:
    if not _steam_running():
        return None
    answer = input("Steam 目前正在執行。是否由 Manager 正常關閉並在完成後重開？ [Y/n]：").strip().lower()
    if answer not in {"", "y", "yes"}:
        raise RuntimeError("必須先完整結束 Steam，否則 Steam 可能覆寫啟動選項")
    executable = steam.client_executable()
    if executable is None:
        raise FileNotFoundError("找不到 Steam 主程式，無法安全地要求 Steam 關閉")
    print("正在等待 Steam 正常結束", end="", flush=True)
    try:
        subprocess.Popen(
            [str(executable), "-shutdown"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError as exc:
        raise RuntimeError(f"無法要求 Steam 關閉：{exc}") from exc
    deadline = time.monotonic() + 45
    while _steam_running() and time.monotonic() < deadline:
        print(".", end="", flush=True)
        time.sleep(1)
    print()
    if _steam_running():
        raise RuntimeError("Steam 在 45 秒內沒有結束；不會強制終止，請檢查下載或執行中的遊戲")
    return executable


def _start_steam(executable: Path) -> None:
    try:
        subprocess.Popen(
            [str(executable)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError as exc:
        print(f"安裝已完成，但無法自動重開 Steam：{exc}")


def _remove_installation() -> None:
    installed = data_dir() / "bin" / executable_name()
    current = Path(sys.executable).resolve()
    if platform.system() == "Windows" and getattr(sys, "frozen", False) and current == installed.resolve():
        remove_managed_files(keep_executable=current)
        script = Path(tempfile.gettempdir()) / f"srfontmanager-cleanup-{os.getpid()}.cmd"
        lines = [
            "@echo off",
            ":retry",
            f'del /f /q "{current}" >nul 2>&1',
            f'if exist "{current}" (ping 127.0.0.1 -n 2 >nul & goto retry)',
            f'rmdir "{current.parent}" >nul 2>&1',
            f'rmdir "{data_dir()}" >nul 2>&1',
            'del /f /q "%~f0"',
        ]
        script.write_text("\r\n".join(lines), encoding="utf-8")
        subprocess.Popen(
            ["cmd.exe", "/d", "/c", str(script)],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    else:
        remove_managed_files()


def _log(path: Path, message: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with path.open("a", encoding="utf-8") as stream:
        stream.write(f"[{timestamp}] {message.rstrip()}\n")


def _pause() -> None:
    input("\n按 Enter 繼續……")


def _clear_screen() -> None:
    os.system("cls" if platform.system() == "Windows" else "clear")


if __name__ == "__main__":
    main()
