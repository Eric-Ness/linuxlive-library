"""Tests for scripts/check_listing.py's folder check.

    python -m unittest discover -s tests
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_listing  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 64
LISTING = {
    "name": "Test Distro",
    "author": "someone",
    "tagline": "A distro for the tests.",
    "about": "It exists so the listing check has something to look at.",
    "credits": "Nobody.",
    "license": "MIT",
}
SPLASH_SCRIPT = 'strip = Image("strip.png");\nsprite = Sprite(strip);\n'


class CheckFolderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.folder = root / "distros" / "test-distro"
        (self.folder / "assets").mkdir(parents=True)
        self._root = check_listing.ROOT
        check_listing.ROOT = root
        self.addCleanup(setattr, check_listing, "ROOT", self._root)
        self.spec = {
            "name": "Test Distro",
            "base": "ubuntu-24.04",
            "desktop": "gnome",
            "branding": {"wallpaper": "assets/wallpaper.png", "logo": "assets/logo.png"},
        }
        self.write("assets/wallpaper.png", PNG)
        self.write("assets/logo.png", PNG)
        self.write("listing.yaml", yaml.safe_dump(LISTING))

    def write(self, rel: str, data: bytes | str) -> None:
        path = self.folder / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)

    def problems(self) -> list[str]:
        self.write("linuxlive.yaml", yaml.safe_dump(self.spec))
        return check_listing.check_folder("test-distro", None)

    def add_splash(self, images: int = 1) -> None:
        names = [f"assets/splash/frame-{i:02}.png" for i in range(images)]
        self.write("assets/splash/splash.script", SPLASH_SCRIPT)
        for name in names:
            self.write(name, PNG)
        self.spec["branding"]["splash"] = {"script": "assets/splash/splash.script", "images": names}

    def test_plain_folder_passes(self):
        self.assertEqual(self.problems(), [])

    def test_splash_passes(self):
        self.add_splash()
        self.assertEqual(self.problems(), [])

    def test_splash_with_24_images_passes(self):
        self.add_splash(images=24)
        self.assertEqual(self.problems(), [])

    def test_splash_near_8_mb_passes(self):
        # The pipeline's limit is 8 MB for the script and images together.
        self.add_splash(images=4)
        for i in range(4):
            self.write(f"assets/splash/frame-{i:02}.png", PNG + b"\0" * (2 * 1024 * 1024 - 1024))
        self.assertEqual(self.problems(), [])

    def test_splash_script_must_be_named_file(self):
        self.add_splash()
        (self.folder / "assets/splash/splash.script").unlink()
        self.assertEqual(self.problems(), [
            "distros/test-distro: linuxlive.yaml: branding.splash.script 'assets/splash/splash.script' is not a file in this folder",
        ])

    def test_splash_image_must_be_named_file(self):
        self.add_splash()
        self.spec["branding"]["splash"]["images"].append("assets/splash/missing.png")
        self.assertEqual(self.problems(), [
            "distros/test-distro: linuxlive.yaml: branding.splash.images[1] 'assets/splash/missing.png' is not a file in this folder",
        ])

    def test_splash_outside_folder_refused(self):
        self.add_splash()
        self.spec["branding"]["splash"]["script"] = "../other/splash.script"
        self.assertEqual(self.problems(), [
            "distros/test-distro: linuxlive.yaml: branding.splash.script '../other/splash.script' is not a file in this folder",
        ])

    def test_splash_script_must_be_text(self):
        self.add_splash()
        self.write("assets/splash/splash.script", b"\x7fELF\0\0\0")
        self.assertEqual(self.problems(), [
            "distros/test-distro: assets/splash/splash.script: a splash script must be a text file of at most 64 KB",
        ])

    def test_splash_script_size_limit(self):
        self.add_splash()
        self.write("assets/splash/splash.script", "#" * (64 * 1024 + 1))
        self.assertEqual(len(self.problems()), 1)

    def test_splash_image_must_be_png(self):
        self.add_splash()
        self.write("assets/splash/frame-00.png", b"GIF89a")
        self.assertEqual(self.problems(), ["distros/test-distro: assets/splash/frame-00.png is not really a PNG file"])

    def test_script_outside_assets_refused(self):
        self.write("splash.script", SPLASH_SCRIPT)
        self.assertEqual(len(self.problems()), 1)
        self.assertIn("splash.script: only linuxlive.yaml", self.problems()[0])

    def test_dock_passes(self):
        apps = [f"app-{i}" for i in range(10)] + ["org.gnome.Calculator", "org.gimp.GIMP"]
        self.spec["apps"] = apps[:10]
        self.spec["flathub"] = apps[10:]
        self.spec["settings"] = {"dock": apps}
        self.assertEqual(self.problems(), [])

    def test_splash_and_dock_together_pass(self):
        self.add_splash(images=3)
        self.spec["apps"] = ["firefox", "gimp"]
        self.spec["settings"] = {"dock": ["firefox", "gimp"]}
        self.assertEqual(self.problems(), [])


class LibraryFoldersTest(unittest.TestCase):
    def test_every_listed_distro_passes(self):
        for folder in sorted((check_listing.ROOT / "distros").iterdir()):
            if folder.is_dir():
                with self.subTest(slug=folder.name):
                    self.assertEqual(check_listing.check_folder(folder.name, None), [])


if __name__ == "__main__":
    unittest.main()
