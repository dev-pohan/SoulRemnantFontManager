import os
import stat
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from srfontmanager.runtime import _replace_managed_executable


class RuntimeTests(TestCase):
    def test_replaces_read_only_executable_and_cleans_legacy_temporary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "downloaded.exe"
            target = root / "installed.exe"
            legacy = target.with_suffix(".exe.writing")
            source.write_bytes(b"new version")
            target.write_bytes(b"old version")
            legacy.write_bytes(b"stale update")
            target.chmod(target.stat().st_mode & ~stat.S_IWRITE)

            _replace_managed_executable(source, target)

            self.assertEqual(target.read_bytes(), b"new version")
            self.assertTrue(target.stat().st_mode & stat.S_IWRITE)
            self.assertFalse(legacy.exists())
            self.assertEqual(list(root.glob("*.writing")), [])

    def test_retries_a_transient_replace_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "downloaded.exe"
            target = root / "installed.exe"
            source.write_bytes(b"new version")
            target.write_bytes(b"old version")
            real_replace = os.replace
            attempts = 0

            def transient_lock(src, dst):
                nonlocal attempts
                attempts += 1
                if attempts == 1:
                    raise PermissionError(5, "file is briefly locked")
                return real_replace(src, dst)

            with patch("srfontmanager.runtime.os.replace", side_effect=transient_lock), patch(
                "srfontmanager.runtime.time.sleep"
            ) as sleep:
                _replace_managed_executable(source, target)

            self.assertEqual(attempts, 2)
            sleep.assert_called_once_with(0.25)
            self.assertEqual(target.read_bytes(), b"new version")
