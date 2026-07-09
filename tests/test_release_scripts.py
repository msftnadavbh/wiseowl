import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReleaseScriptTests(unittest.TestCase):
    def test_verify_release_passes_current_repo(self):
        verify_release = load_script("verify_release")
        self.assertEqual(verify_release.validate(ROOT), [])

    def test_archive_excludes_generated_paths(self):
        build_release_archive = load_script("build_release_archive")
        self.assertFalse(build_release_archive.should_include(ROOT / "__pycache__" / "x.pyc"))
        self.assertFalse(build_release_archive.should_include(ROOT / ".env"))
        self.assertTrue(build_release_archive.should_include(ROOT / "README.md"))

    def test_archive_surface_matches_documented_files(self):
        build_release_archive = load_script("build_release_archive")
        files = {path.as_posix() for path in build_release_archive.iter_files(ROOT)}
        expected = {
            "install.py",
            ".gitignore",
            "assets/wise-owl-logo.png",
            "assets/wise-owl-logo-transparent.png",
            "assets/wise-owl-workflow.svg",
            "assets/wise-owl-workflow.png",
            "assets/wise-owl-install.svg",
            "assets/wise-owl-install.png",
            "assets/wise-owl-cli-demo.gif",
            "docs/demo-transcript.md",
            "scripts/render_cli_demo.mjs",
            "wise-owl-plugin/assets/wise-owl-logo.png",
            "wise-owl-plugin/assets/wise-owl-logo-transparent.png",
            "wise-owl-plugin/assets/wise-owl-workflow.svg",
            "wise-owl-plugin/assets/wise-owl-workflow.png",
            "wise-owl-plugin/scripts/install_wise_owl.py",
        }
        self.assertTrue(expected.issubset(files))
        self.assertFalse(any(path.startswith("dist/") for path in files))
        self.assertFalse(any("__pycache__" in path for path in files))

    def test_public_docs_do_not_contain_local_user_paths_or_em_dashes(self):
        public_files = [
            ROOT / "README.md",
            ROOT / "AGENTS.md",
            ROOT / "CHANGELOG.md",
            ROOT / "MANIFEST.md",
            ROOT / "wise-owl-plugin" / ".codex-plugin" / "plugin.json",
            ROOT / ".agents" / "skills" / "wise-owl" / "SKILL.md",
        ]
        public_files.extend((ROOT / "docs").glob("*.md"))
        for path in public_files:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("/Users/", text, str(path))
            self.assertNotIn("\u2014", text, str(path))
            self.assertNotIn("\u2013", text, str(path))


if __name__ == "__main__":
    unittest.main()
