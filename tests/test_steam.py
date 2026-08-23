import tempfile
from pathlib import Path
from unittest import TestCase

from srfontmanager import steam


class SteamTests(TestCase):
    def test_preserves_file_and_updates_only_app_block(self):
        text = '''"UserLocalConfigStore"\n{\n\t"Software"\n\t{\n\t\t"Valve"\n\t\t{\n\t\t\t"Steam"\n\t\t\t{\n\t\t\t\t"apps"\n\t\t\t\t{\n\t\t\t\t\t"3451980"\n\t\t\t\t\t{\n\t\t\t\t\t\t"LaunchOptions" "old %command%"\n\t\t\t\t\t}\n\t\t\t\t\t"1" { "LaunchOptions" "keep" }\n\t\t\t\t}\n\t\t\t}\n\t\t}\n\t}\n}\n'''
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "localconfig.vdf"
            path.write_text(text, encoding="utf-8")
            steam.set_launch_options(path, '"C:\\Tool\\manager.exe" --prelaunch -- %command%')
            self.assertIn("manager.exe", steam.get_launch_options(path))
            self.assertIn('"1" { "LaunchOptions" "keep" }', path.read_text(encoding="utf-8"))
            self.assertTrue(path.with_suffix(".vdf.srfontmanager.bak").is_file())

