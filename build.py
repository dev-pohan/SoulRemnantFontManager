from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
name = "SoulRemnantFontManager" if platform.system() == "Windows" else "soul-remnant-font-manager"

command = [
    sys.executable,
    "-m",
    "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onefile",
    "--name",
    name,
    "--paths",
    str(ROOT / "src"),
]
if platform.system() == "Windows":
    command.append("--noconsole")
command.append(str(ROOT / "src" / "srfontmanager" / "__main__.py"))
subprocess.run(command, cwd=ROOT, check=True)
