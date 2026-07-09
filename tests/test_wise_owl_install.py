import importlib.util
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
        self.assertIn("Would change (dry run):", result.stdout)
        self.assertFalse((self.root / ".agents").exists())

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
        self.assertIn("Would change (dry run):", result.stdout)
        self.assertIn(str(self.user_skills_home / "skills" / "wise-owl"), result.stdout)
        self.assertFalse((self.user_skills_home / "skills").exists())

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
            ROOT / "wise-owl-plugin",
            plugin_installer.DEFAULT_MODEL,
            plugin_installer.DEFAULT_PRIME_MODEL,
            False,
        )
        plugin_installer.write_planned(dry_changed, dry_run=True, force=False)
        self.assertFalse((self.user_skills_home / "skills").exists())

        changed = plugin_installer.write_planned(dry_changed, dry_run=False, force=False)
        self.assertTrue(changed)
        self.assertTrue((self.user_skills_home / "skills" / "wise-owl" / "SKILL.md").exists())
        self.assertTrue((self.codex_home / "agents" / "prime_owl.toml").exists())

    def test_plugin_conflict_preflight_writes_nothing(self):
        plugin_installer = load_plugin_installer()
        planned = plugin_installer.plan_install(
            "user",
            self.root,
            self.codex_home,
            ROOT / "wise-owl-plugin",
            plugin_installer.DEFAULT_MODEL,
            plugin_installer.DEFAULT_PRIME_MODEL,
            False,
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
            ROOT / "wise-owl-plugin",
            plugin_installer.DEFAULT_MODEL,
            plugin_installer.DEFAULT_PRIME_MODEL,
            False,
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
        self.assertIn("If no accepted findings remain, return exactly:", prime)
        self.assertIn('"accepted_findings": []', prime)
        self.assertIn('"rejected_findings": []', prime)
        self.assertIn('"No Wise Owl accepted findings remain."', prime)
        self.assertIn("do not return role", prime)
        self.assertIn("do not omit accepted_findings, rejected_findings, or builder_instructions", prime)

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
        self.assertIn("MIT license decision", readme)
        self.assertIn("Install In 60 Seconds", readme)
        self.assertIn("python3 install.py --dry-run", readme)
        self.assertIn("assets/wise-owl-logo-transparent.png", readme)
        self.assertIn("assets/wise-owl-workflow.png", readme)
        self.assertIn("assets/wise-owl-install.png", readme)

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
