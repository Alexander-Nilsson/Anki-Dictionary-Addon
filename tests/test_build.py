"""Packaging must fail loudly when required artifacts are missing."""

import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_BUILD_SCRIPT = Path(__file__).resolve().parents[1] / "build.py"
_spec = importlib.util.spec_from_file_location("addon_build", _BUILD_SCRIPT)
assert _spec is not None and _spec.loader is not None
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)


class BuildTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.previous = Path.cwd()
        os.chdir(self.tmp.name)
        self.addCleanup(os.chdir, self.previous)
        self.root = Path("addon")
        Path("web").mkdir()

    def test_missing_npm_stops_build(self) -> None:
        with patch.object(build.shutil, "which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "npm is required"):
                build.build_web_ui(self.root)

    def test_web_build_failure_is_fatal(self) -> None:
        failure = subprocess.CalledProcessError(1, "npm")
        with (
            patch.object(build.shutil, "which", return_value="/node/npm"),
            patch.object(build.subprocess, "run", side_effect=failure),
        ):
            with self.assertRaisesRegex(RuntimeError, "web UI build failed"):
                build.build_web_ui(self.root)

    def test_missing_settings_is_fatal(self) -> None:
        Path("web/dist").mkdir()
        Path("web/dist/dictionary.html").write_text("dictionary")
        with (
            patch.object(build.shutil, "which", return_value="/node/npm"),
            patch.object(build.subprocess, "run"),
        ):
            with self.assertRaisesRegex(RuntimeError, "settings.html"):
                build.build_web_ui(self.root)

    def test_all_three_pages_are_copied(self) -> None:
        Path("web/dist").mkdir()
        for name in ("dictionary", "settings", "exporter"):
            Path("web/dist", name + ".html").write_text(name)
        with (
            patch.object(build.shutil, "which", return_value="/node/npm"),
            patch.object(build.subprocess, "run") as run,
        ):
            self.assertTrue(build.build_web_ui(self.root))
            self.assertEqual(run.call_args_list[0].args[0][0], "/node/npm")
        copied = self.root / "assets" / "web" / "settings.html"
        self.assertEqual(copied.read_text(), "settings")

    def test_dependency_failure_stops_build(self) -> None:
        with patch.object(
            build,
            "run_pip_command",
            side_effect=RuntimeError("wheel not available"),
        ):
            with self.assertRaisesRegex(RuntimeError, "Could not bundle curl_cffi"):
                build.install_curl_cffi(self.root / "vendor")

    def test_dependency_target_is_python313(self) -> None:
        targets = {
            "aarch64-apple-darwin",
            "x86_64-apple-darwin",
            "x86_64-manylinux2014",
            "x86_64-pc-windows-msvc",
        }
        with patch.object(build, "run_pip_command") as install:
            build.install_curl_cffi(self.root / "vendor")
            self.assertEqual(install.call_count, 4)
            seen = set()
            for call in install.call_args_list:
                args = call.args[0]
                version = args[args.index("--python-version") + 1]
                self.assertEqual(version, "3.13")
                self.assertEqual(args.count("--platform"), 1)
                seen.add(args[args.index("--platform") + 1])
            self.assertEqual(seen, targets)

    def test_incomplete_build_cannot_be_packaged(self) -> None:
        Path("build/anki_dictionary_addon").mkdir(parents=True)
        with self.assertRaisesRegex(RuntimeError, "Build is incomplete"):
            build.create_ankiaddon_package()
        self.assertEqual(list(Path("build").glob("*.ankiaddon")), [])


if __name__ == "__main__":
    unittest.main()
