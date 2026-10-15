import tempfile
import unittest
from pathlib import Path

from scripts.install_picker_label import OLD, NEW, install


class PickerLabelTests(unittest.TestCase):
    def test_only_mapping_changes_and_backup_survives_repeat(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            web = root / "web"
            (web / "assets").mkdir(parents=True)
            html = '<script type="module" src="/assets/index-example.js"></script>'
            (web / "index.html").write_text(html)
            asset = web / "assets/index-example.js"
            original = b"/*before*/" + OLD + b";/*after*/"
            asset.write_bytes(original)
            backup = root / "backup"
            result = install(web, backup)
            self.assertEqual(result["action"], "installed")
            self.assertEqual(asset.read_bytes(), b"/*before*/" + NEW + b";/*after*/")
            self.assertEqual(Path(result["backup"]).read_bytes(), original)
            self.assertEqual((web / "index.html").read_text(), html)
            self.assertEqual(install(web, backup)["action"], "already_installed")

    def test_unrecognized_bundle_is_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets").mkdir()
            (root / "index.html").write_text('<script src="/assets/index-other.js"></script>')
            asset = root / "assets/index-other.js"
            asset.write_bytes(b"different-build")
            with self.assertRaises(ValueError):
                install(root, root / "backup")
            self.assertEqual(asset.read_bytes(), b"different-build")


if __name__ == "__main__":
    unittest.main()
