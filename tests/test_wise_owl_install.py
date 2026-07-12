import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / ".agents" / "skills" / "wise-owl" / "scripts" / "wise_owl_install.py"
PLUGIN_INSTALLER = ROOT / "wise-owl-plugin" / "scripts" / "install_wise_owl.py"


def load_installer():
    spec = importlib.util.spec_from_file_location("wise_owl_install", INSTALLER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_plugin_installer():
    spec = importlib.util.spec_from_file_location("install_wise_owl_plugin", PLUGIN_INSTALLER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WiseOwlInstallTests(unittest.TestCase):
    def setUp(self):
        self.installer = load_installer()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.codex_home = self.root / "home" / ".codex"
        self.user_skills_home = self.root / "home" / ".agents"

    def tearDown(self):
        self.tmp.cleanup()

    def make_template(self):
        template = self.root / "template"
        shutil.copytree(ROOT / ".agents", template / ".agents")
        shutil.copytree(ROOT / ".codex", template / ".codex")
        manifest = template / "wise-owl-plugin" / ".codex-plugin" / "plugin.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text((ROOT / "wise-owl-plugin" / ".codex-plugin" / "plugin.json").read_text(), encoding="utf-8")
        return template

    def test_dry_run_does_not_write_files(self):
        changed = self.installer.install("repo", self.root, self.codex_home, dry_run=True, template_root=ROOT)
        self.assertTrue(changed)
        self.assertFalse((self.root / ".agents" / "skills" / "wise-owl" / "SKILL.md").exists())
        self.assertFalse((self.root / ".codex" / "agents").exists())

    def test_dry_run_allows_existing_different_files(self):
        skill = self.root / ".agents" / "skills" / "wise-owl" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("custom\n")
        changed = self.installer.install("repo", self.root, self.codex_home, dry_run=True, template_root=ROOT)
        self.assertIn(skill, changed)
        self.assertEqual(skill.read_text(), "custom\n")

    def test_refuses_overwrite_without_force(self):
        skill = self.root / ".agents" / "skills" / "wise-owl" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("custom\n")
        with self.assertRaisesRegex(FileExistsError, "refusing to overwrite"):
            self.installer.install("repo", self.root, self.codex_home, template_root=ROOT)

    def test_conflict_preflight_writes_nothing(self):
        config = self.root / ".codex" / "config.toml"
        config.parent.mkdir(parents=True)
        config.write_text('[project]\nname = "custom"\n', encoding="utf-8")
        agents_md = self.root / "AGENTS.md"
        agents_md.write_text("# Project\n", encoding="utf-8")
        first_skill = self.root / ".agents" / "skills" / "wise-owl" / "SKILL.md"
        later_conflict = self.root / ".agents" / "skills" / "wise-owl" / "references" / "finding-schema.md"
        later_conflict.parent.mkdir(parents=True)
        later_conflict.write_text("custom\n", encoding="utf-8")

        with self.assertRaisesRegex(FileExistsError, "refusing to overwrite"):
            self.installer.install("repo", self.root, self.codex_home, patch_agents=True, template_root=ROOT)

        self.assertFalse(first_skill.exists())
        self.assertEqual(config.read_text(encoding="utf-8"), '[project]\nname = "custom"\n')
        self.assertEqual(agents_md.read_text(encoding="utf-8"), "# Project\n")
        self.assertEqual(later_conflict.read_text(encoding="utf-8"), "custom\n")

    def test_force_overwrites_expected_files(self):
        skill = self.root / ".agents" / "skills" / "wise-owl" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("custom\n")
        self.installer.install("repo", self.root, self.codex_home, force=True, template_root=ROOT)
        self.assertIn("name: wise-owl", skill.read_text())

    def test_cli_dry_run_output_is_explicit(self):
        result = subprocess.run(
            [sys.executable, str(INSTALLER), "--scope", "repo", "--dry-run"],
            cwd=self.root,
            env={"WISE_OWL_TEMPLATE_ROOT": str(ROOT)},
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Wise Owl dry run for repo scope.", result.stdout)
        self.assertIn("Would change", result.stdout)
        self.assertIn("No files were written.", result.stdout)
        self.assertIn(str(self.root / ".agents" / "skills" / "wise-owl"), result.stdout)
        self.assertNotIn("SKILL.md\n", result.stdout)
        self.assertFalse((self.root / ".agents").exists())

    def test_verbose_dry_run_lists_changed_paths(self):
        result = subprocess.run(
            [sys.executable, str(INSTALLER), "--scope", "repo", "--dry-run", "--verbose"],
            cwd=self.root,
            env={"WISE_OWL_TEMPLATE_ROOT": str(ROOT)},
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(self.root / ".agents" / "skills" / "wise-owl" / "SKILL.md"), result.stdout)

    def test_root_installer_defaults_to_user_scope(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "install.py"), "--dry-run"],
            cwd=self.root,
            env={
                "HOME": str(self.root / "home"),
                "WISE_OWL_TEMPLATE_ROOT": str(ROOT),
            },
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Wise Owl dry run for user scope.", result.stdout)
        self.assertIn(str(self.user_skills_home / "skills" / "wise-owl"), result.stdout)
        self.assertFalse((self.user_skills_home / "skills").exists())

    def test_root_installer_help_uses_public_entrypoint_name(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "install.py"), "--help"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: install.py", result.stdout)
        self.assertNotIn("usage: wise_owl_install.py", result.stdout)
        self.assertIn("repo uses current", result.stdout)
        self.assertIn("working directory", result.stdout)

    def test_underlying_installer_defaults_to_user_scope(self):
        result = subprocess.run(
            [sys.executable, str(INSTALLER), "--dry-run"],
            cwd=self.root,
            env={
                "HOME": str(self.root / "home"),
                "WISE_OWL_TEMPLATE_ROOT": str(ROOT),
            },
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(self.user_skills_home / "skills" / "wise-owl"), result.stdout)

    def test_check_passes_after_install_and_detects_missing_agent(self):
        self.installer.install("user", self.root, self.codex_home, template_root=ROOT)
        self.assertEqual(
            self.installer.check_install("user", self.root, self.codex_home, self.user_skills_home),
            [],
        )

        (self.codex_home / "agents" / "proof_owl.toml").unlink()
        errors = self.installer.check_install("user", self.root, self.codex_home, self.user_skills_home)
        self.assertTrue(any("missing agent TOML: proof_owl.toml" in error for error in errors), errors)

    def test_user_check_ignores_repository_agents_policy(self):
        self.installer.install("user", self.root, self.codex_home, template_root=ROOT)
        agents_md = self.root / "AGENTS.md"

        for policy in (
            self.installer.AGENTS_POLICY_V0_1,
            "## WISE OWL REVIEW POLICY\n\nKeep my custom routing rules.\n",
        ):
            with self.subTest(policy=policy.splitlines()[0]):
                agents_md.write_text(policy, encoding="utf-8")
                self.assertEqual(
                    self.installer.check_install("user", self.root, self.codex_home, self.user_skills_home),
                    [],
                )

    def test_check_fails_when_managed_manifest_is_missing(self):
        self.installer.install("user", self.root, self.codex_home, template_root=ROOT)
        manifest = self.user_skills_home / "skills" / "wise-owl" / ".wise-owl-install.json"
        manifest.unlink()
        errors = self.installer.check_install("user", self.root, self.codex_home, self.user_skills_home)
        self.assertTrue(any("missing managed install manifest" in error for error in errors), errors)

    def test_check_cli_is_read_only_and_defaults_to_user_scope(self):
        self.installer.install("user", self.root, self.codex_home, template_root=ROOT)
        before = {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        result = subprocess.run(
            [sys.executable, str(ROOT / "install.py"), "--check"],
            cwd=self.root,
            env={
                "HOME": str(self.root / "home"),
                "WISE_OWL_TEMPLATE_ROOT": str(ROOT),
            },
            text=True,
            capture_output=True,
            check=False,
        )
        after = {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Wise Owl check passed for user scope.", result.stdout)
        self.assertEqual(before, after)

    def test_install_success_output_includes_next_steps(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "install.py")],
            cwd=self.root,
            env={
                "HOME": str(self.root / "home"),
                "WISE_OWL_TEMPLATE_ROOT": str(ROOT),
            },
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Wise Owl installed for user scope.", result.stdout)
        self.assertIn("Restart or reopen Codex.", result.stdout)
        self.assertIn("Use Wise Owl Standard to review this change.", result.stdout)
        self.assertIn("--check", result.stdout)
        self.assertNotIn("SKILL.md\n", result.stdout)

    def test_managed_upgrade_replaces_unchanged_owned_files_without_force(self):
        template = self.make_template()
        self.installer.install("user", self.root, self.codex_home, template_root=template)
        installed_skill = self.user_skills_home / "skills" / "wise-owl" / "SKILL.md"
        updated = (template / ".agents" / "skills" / "wise-owl" / "SKILL.md").read_text() + "\nUpgrade marker.\n"
        (template / ".agents" / "skills" / "wise-owl" / "SKILL.md").write_text(updated, encoding="utf-8")

        self.installer.install("user", self.root, self.codex_home, template_root=template)

        self.assertEqual(installed_skill.read_text(encoding="utf-8"), updated)
        manifest = json.loads((installed_skill.parent / ".wise-owl-install.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], 1)
        self.assertIn("skill/SKILL.md", manifest["files"])

    def test_managed_upgrade_refuses_modified_owned_files(self):
        template = self.make_template()
        self.installer.install("user", self.root, self.codex_home, template_root=template)
        installed_skill = self.user_skills_home / "skills" / "wise-owl" / "SKILL.md"
        installed_skill.write_text("local customization\n", encoding="utf-8")
        source_skill = template / ".agents" / "skills" / "wise-owl" / "SKILL.md"
        source_skill.write_text(source_skill.read_text(encoding="utf-8") + "\nUpgrade marker.\n", encoding="utf-8")

        with self.assertRaisesRegex(FileExistsError, "locally modified managed files"):
            self.installer.install("user", self.root, self.codex_home, template_root=template)

        self.assertEqual(installed_skill.read_text(encoding="utf-8"), "local customization\n")

    def test_managed_upgrade_removes_stale_unchanged_owned_files(self):
        template = self.make_template()
        stale_source = template / ".agents" / "skills" / "wise-owl" / "references" / "old-guide.md"
        stale_source.write_text("old guide\n", encoding="utf-8")
        self.installer.install("user", self.root, self.codex_home, template_root=template)
        installed = self.user_skills_home / "skills" / "wise-owl" / "references" / "old-guide.md"
        self.assertTrue(installed.exists())

        stale_source.unlink()
        self.installer.install("user", self.root, self.codex_home, template_root=template)

        self.assertFalse(installed.exists())
        manifest = json.loads((self.user_skills_home / "skills" / "wise-owl" / ".wise-owl-install.json").read_text())
        self.assertNotIn("skill/references/old-guide.md", manifest["files"])

    def test_managed_upgrade_refuses_to_orphan_modified_stale_files(self):
        template = self.make_template()
        stale_source = template / ".agents" / "skills" / "wise-owl" / "references" / "old-guide.md"
        stale_source.write_text("old guide\n", encoding="utf-8")
        self.installer.install("user", self.root, self.codex_home, template_root=template)
        installed = self.user_skills_home / "skills" / "wise-owl" / "references" / "old-guide.md"
        installed.write_text("local guide\n", encoding="utf-8")
        stale_source.unlink()

        with self.assertRaisesRegex(FileExistsError, "locally modified managed files"):
            self.installer.install("user", self.root, self.codex_home, template_root=template)

        self.assertEqual(installed.read_text(encoding="utf-8"), "local guide\n")

    def test_installed_script_reinstall_preserves_package_version(self):
        self.installer.install("user", self.root, self.codex_home, template_root=ROOT)
        installed_script = self.user_skills_home / "skills" / "wise-owl" / "scripts" / "wise_owl_install.py"
        result = subprocess.run(
            [sys.executable, str(installed_script), "--scope", "user"],
            cwd=self.root,
            env={
                "HOME": str(self.root / "home"),
                "WISE_OWL_REPO_ROOT": str(self.root / "repo"),
                "WISE_OWL_CODEX_HOME": str(self.codex_home),
                "WISE_OWL_USER_SKILLS_HOME": str(self.user_skills_home),
            },
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((installed_script.parents[1] / ".wise-owl-install.json").read_text())
        self.assertEqual(manifest["package_version"], "0.2.0")

    def test_uninstall_removes_owned_files_and_preserves_shared_config(self):
        self.installer.install("user", self.root, self.codex_home, template_root=ROOT)
        config = self.codex_home / "config.toml"

        removed, preserved = self.installer.uninstall(
            "user",
            self.root,
            self.codex_home,
            self.user_skills_home,
        )

        self.assertTrue(removed)
        self.assertEqual(preserved, [])
        self.assertFalse((self.user_skills_home / "skills" / "wise-owl").exists())
        self.assertFalse((self.codex_home / "agents" / "logic_owl.toml").exists())
        self.assertTrue(config.exists())

    def test_uninstall_preserves_locally_modified_owned_files(self):
        self.installer.install("user", self.root, self.codex_home, template_root=ROOT)
        agent = self.codex_home / "agents" / "logic_owl.toml"
        agent.write_text(agent.read_text(encoding="utf-8") + "# local\n", encoding="utf-8")

        removed, preserved = self.installer.uninstall(
            "user",
            self.root,
            self.codex_home,
            self.user_skills_home,
        )

        self.assertTrue(removed)
        self.assertEqual(preserved, [agent])
        self.assertTrue(agent.exists())
        manifest = self.user_skills_home / "skills" / "wise-owl" / ".wise-owl-install.json"
        self.assertTrue(manifest.exists())

    def test_uninstall_without_manifest_refuses_guessing_ownership(self):
        with self.assertRaisesRegex(FileNotFoundError, "managed install manifest"):
            self.installer.uninstall("user", self.root, self.codex_home, self.user_skills_home)

    def test_check_and_uninstall_reject_symlinked_manifest(self):
        self.installer.install("user", self.root, self.codex_home, template_root=ROOT)
        skill_dir = self.user_skills_home / "skills" / "wise-owl"
        manifest = skill_dir / ".wise-owl-install.json"
        original = manifest.read_text(encoding="utf-8")
        outside = self.root / "outside-manifest.json"
        outside.write_text(original, encoding="utf-8")
        manifest.unlink()
        try:
            manifest.symlink_to(outside)
        except OSError as exc:
            self.skipTest(f"symlinks unavailable: {exc}")

        agent = self.codex_home / "agents" / "logic_owl.toml"
        agent.write_text(agent.read_text(encoding="utf-8") + "# local\n", encoding="utf-8")

        errors = self.installer.check_install("user", self.root, self.codex_home, self.user_skills_home)
        self.assertTrue(any("manifest must not be a symlink" in error for error in errors), errors)
        with self.assertRaisesRegex(ValueError, "symlink write target"):
            self.installer.uninstall("user", self.root, self.codex_home, self.user_skills_home)

        self.assertEqual(outside.read_text(encoding="utf-8"), original)
        self.assertTrue(agent.exists())

    def test_check_and_uninstall_reject_skill_directory_escape(self):
        self.installer.install("user", self.root, self.codex_home, template_root=ROOT)
        skill_dir = self.user_skills_home / "skills" / "wise-owl"
        outside = self.root / "outside-skill"
        skill_dir.rename(outside)
        try:
            skill_dir.symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"symlinks unavailable: {exc}")

        errors = self.installer.check_install("user", self.root, self.codex_home, self.user_skills_home)
        self.assertTrue(any("outside install roots" in error for error in errors), errors)
        with self.assertRaisesRegex(ValueError, "outside install roots"):
            self.installer.uninstall("user", self.root, self.codex_home, self.user_skills_home)

        self.assertTrue((outside / "SKILL.md").exists())
        self.assertTrue((self.codex_home / "agents" / "logic_owl.toml").exists())

    def test_public_uninstall_cli_removes_clean_install(self):
        self.installer.install("user", self.root, self.codex_home, template_root=ROOT)
        result = subprocess.run(
            [sys.executable, str(ROOT / "install.py"), "--uninstall"],
            cwd=self.root,
            env={
                "HOME": str(self.root / "home"),
                "WISE_OWL_REPO_ROOT": str(self.root / "repo"),
                "WISE_OWL_CODEX_HOME": str(self.codex_home),
                "WISE_OWL_USER_SKILLS_HOME": str(self.user_skills_home),
                "WISE_OWL_TEMPLATE_ROOT": str(ROOT),
            },
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Removed", result.stdout)
        self.assertIn("Shared config.toml and AGENTS.md entries were left unchanged.", result.stdout)
        self.assertFalse((self.user_skills_home / "skills" / "wise-owl").exists())
        self.assertTrue((self.codex_home / "config.toml").exists())

    def test_public_uninstall_cli_reports_preserved_modified_file(self):
        self.installer.install("user", self.root, self.codex_home, template_root=ROOT)
        agent = self.codex_home / "agents" / "logic_owl.toml"
        agent.write_text(agent.read_text(encoding="utf-8") + "# local\n", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(ROOT / "install.py"), "--uninstall"],
            cwd=self.root,
            env={
                "HOME": str(self.root / "home"),
                "WISE_OWL_REPO_ROOT": str(self.root / "repo"),
                "WISE_OWL_CODEX_HOME": str(self.codex_home),
                "WISE_OWL_USER_SKILLS_HOME": str(self.user_skills_home),
                "WISE_OWL_TEMPLATE_ROOT": str(ROOT),
            },
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Preserved locally modified files", result.stderr)
        self.assertIn(str(agent), result.stderr)
        self.assertTrue(agent.exists())

    def test_install_rejects_symlinked_shared_config_target(self):
        config = self.root / ".codex" / "config.toml"
        config.parent.mkdir(parents=True)
        outside = self.root / "outside-config.toml"
        outside.write_text('[outside]\nvalue = "untouched"\n', encoding="utf-8")
        try:
            config.symlink_to(outside)
        except OSError as exc:
            self.skipTest(f"symlinks unavailable: {exc}")

        with self.assertRaisesRegex(ValueError, "symlink write target"):
            self.installer.install("repo", self.root, self.codex_home, template_root=ROOT)

        self.assertEqual(outside.read_text(encoding="utf-8"), '[outside]\nvalue = "untouched"\n')
        self.assertFalse((self.root / ".agents" / "skills" / "wise-owl" / "SKILL.md").exists())

    def test_install_rejects_symlinked_managed_file_target(self):
        skill = self.root / ".agents" / "skills" / "wise-owl" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        outside = self.root / "outside-skill.md"
        outside.write_text("untouched\n", encoding="utf-8")
        try:
            skill.symlink_to(outside)
        except OSError as exc:
            self.skipTest(f"symlinks unavailable: {exc}")

        with self.assertRaisesRegex(ValueError, "symlink write target"):
            self.installer.install("repo", self.root, self.codex_home, template_root=ROOT)

        self.assertEqual(outside.read_text(encoding="utf-8"), "untouched\n")

    def test_generated_tomls_parse_with_tomllib_when_available(self):
        try:
            import tomllib
        except ModuleNotFoundError:
            self.skipTest("tomllib is unavailable before Python 3.11")

        planned = self.installer.plan_install("repo", self.root, self.codex_home, "gpt-test", "prime-test", False, ROOT)
        tomls = {
            path.name: content
            for path, content in planned.items()
            if path.suffix == ".toml" and path.parent.name == "agents"
        }
        self.assertEqual(len(tomls), 4)
        for content in tomls.values():
            parsed = tomllib.loads(content)
            self.assertIn("name", parsed)
            self.assertIn("developer_instructions", parsed)
        self.assertEqual(tomllib.loads(tomls["logic_owl.toml"])["model"], "gpt-test")
        self.assertEqual(tomllib.loads(tomls["guardian_owl.toml"])["model"], "gpt-test")
        self.assertEqual(tomllib.loads(tomls["prime_owl.toml"])["model"], "prime-test")

    def test_default_model_policy_is_split(self):
        try:
            import tomllib
        except ModuleNotFoundError:
            self.skipTest("tomllib is unavailable before Python 3.11")

        planned = self.installer.plan_install(
            "repo",
            self.root,
            self.codex_home,
            self.installer.DEFAULT_MODEL,
            self.installer.DEFAULT_PRIME_MODEL,
            False,
            ROOT,
        )
        tomls = {
            path.name: tomllib.loads(content)
            for path, content in planned.items()
            if path.suffix == ".toml" and path.parent.name == "agents"
        }
        self.assertEqual(tomls["logic_owl.toml"]["model"], "gpt-5.4-mini")
        self.assertEqual(tomls["proof_owl.toml"]["model"], "gpt-5.4-mini")
        self.assertEqual(tomls["guardian_owl.toml"]["model"], "gpt-5.5")
        self.assertEqual(tomls["prime_owl.toml"]["model"], "gpt-5.5")

    def test_model_values_are_toml_escaped(self):
        try:
            import tomllib
        except ModuleNotFoundError:
            self.skipTest("tomllib is unavailable before Python 3.11")

        model = 'gpt-test"\napproval_policy = "never"\n#'
        prime_model = 'prime-test"\nsandbox_mode = "workspace-write"\n#'
        planned = self.installer.plan_install("repo", self.root, self.codex_home, model, prime_model, False, ROOT)
        tomls = {
            path.name: content
            for path, content in planned.items()
            if path.suffix == ".toml" and path.parent.name == "agents"
        }
        logic_owl = tomllib.loads(tomls["logic_owl.toml"])
        prime_owl = tomllib.loads(tomls["prime_owl.toml"])
        self.assertEqual(logic_owl["model"], model)
        self.assertNotIn("approval_policy", logic_owl)
        self.assertEqual(prime_owl["model"], prime_model)
        self.assertEqual(prime_owl["sandbox_mode"], "read-only")

    def test_plugin_model_values_are_toml_escaped(self):
        try:
            import tomllib
        except ModuleNotFoundError:
            self.skipTest("tomllib is unavailable before Python 3.11")

        plugin_installer = load_plugin_installer()
        model = 'gpt-plugin"\napproval_policy = "never"\n#'
        content = plugin_installer.replace_model('name = "owl"\nmodel = "old"\nsandbox_mode = "read-only"\n', model)
        parsed = tomllib.loads(content)
        self.assertEqual(parsed["model"], model)
        self.assertEqual(parsed["sandbox_mode"], "read-only")
        self.assertNotIn("approval_policy", parsed)

    def test_user_scope_install_writes_to_documented_user_locations(self):
        changed = self.installer.install("user", self.root, self.codex_home, template_root=ROOT)
        self.assertTrue(changed)
        self.assertTrue((self.user_skills_home / "skills" / "wise-owl" / "SKILL.md").exists())
        self.assertTrue((self.codex_home / "agents" / "logic_owl.toml").exists())
        self.assertTrue((self.codex_home / "config.toml").exists())
        self.assertFalse((self.root / ".agents").exists())
        self.assertFalse((self.root / ".codex").exists())
        self.assertFalse((self.codex_home / "skills" / "wise-owl" / "SKILL.md").exists())

    def test_user_scope_legacy_cleanup_only_under_codex_home_with_force(self):
        legacy = self.codex_home / "agents" / "owl_guard.toml"
        legacy.parent.mkdir(parents=True)
        legacy.write_text("legacy\n", encoding="utf-8")
        repo_legacy = self.root / ".codex" / "agents" / "owl_guard.toml"
        repo_legacy.parent.mkdir(parents=True)
        repo_legacy.write_text("repo legacy\n", encoding="utf-8")

        self.installer.install("user", self.root, self.codex_home, force=True, template_root=ROOT)

        self.assertFalse(legacy.exists())
        self.assertEqual(repo_legacy.read_text(encoding="utf-8"), "repo legacy\n")

    def test_plugin_user_scope_install_and_dry_run(self):
        plugin_installer = load_plugin_installer()
        dry_changed = plugin_installer.plan_install(
            "user",
            self.root,
            self.codex_home,
            plugin_installer.DEFAULT_MODEL,
            plugin_installer.DEFAULT_PRIME_MODEL,
            False,
            ROOT / "wise-owl-plugin",
        )
        plugin_installer.write_planned(dry_changed, dry_run=True, force=False)
        self.assertFalse((self.user_skills_home / "skills").exists())

        changed = plugin_installer.write_planned(dry_changed, dry_run=False, force=False)
        self.assertTrue(changed)
        self.assertTrue((self.user_skills_home / "skills" / "wise-owl" / "SKILL.md").exists())
        self.assertTrue((self.codex_home / "agents" / "prime_owl.toml").exists())

    def test_plugin_full_install_writes_complete_skill_and_manifest(self):
        plugin_installer = load_plugin_installer()
        plugin_installer.install(
            "user",
            self.root,
            self.codex_home,
            user_skills_home=self.user_skills_home,
            template_root=ROOT / "wise-owl-plugin",
        )
        skill = self.user_skills_home / "skills" / "wise-owl"
        self.assertTrue((skill / "references" / "finding-schema.md").is_file())
        self.assertTrue((skill / "scripts" / "wise_owl_validate_packet.py").is_file())
        self.assertTrue((skill / ".wise-owl-install.json").is_file())

    def test_plugin_conflict_preflight_writes_nothing(self):
        plugin_installer = load_plugin_installer()
        planned = plugin_installer.plan_install(
            "user",
            self.root,
            self.codex_home,
            plugin_installer.DEFAULT_MODEL,
            plugin_installer.DEFAULT_PRIME_MODEL,
            False,
            ROOT / "wise-owl-plugin",
        )
        config = self.codex_home / "config.toml"
        config.parent.mkdir(parents=True)
        config.write_text('[project]\nname = "custom"\n', encoding="utf-8")
        conflict = self.codex_home / "agents" / "proof_owl.toml"
        conflict.parent.mkdir(parents=True)
        conflict.write_text("custom\n", encoding="utf-8")

        with self.assertRaisesRegex(FileExistsError, "refusing to overwrite"):
            plugin_installer.write_planned(planned, dry_run=False, force=False)

        self.assertFalse((self.user_skills_home / "skills" / "wise-owl" / "SKILL.md").exists())
        self.assertEqual(config.read_text(encoding="utf-8"), '[project]\nname = "custom"\n')
        self.assertEqual(conflict.read_text(encoding="utf-8"), "custom\n")

    def test_plugin_force_removes_legacy_agent_files(self):
        plugin_installer = load_plugin_installer()
        legacy = self.codex_home / "agents" / "owl_proof.toml"
        legacy.parent.mkdir(parents=True)
        legacy.write_text("legacy\n", encoding="utf-8")
        planned = plugin_installer.plan_install(
            "user",
            self.root,
            self.codex_home,
            plugin_installer.DEFAULT_MODEL,
            plugin_installer.DEFAULT_PRIME_MODEL,
            False,
            ROOT / "wise-owl-plugin",
        )
        plugin_installer.write_planned(planned, dry_run=False, force=True)
        plugin_installer.handle_legacy_agents(self.codex_home / "agents", dry_run=False, force=True)
        self.assertFalse(legacy.exists())

    def test_skill_frontmatter_includes_name_and_description(self):
        skill_md = (ROOT / ".agents" / "skills" / "wise-owl" / "SKILL.md").read_text()
        frontmatter = skill_md.split("---", 2)[1]
        self.assertIn("name: wise-owl", frontmatter)
        self.assertIn("description:", frontmatter)

    def test_config_merge_preserves_existing_keys(self):
        merged = self.installer.merge_config('[other]\nvalue = "kept"\n\n[agents]\ncustom = "yes"\n')
        self.assertIn('[other]\nvalue = "kept"', merged)
        self.assertIn('custom = "yes"', merged)
        self.assertIn("max_threads = 6", merged)
        self.assertIn("max_depth = 1", merged)

    def test_agents_md_patch_is_idempotent(self):
        once = self.installer.patch_agents_md("# Project\n")
        twice = self.installer.patch_agents_md(once)
        self.assertEqual(once, twice)
        self.assertEqual(once.count("## Wise Owl Review Policy"), 1)

    def test_agents_md_patch_upgrades_exact_generated_v01_policy(self):
        legacy_policy = self.installer.AGENTS_POLICY_V0_1
        self.assertEqual(
            hashlib.sha256(legacy_policy.encode("utf-8")).hexdigest(),
            "50a77fe8d2b737c73d59ad5b56db36b302efdc5f171067db130adb9c8130c7d4",
        )
        existing = f"# Project\n\n{legacy_policy}\n## User Rules\n\nKeep this.\n"
        agents_md = self.root / "AGENTS.md"
        agents_md.write_text(existing, encoding="utf-8")

        changed = self.installer.install(
            "repo",
            self.root,
            self.codex_home,
            patch_agents=True,
            template_root=ROOT,
        )
        patched = agents_md.read_text(encoding="utf-8")

        self.assertIn(agents_md, changed)
        self.assertEqual(patched, existing.replace(legacy_policy, self.installer.AGENTS_POLICY))
        self.assertEqual(patched.count("## Wise Owl Review Policy"), 1)
        self.assertNotIn("Wise Owl Lite: Prime Owl only", patched)
        self.assertIn("## User Rules\n\nKeep this.\n", patched)
        self.assertEqual(self.installer.check_install("repo", self.root, self.codex_home), [])

    def test_agents_md_patch_rejects_customized_policy_without_writing(self):
        agents_md = self.root / "AGENTS.md"
        customized = "# Project\n\n## Wise Owl Review Policy\n\nKeep my custom routing rules.\n"
        agents_md.write_text(customized, encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "customized or ambiguous Wise Owl Review Policy"):
            self.installer.install(
                "repo",
                self.root,
                self.codex_home,
                patch_agents=True,
                template_root=ROOT,
            )

        self.assertEqual(agents_md.read_text(encoding="utf-8"), customized)
        self.assertFalse((self.root / ".agents" / "skills" / "wise-owl" / "SKILL.md").exists())
        self.assertFalse((self.root / ".codex" / "config.toml").exists())

    def test_agents_md_patch_rejects_markdown_equivalent_policy_headings_without_writing(self):
        agents_md = self.root / "AGENTS.md"
        headings = (
            "## WISE OWL REVIEW POLICY",
            "##  Wise Owl Review Policy",
            "## Wise Owl Review Policy ##",
        )
        for heading in headings:
            with self.subTest(heading=heading):
                customized = f"# Project\n\n{heading}\n\nKeep my custom routing rules.\n"
                agents_md.write_text(customized, encoding="utf-8")

                with self.assertRaisesRegex(ValueError, "customized or ambiguous Wise Owl Review Policy"):
                    self.installer.install(
                        "repo",
                        self.root,
                        self.codex_home,
                        patch_agents=True,
                        template_root=ROOT,
                    )

                self.assertEqual(agents_md.read_text(encoding="utf-8"), customized)
                self.assertFalse((self.root / ".agents" / "skills" / "wise-owl" / "SKILL.md").exists())
                self.assertFalse((self.root / ".codex" / "config.toml").exists())

    def test_patch_agents_cli_reports_customized_policy_conflict_without_traceback(self):
        agents_md = self.root / "AGENTS.md"
        customized = "## Wise Owl Review Policy\n\nKeep my custom routing rules.\n"
        agents_md.write_text(customized, encoding="utf-8")

        result = subprocess.run(
            [sys.executable, str(INSTALLER), "--scope", "repo", "--patch-agents-md"],
            cwd=self.root,
            env={"WISE_OWL_TEMPLATE_ROOT": str(ROOT)},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("Wise Owl install failed:", result.stderr)
        self.assertIn("customized or ambiguous Wise Owl Review Policy", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(agents_md.read_text(encoding="utf-8"), customized)

    def test_patch_agents_cli_rejects_markdown_equivalent_policy_headings_without_writing(self):
        agents_md = self.root / "AGENTS.md"
        headings = (
            "## WISE OWL REVIEW POLICY",
            "##  Wise Owl Review Policy",
            "## Wise Owl Review Policy ##",
        )
        for heading in headings:
            with self.subTest(heading=heading):
                customized = f"{heading}\n\nKeep my custom routing rules.\n"
                agents_md.write_text(customized, encoding="utf-8")

                result = subprocess.run(
                    [sys.executable, str(INSTALLER), "--scope", "repo", "--patch-agents-md"],
                    cwd=self.root,
                    env={"WISE_OWL_TEMPLATE_ROOT": str(ROOT)},
                    text=True,
                    capture_output=True,
                    check=False,
                )

                self.assertEqual(result.returncode, 1)
                self.assertIn("Wise Owl install failed:", result.stderr)
                self.assertIn("customized or ambiguous Wise Owl Review Policy", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(agents_md.read_text(encoding="utf-8"), customized)

    def test_check_rejects_obsolete_prime_only_lite_policy(self):
        self.installer.install("repo", self.root, self.codex_home, template_root=ROOT)
        agents_md = self.root / "AGENTS.md"
        agents_md.write_text(self.installer.AGENTS_POLICY_V0_1, encoding="utf-8")

        errors = self.installer.check_install("repo", self.root, self.codex_home)

        self.assertTrue(any("obsolete v0.1 Wise Owl Review Policy" in error for error in errors), errors)

    def test_plugin_skill_matches_repo_skill(self):
        repo_skill = ROOT / ".agents" / "skills" / "wise-owl" / "SKILL.md"
        plugin_skill = ROOT / "wise-owl-plugin" / "skills" / "wise-owl" / "SKILL.md"
        self.assertEqual(repo_skill.read_text(), plugin_skill.read_text())

    def test_plugin_agent_assets_match_repo_agents(self):
        expected = {"logic_owl.toml", "guardian_owl.toml", "proof_owl.toml", "prime_owl.toml"}
        self.assertEqual({path.name for path in (ROOT / ".codex" / "agents").glob("*.toml")}, expected)
        self.assertEqual({path.name for path in (ROOT / "wise-owl-plugin" / "assets" / "agents").glob("*.toml")}, expected)
        for path in (ROOT / ".codex" / "agents").glob("*.toml"):
            plugin_asset = ROOT / "wise-owl-plugin" / "assets" / "agents" / path.name
            self.assertEqual(path.read_text(), plugin_asset.read_text())

    def test_agent_nicknames_are_stable_singletons(self):
        try:
            import tomllib
        except ModuleNotFoundError:
            self.skipTest("tomllib is unavailable before Python 3.11")

        expected = {
            "logic_owl.toml": ["Logic Owl"],
            "guardian_owl.toml": ["Guardian Owl"],
            "proof_owl.toml": ["Proof Owl"],
            "prime_owl.toml": ["Prime Owl"],
        }
        forbidden = {"Actually Owl", "Hoot Check", "Night Watch", "Hoot Guard", "Test Owl", "Hoot Proof", "The Judge", "Wise Owl"}
        for path in (ROOT / ".codex" / "agents").glob("*.toml"):
            parsed = tomllib.loads(path.read_text())
            self.assertEqual(parsed["nickname_candidates"], expected[path.name])
            self.assertFalse(forbidden.intersection(parsed["nickname_candidates"]))

    def test_agent_reasoning_effort_values_are_documented_safe(self):
        try:
            import tomllib
        except ModuleNotFoundError:
            self.skipTest("tomllib is unavailable before Python 3.11")

        allowed = {"low", "medium", "high"}
        for path in (ROOT / ".codex" / "agents").glob("*.toml"):
            parsed = tomllib.loads(path.read_text())
            self.assertIn(parsed["model_reasoning_effort"], allowed)

    def test_agent_tomls_document_exact_pass_packets(self):
        expected_roles = {
            "logic_owl.toml": '"role": "logic_owl"',
            "guardian_owl.toml": '"role": "guardian_owl"',
            "proof_owl.toml": '"role": "proof_owl"',
        }
        for filename, role_text in expected_roles.items():
            content = (ROOT / ".codex" / "agents" / filename).read_text()
            self.assertIn("If there are no meaningful findings, return exactly:", content)
            self.assertIn(role_text, content)
            self.assertIn('"notes": ["No meaningful issues found."]', content)
            self.assertIn("notes is required, even on pass", content)
            self.assertIn("do not add extra top-level fields", content)

        prime = (ROOT / ".codex" / "agents" / "prime_owl.toml").read_text()
        self.assertIn("If critics returned no findings, return exactly:", prime)
        self.assertIn('"accepted_findings": []', prime)
        self.assertIn('"rejected_findings": []', prime)
        self.assertIn('"No Wise Owl accepted findings remain."', prime)
        self.assertIn("If every critic finding is rejected", prime)
        self.assertIn("keep every rejected source_id in rejected_findings", prime)
        self.assertIn("do not return role", prime)
        self.assertIn("do not omit accepted_findings, rejected_findings, or builder_instructions", prime)

    def test_agent_tomls_document_exact_non_pass_packets(self):
        expected_categories = {
            "logic_owl.toml": "correctness",
            "guardian_owl.toml": "security",
            "proof_owl.toml": "testability",
        }
        for filename, category in expected_categories.items():
            content = (ROOT / ".codex" / "agents" / filename).read_text()
            self.assertIn("For any finding packet, use exactly this shape:", content)
            self.assertIn('"evidence": "one non-empty string"', content)
            self.assertIn(f'"category": "{category}"', content)
            self.assertIn("Allowed categories: correctness, security, testability, maintainability, scope, ci", content)
            self.assertIn("Do not return evidence as an array", content)

        prime = (ROOT / ".codex" / "agents" / "prime_owl.toml").read_text()
        self.assertIn("If accepted findings remain, use exactly this shape:", prime)
        self.assertIn('"required_builder_action": "minimal action"', prime)
        self.assertIn("Allowed categories: correctness, security, testability, maintainability, scope, ci", prime)
        self.assertIn("Do not use required_fix", prime)

    def test_review_evidence_guidance_is_privacy_minimized(self):
        placeholder = "[REDACTED:credential]"
        for filename in ("logic_owl.toml", "guardian_owl.toml", "proof_owl.toml"):
            content = (ROOT / ".codex" / "agents" / filename).read_text()
            with self.subTest(filename=filename):
                self.assertIn("location and sensitive-data type", content)
                self.assertIn("without repeating the raw sensitive value", content)
                self.assertIn(placeholder, content)

        prime = (ROOT / ".codex" / "agents" / "prime_owl.toml").read_text()
        self.assertIn("Do not preserve or repeat leaked sensitive values", prime)
        self.assertIn(placeholder, prime)

        surfaces = {
            "SKILL.md": (ROOT / ".agents" / "skills" / "wise-owl" / "SKILL.md").read_text(),
            "AGENTS.md": (ROOT / "AGENTS.md").read_text(),
            "installer policy": self.installer.AGENTS_POLICY,
        }
        for name, content in surfaces.items():
            with self.subTest(name=name):
                self.assertIn("Before spawn, the builder must strip raw sensitive values", content)
                self.assertIn(placeholder, content)

        docs = (ROOT / "docs" / "wise-owl.md").read_text()
        self.assertIn("best-effort instruction hygiene", docs)
        self.assertIn("not sanitizer or confidentiality enforcement", docs)
        self.assertIn(placeholder, docs)

    def test_installer_warns_for_legacy_agent_files(self):
        legacy = self.root / ".codex" / "agents" / "owl_guard.toml"
        legacy.parent.mkdir(parents=True)
        legacy.write_text("legacy\n")
        result = subprocess.run(
            [sys.executable, str(INSTALLER), "--scope", "repo", "--dry-run"],
            cwd=self.root,
            env={"WISE_OWL_TEMPLATE_ROOT": str(ROOT)},
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("legacy Wise Owl agent TOMLs", result.stderr)

    def test_force_removes_legacy_agent_files(self):
        legacy = self.root / ".codex" / "agents" / "owl_guard.toml"
        legacy.parent.mkdir(parents=True)
        legacy.write_text("legacy\n")
        self.installer.install("repo", self.root, self.codex_home, force=True, template_root=ROOT)
        self.assertFalse(legacy.exists())
        self.assertTrue((self.root / ".codex" / "agents" / "guardian_owl.toml").exists())

    def test_skill_documents_router_and_brackets(self):
        skill = (ROOT / ".agents" / "skills" / "wise-owl" / "SKILL.md").read_text()
        required = [
            "No Wise Owl",
            "Wise Owl Lite",
            "Wise Owl Standard",
            "Wise Owl Security",
            "Wise Owl Full Council",
            "Choose the cheapest mode that covers the risk",
            "Escalate, never downgrade",
            "Lite is the default for low-risk review/planning requests",
            "Wise Owl Lite: Logic Owl, then Prime Owl",
            "complete-lite only when both Logic Owl and Prime Owl return valid packets",
            "complete-lite",
            "not spawned",
            "Logic Owl + Proof Owl in parallel",
            "Guardian Owl, then Prime Owl",
            "Logic Owl + Guardian Owl + Proof Owl in parallel",
            "not background automation",
            "Model diversity:",
            "[WISE_OWL_REVIEW]",
            "[REVIEW_PACKET]",
            "[CRITIC_RESULTS]",
            "[ACCEPTED_FINDINGS]",
            "[REJECTED_FINDINGS]",
            "[EXECUTION_ISSUES]",
            "[BUILDER_ACTIONS]",
            "[/WISE_OWL_REVIEW]",
            "[PARALLEL_CRITIC_PHASE]",
            "[PRIME_REDUCTION_PHASE]",
            "[NO_INTERLEAVED_WORK_DURING_OWL_PHASE]",
            "extra repo reads, additional tests, ad hoc validation scripts",
            "Compact Review Packet",
            "Review Packet construction must finish before spawning critics",
            "not merge a blocking security finding with non-blocking documentation",
            "Pass/no-finding critic results must still validate",
            "A raw `pass` packet missing those required fields is malformed",
        ]
        for text in required:
            self.assertIn(text, skill)

    def test_lite_and_prime_pass_contracts_match_across_public_surfaces(self):
        surfaces = {
            "AGENTS.md": (ROOT / "AGENTS.md").read_text(),
            "SKILL.md": (ROOT / ".agents" / "skills" / "wise-owl" / "SKILL.md").read_text(),
            "installer policy": self.installer.AGENTS_POLICY,
            "workflow docs": (ROOT / "docs" / "wise-owl.md").read_text(),
        }
        for name, content in surfaces.items():
            with self.subTest(name=name):
                self.assertIn("Wise Owl Lite: Logic Owl, then Prime Owl", content)
                self.assertNotIn("Wise Owl Lite: Prime Owl only", content)

        readme = (ROOT / "README.md").read_text()
        schema = (ROOT / ".agents" / "skills" / "wise-owl" / "references" / "finding-schema.md").read_text()
        changelog = (ROOT / "CHANGELOG.md").read_text()
        self.assertIn("| Lite | Logic Owl + Prime Owl |", readme)
        self.assertIn("If critics returned no findings", schema)
        self.assertIn("If every critic finding is rejected", schema)
        self.assertIn("all valid v0.1 packet shapes remain valid", changelog)

    def test_agents_md_documents_router(self):
        agents = (ROOT / "AGENTS.md").read_text()
        self.assertIn("Choose the cheapest mode that covers the risk", agents)
        self.assertIn("Wise Owl Lite", agents)
        self.assertIn("Wise Owl Standard", agents)
        self.assertIn("Wise Owl Security", agents)
        self.assertIn("Wise Owl Full Council", agents)
        self.assertIn("complete-lite", agents)
        self.assertIn("lightweight Codex skill + custom-agent workflow", agents)
        self.assertIn("model diversity", agents)
        self.assertIn("extra repo reads, additional tests, ad hoc validation scripts", agents)

    def test_docs_cover_packaging_and_review_hardening(self):
        docs = (ROOT / "docs" / "wise-owl.md").read_text()
        packaging = (ROOT / "docs" / "packaging.md").read_text()
        readme = (ROOT / "README.md").read_text()
        self.assertIn("Review Packet construction must finish before spawning critics", docs)
        self.assertIn("model diversity", docs)
        self.assertIn("Do not merge a blocking security finding", docs)
        self.assertIn("Prime Owl defaults to `gpt-5.5`", docs)
        self.assertIn("Logic Owl/Proof Owl default to `gpt-5.4-mini`", docs)
        self.assertIn("syntax/schema-only", docs)
        self.assertIn("Pass/no-finding results must still validate", docs)
        self.assertIn("A raw critic pass packet with missing, empty, blank, null, or non-string `notes` entries is malformed", docs)
        self.assertIn("A critic-style Prime pass packet", docs)
        self.assertIn("dry-run first", packaging)
        self.assertIn("~/.agents/skills/wise-owl", packaging)
        self.assertIn("~/.agents/skills/wise-owl", readme)
        self.assertNotIn("~/.codex/skills/wise-owl", packaging)
        self.assertNotIn("~/.codex/skills/wise-owl", readme)
        self.assertIn("Use `--force` only after reviewing", packaging)
        self.assertNotIn("--scope user --force", packaging)
        self.assertNotIn("--scope user --force", readme)
        self.assertIn("MIT licensed", readme)
        self.assertIn("Install In 60 Seconds", readme)
        self.assertIn("python3 install.py --dry-run", readme)
        self.assertIn("python3 install.py --check", readme)
        self.assertIn("python3 install.py --uninstall", readme)
        self.assertIn("Python 3.10+", readme)
        self.assertIn("assets/wise-owl-logo-transparent.png", readme)
        self.assertIn("assets/wise-owl-workflow.png", readme)
        self.assertIn("assets/wise-owl-install.png", readme)
        self.assertIn("assets/wise-owl-cli-demo.gif", readme)
        self.assertIn("Wise Owl gives Codex a sharper pre-ship moment", readme)
        self.assertIn("Prime Owl filters the noise", readme)
        self.assertIn("Start from a normal Codex prompt", readme)
        self.assertIn("docs/demo-transcript.md", readme)
        self.assertNotIn("Packaging Checks", readme)
        self.assertNotIn("Known Limitations", readme)
        self.assertIn("--mode standard", docs)
        self.assertIn("pass only when `findings` is empty", docs)
        self.assertIn("managed install manifest", packaging)
        self.assertIn("python3 install.py --check", packaging)
        self.assertIn("python3 install.py --uninstall", packaging)
        self.assertIn("python3 scripts/sync_plugin_assets.py --check", packaging)
        self.assertIn("python3 scripts/verify_release.py", packaging)

    def test_plugin_manifest_references_packaged_logo(self):
        import json

        manifest = json.loads((ROOT / "wise-owl-plugin" / ".codex-plugin" / "plugin.json").read_text())
        self.assertEqual(manifest["interface"]["logo"], "./assets/wise-owl-logo-transparent.png")
        self.assertEqual(manifest["interface"]["composerIcon"], "./assets/wise-owl-logo-transparent.png")
        self.assertEqual(manifest["interface"]["screenshots"], ["./assets/wise-owl-workflow.png"])
        self.assertTrue((ROOT / "wise-owl-plugin" / "assets" / "wise-owl-logo-transparent.png").is_file())
        self.assertTrue((ROOT / "wise-owl-plugin" / "assets" / "wise-owl-workflow.png").is_file())


if __name__ == "__main__":
    unittest.main()
