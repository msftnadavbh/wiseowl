import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


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

    def test_release_requires_core_test_modules(self):
        verify_release = load_script("verify_release")
        for relative in (
            "tests/test_release_scripts.py",
            "tests/test_wise_owl_install.py",
            "tests/test_wise_owl_validate_packet.py",
        ):
            with self.subTest(relative=relative):
                self.assertIn(relative, verify_release.REQUIRED_FILES)

    def test_unit_test_checks_reject_zero_discovered_tests(self):
        verify_release = load_script("verify_release")
        with mock.patch.object(verify_release, "run_command", return_value=(0, "", "Ran 0 tests in 0.000s\n\nOK\n")):
            errors = verify_release.unit_test_checks(ROOT)
        self.assertEqual(errors, ["unit test discovery reported zero tests"])

    def test_unit_test_checks_reject_missing_test_summary(self):
        verify_release = load_script("verify_release")
        with mock.patch.object(verify_release, "run_command", return_value=(0, "", "OK\n")):
            errors = verify_release.unit_test_checks(ROOT)
        self.assertEqual(errors, ["unit test discovery did not report a test count"])

    def test_unit_test_checks_ignore_positive_summary_lookalike_on_stdout(self):
        verify_release = load_script("verify_release")
        with mock.patch.object(
            verify_release,
            "run_command",
            return_value=(0, "Ran 123 tests in 1.234s\n", "OK\n"),
        ):
            errors = verify_release.unit_test_checks(ROOT)
        self.assertEqual(errors, ["unit test discovery did not report a test count"])

    def test_unit_test_checks_use_real_stderr_summary_over_stdout_lookalike(self):
        verify_release = load_script("verify_release")
        with mock.patch.object(
            verify_release,
            "run_command",
            return_value=(
                0,
                "Ran 123 tests in 1.234s\n",
                "progress: Ran 456 tests in 2.345s\nRan 0 tests in 0.000s\n\nOK\n",
            ),
        ):
            errors = verify_release.unit_test_checks(ROOT)
        self.assertEqual(errors, ["unit test discovery reported zero tests"])

    def test_unit_test_checks_use_final_complete_stderr_summary(self):
        verify_release = load_script("verify_release")
        stderr = "Ran 0 tests in 0.000s\nRan 123 tests in 1.234s\n\nOK\n"
        with mock.patch.object(verify_release, "run_command", return_value=(0, "", stderr)):
            errors = verify_release.unit_test_checks(ROOT)
        self.assertEqual(errors, [])

    def test_unit_test_checks_ignore_incomplete_final_summary_lookalike(self):
        verify_release = load_script("verify_release")
        stderr = "Ran 123 tests in 1.234s and kept going\n\nOK\n"
        with mock.patch.object(verify_release, "run_command", return_value=(0, "", stderr)):
            errors = verify_release.unit_test_checks(ROOT)
        self.assertEqual(errors, ["unit test discovery did not report a test count"])

    def test_unit_test_checks_preserve_test_failures(self):
        verify_release = load_script("verify_release")
        with mock.patch.object(verify_release, "run_command", return_value=(1, "failed stdout", "failed stderr")):
            errors = verify_release.unit_test_checks(ROOT)
        self.assertEqual(errors, ["unit tests failed:\nfailed stdoutfailed stderr"])

    def test_unit_test_checks_accept_positive_discovery_count(self):
        verify_release = load_script("verify_release")
        with mock.patch.object(verify_release, "run_command", return_value=(0, "", "Ran 123 tests in 1.234s\n\nOK\n")):
            errors = verify_release.unit_test_checks(ROOT)
        self.assertEqual(errors, [])

    def test_archive_excludes_generated_paths(self):
        build_release_archive = load_script("build_release_archive")
        self.assertFalse(build_release_archive.should_include(ROOT / "__pycache__" / "x.pyc"))
        self.assertFalse(build_release_archive.should_include(ROOT / ".env"))
        with tempfile.TemporaryDirectory() as directory:
            install_manifest = Path(directory) / ".wise-owl-install.json"
            install_manifest.write_text("{}", encoding="utf-8")
            self.assertFalse(build_release_archive.should_include(install_manifest))
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

    def test_release_scripts_resolve_root_from_their_file(self):
        verify_release = load_script("verify_release")
        build_release_archive = load_script("build_release_archive")
        self.assertEqual(verify_release.repo_root(), ROOT)
        self.assertEqual(build_release_archive.repo_root(), ROOT)

    def test_static_verifier_runs_from_a_different_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "verify_release.py"), "--static"],
                cwd=directory,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Static release verification passed.", result.stdout)

    def test_archive_list_runs_from_a_different_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "build_release_archive.py"), "--list"],
                cwd=directory,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(".codex/agents/logic_owl.toml", result.stdout)

    def test_release_version_comes_from_plugin_manifest(self):
        verify_release = load_script("verify_release")
        build_release_archive = load_script("build_release_archive")
        expected = json.loads((ROOT / "wise-owl-plugin" / ".codex-plugin" / "plugin.json").read_text())["version"]
        self.assertEqual(verify_release.release_version(ROOT), expected)
        self.assertEqual(build_release_archive.release_version(ROOT), expected)
        self.assertEqual(build_release_archive.archive_name(ROOT), f"wise-owl-v{expected}.zip")

    def test_next_release_metadata_is_v020(self):
        verify_release = load_script("verify_release")
        self.assertEqual(verify_release.release_version(ROOT), "0.2.0")
        self.assertIn("## v0.2.0 - Unreleased", (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"))
        self.assertIn("# Wise Owl v0.2.0 Manifest", (ROOT / "MANIFEST.md").read_text(encoding="utf-8"))

    def test_built_archive_has_exact_selected_members(self):
        build_release_archive = load_script("build_release_archive")
        with tempfile.TemporaryDirectory() as directory:
            archive = build_release_archive.build_archive(ROOT, Path(directory))
            with zipfile.ZipFile(archive) as handle:
                names = handle.namelist()
        expected = (ROOT / "tests" / "fixtures" / "release_archive_members.txt").read_text(encoding="utf-8").splitlines()
        self.assertEqual(names, expected)

    def test_archive_uses_reproducible_timestamps(self):
        build_release_archive = load_script("build_release_archive")
        with tempfile.TemporaryDirectory() as directory:
            archive = build_release_archive.build_archive(ROOT, Path(directory))
            with zipfile.ZipFile(archive) as handle:
                timestamps = {item.date_time for item in handle.infolist()}
        self.assertEqual(timestamps, {(1980, 1, 1, 0, 0, 0)})

    def test_archive_rejects_symlinks(self):
        build_release_archive = load_script("build_release_archive")
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "tmp" / "release"
            (root / "docs").mkdir(parents=True)
            internal = root / "docs" / "internal.md"
            internal.write_text("internal", encoding="utf-8")
            external = base / "external.md"
            external.write_text("external", encoding="utf-8")
            (root / "docs" / "internal-link.md").symlink_to(internal)
            (root / "docs" / "external-link.md").symlink_to(external)

            files = {path.as_posix() for path in build_release_archive.iter_files(root)}

        self.assertIn("docs/internal.md", files)
        self.assertNotIn("docs/internal-link.md", files)
        self.assertNotIn("docs/external-link.md", files)

    def test_archive_rejects_symlinked_directories(self):
        build_release_archive = load_script("build_release_archive")
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for name in ("internal", "external"):
                with self.subTest(name=name):
                    root = base / name / "release"
                    root.mkdir(parents=True)
                    target = root / "content" if name == "internal" else base / "outside"
                    target.mkdir(parents=True)
                    (target / "linked.md").write_text(name, encoding="utf-8")
                    (root / "docs").symlink_to(target, target_is_directory=True)

                    files = {path.as_posix() for path in build_release_archive.iter_files(root)}

                    self.assertNotIn("docs/linked.md", files)

    def test_archive_build_is_reproducible_and_checksummed(self):
        build_release_archive = load_script("build_release_archive")
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "release"
            manifest = root / "wise-owl-plugin" / ".codex-plugin" / "plugin.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text('{"version": "0.2.0"}', encoding="utf-8")
            (root / "README.md").write_text("Wise Owl\n", encoding="utf-8")

            first = build_release_archive.build_archive(root, base / "first")
            second = build_release_archive.build_archive(root, base / "second")
            first_checksum = first.with_name(f"{first.name}.sha256")
            second_checksum = second.with_name(f"{second.name}.sha256")

            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(
                first_checksum.read_text(encoding="utf-8"),
                f"{build_release_archive.archive_sha256(first)}  {first.name}\n",
            )
            self.assertEqual(
                second_checksum.read_text(encoding="utf-8"),
                f"{build_release_archive.archive_sha256(second)}  {second.name}\n",
            )

    def test_installer_smoke_is_confined_to_supplied_sandbox(self):
        verify_release = load_script("verify_release")
        with tempfile.TemporaryDirectory() as directory:
            sandbox = Path(directory)
            errors = verify_release.installer_smoke(ROOT, sandbox)
            written = [path for path in sandbox.rglob("*") if path.is_file()]
        self.assertEqual(errors, [])
        self.assertTrue(written)
        self.assertTrue(all(str(path).startswith(str(sandbox)) for path in written))

    def test_ci_uses_the_canonical_release_verifier(self):
        workflow = ROOT / ".github" / "workflows" / "verify.yml"
        self.assertTrue(workflow.is_file())
        text = workflow.read_text(encoding="utf-8")
        self.assertIn('python-version: ["3.10", "3.12", "3.14"]', text)
        self.assertIn("python3 scripts/verify_release.py", text)
        self.assertIn("permissions:\n  contents: read", text)

    def test_plugin_package_matches_canonical_sources(self):
        sync_plugin_assets = load_script("sync_plugin_assets")
        self.assertEqual(sync_plugin_assets.verify(ROOT), [])

        plugin_skill = ROOT / "wise-owl-plugin" / "skills" / "wise-owl"
        self.assertTrue((plugin_skill / "references" / "finding-schema.md").is_file())
        self.assertTrue((plugin_skill / "references" / "severity-rubric.md").is_file())
        self.assertTrue((plugin_skill / "scripts" / "wise_owl_validate_packet.py").is_file())
        self.assertEqual(
            (ROOT / ".agents" / "skills" / "wise-owl" / "scripts" / "wise_owl_install.py").read_bytes(),
            (ROOT / "wise-owl-plugin" / "scripts" / "install_wise_owl.py").read_bytes(),
        )

    def test_workflow_preview_shows_a_consistent_full_council(self):
        workflow = (ROOT / "assets" / "wise-owl-workflow.svg").read_text(encoding="utf-8")
        self.assertIn("Use Wise Owl Full Council", workflow)
        self.assertIn("Guardian Owl, then Prime Owl", workflow)
        self.assertNotIn("Use Wise Owl Standard", workflow)

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
