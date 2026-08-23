from __future__ import annotations

import ctypes
import os
import platform
import sys


def ensure_console() -> None:
    if platform.system() != "Windows" or not getattr(sys, "frozen", False):
        return
    kernel32 = ctypes.windll.kernel32
    if kernel32.GetConsoleWindow() == 0:
        kernel32.AllocConsole()
    kernel32.SetConsoleOutputCP(65001)
    kernel32.SetConsoleCP(65001)
    sys.stdin = open("CONIN$", "r", encoding="utf-8", errors="replace")
    sys.stdout = open("CONOUT$", "w", encoding="utf-8", errors="replace", buffering=1)
    sys.stderr = open("CONOUT$", "w", encoding="utf-8", errors="replace", buffering=1)
    os.system("title Soul's Remnant Font Manager")

