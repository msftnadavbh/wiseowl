#!/usr/bin/env python3
"""Run deterministic Wise Owl release verification."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import py_compile
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

AGENTS = ("logic_owl.toml", "guardian_owl.toml", "proof_owl.toml", "prime_owl.toml")
REQUIRED_FILES = (
    "README.md",
    "install.py",
    "LICENSE",
    "CHANGELOG.md",
    "AGENTS.md",
    "MANIFEST.md",
    ".gitignore",
    ".github/workflows/verify.yml",
    "assets/wise-owl-logo.png",
    "assets/wise-owl-logo-transparent.png",
    "assets/wise-owl-workflow.svg",
    "assets/wise-owl-workflow.png",
    "assets/wise-owl-install.svg",
    "assets/wise-owl-install.png",
    "assets/wise-owl-cli-demo.gif",
    ".agents/skills/wise-owl/SKILL.md",
    ".agents/skills/wise-owl/references/finding-schema.md",
    ".agents/skills/wise-owl/references/severity-rubric.md",
    ".agents/skills/wise-owl/scripts/wise_owl_validate_packet.py",
    ".agents/skills/wise-owl/scripts/wise_owl_install.py",
    ".codex/config.toml",
    "docs/wise-owl.md",
    "docs/packaging.md",
    "docs/release.md",
    "docs/distribution.md",
    "docs/demo-transcript.md",
    "scripts/render_cli_demo.mjs",
    "scripts/sync_plugin_assets.py",
    "tests/test_release_scripts.py",
    "tests/test_wise_owl_install.py",
    "tests/test_wise_owl_validate_packet.py",
    "tests/fixtures/release_archive_members.txt",
    "wise-owl-plugin/.codex-plugin/plugin.json",
    "wise-owl-plugin/skills/wise-owl/SKILL.md",
    "wise-owl-plugin/skills/wise-owl/references/finding-schema.md",
    "wise-owl-plugin/skills/wise-owl/references/severity-rubric.md",
    "wise-owl-plugin/skills/wise-owl/scripts/wise_owl_validate_packet.py",
    "wise-owl-plugin/scripts/install_wise_owl.py",
    "wise-owl-plugin/assets/wise-owl-logo.png",
    "wise-owl-plugin/assets/wise-owl-logo-transparent.png",
    "wise-owl-plugin/assets/wise-owl-workflow.svg",
    "wise-owl-plugin/assets/wise-owl-workflow.png",
)
REQUIRED_DIRS = (
    ".agents/skills/wise-owl",
    ".codex/agents",
    ".github/workflows",
    "wise-owl-plugin/assets/agents",
    "wise-owl-plugin/skills/wise-owl/references",
    "wise-owl-plugin/skills/wise-owl/scripts",
    "docs",
    "tests",
    "scripts",
)
PYTHON_FILES = (
    "install.py",
    ".agents/skills/wise-owl/scripts/wise_owl_validate_packet.py",
    ".agents/skills/wise-owl/scripts/wise_owl_install.py",
    "wise-owl-plugin/scripts/install_wise_owl.py",
    "scripts/sync_plugin_assets.py",
    "scripts/verify_release.py",
    "scripts/build_release_archive.py",
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def release_version(root: Path) -> str:
    manifest = root / "wise-owl-plugin" / ".codex-plugin" / "plugin.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    version = data.get("version")
    if not isinstance(version, str) or not version.strip():
        raise ValueError(f"plugin manifest has no valid version: {manifest}")
    return version


def load_script(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            errors.append(f"missing required file: {relative}")
    for relative in REQUIRED_DIRS:
        if not (root / relative).is_dir():
            errors.append(f"missing required directory: {relative}")
    for name in AGENTS:
        if not (root / ".codex" / "agents" / name).is_file():
            errors.append(f"missing repo agent TOML: {name}")
        if not (root / "wise-owl-plugin" / "assets" / "agents" / name).is_file():
            errors.append(f"missing plugin agent TOML: {name}")

    sync_path = root / "scripts" / "sync_plugin_assets.py"
    if sync_path.is_file():
        try:
            sync_plugin_assets = load_script(sync_path, "wise_owl_sync_plugin_assets")
            errors.extend(sync_plugin_assets.verify(root))
        except Exception as exc:  # pragma: no cover - defensive release error reporting
            errors.append(f"could not verify plugin assets: {exc}")

    try:
        version = release_version(root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
    else:
        changelog = root / "CHANGELOG.md"
        if changelog.is_file() and f"## v{version}" not in changelog.read_text(encoding="utf-8"):
            errors.append(f"CHANGELOG.md does not contain v{version}")
        manifest = root / "MANIFEST.md"
        if manifest.is_file() and f"# Wise Owl v{version} Manifest" not in manifest.read_text(encoding="utf-8"):
            errors.append(f"MANIFEST.md does not identify v{version}")
    return errors


def compile_checks(root: Path) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory)
        for index, relative in enumerate(PYTHON_FILES):
            try:
                py_compile.compile(str(root / relative), cfile=str(output / f"{index}.pyc"), doraise=True)
            except py_compile.PyCompileError as exc:
                errors.append(f"compile failed for {relative}: {exc.msg}")
    return errors


def run_command(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> tuple[int, str, str]:
    result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    return result.returncode, result.stdout, result.stderr


def unit_test_checks(root: Path) -> list[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    code, stdout, stderr = run_command([sys.executable, "-m", "unittest", "discover", "-s", "tests"], root, env)
    if code != 0:
        return [f"unit tests failed:\n{stdout}{stderr}"]
    summaries = re.findall(r"^Ran (\d+) tests? in \d+(?:\.\d+)?s\r?$", stderr, re.MULTILINE)
    if not summaries:
        return ["unit test discovery did not report a test count"]
    if int(summaries[-1]) == 0:
        return ["unit test discovery reported zero tests"]
    return []


def validator_smoke(root: Path) -> list[str]:
    validator = root / ".agents" / "skills" / "wise-owl" / "scripts" / "wise_owl_validate_packet.py"
    fixtures = root / "tests" / "fixtures"
    cases = (
        (["--type", "critic", "--file", str(fixtures / "critic_valid_blocked.json")], 0),
        (["--type", "prime", "--file", str(fixtures / "prime_valid_pass_empty.json")], 0),
        (
            [
                "--type",
                "prime",
                "--file",
                str(fixtures / "prime_valid_split_docs_security_and_release_hygiene.json"),
                "--critics",
                str(fixtures / "critic_release_logic_owl.json"),
                str(fixtures / "critic_release_guardian_owl.json"),
                str(fixtures / "critic_release_proof_owl.json"),
                "--mode",
                "full",
            ],
            0,
        ),
        (
            [
                "--type",
                "prime",
                "--file",
                str(fixtures / "prime_invalid_stale_source_ids_and_verdict_mismatch.json"),
                "--critics",
                str(fixtures / "critic_current_guardian_owl_api_auth_and_storage.json"),
                str(fixtures / "critic_current_proof_owl_persistence_and_routes.json"),
            ],
            1,
        ),
    )
    errors: list[str] = []
    for args, expected in cases:
        code, stdout, stderr = run_command([sys.executable, str(validator), *args], root)
        if code != expected:
            errors.append(f"validator smoke expected exit {expected}, got {code}:\n{stdout}{stderr}")
    return errors


def installer_smoke(root: Path, sandbox: Path) -> list[str]:
    installer = root / "install.py"
    repo_target = sandbox / "repo"
    codex_home = sandbox / "home" / ".codex"
    skills_home = sandbox / "home" / ".agents"
    repo_target.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(sandbox / "home"),
            "PYTHONDONTWRITEBYTECODE": "1",
            "WISE_OWL_REPO_ROOT": str(repo_target),
            "WISE_OWL_CODEX_HOME": str(codex_home),
            "WISE_OWL_USER_SKILLS_HOME": str(skills_home),
            "WISE_OWL_TEMPLATE_ROOT": str(root),
        }
    )
    errors: list[str] = []
    dry_run = [sys.executable, str(installer), "--scope", "user", "--dry-run"]
    code, stdout, stderr = run_command(dry_run, repo_target, env)
    if code != 0:
        errors.append(f"installer dry-run failed:\n{stdout}{stderr}")
    if codex_home.exists() or skills_home.exists():
        errors.append("installer dry-run wrote to the sandbox")

    for command, label in (
        ([sys.executable, str(installer), "--scope", "user"], "install"),
        ([sys.executable, str(installer), "--scope", "user", "--check"], "check"),
        ([sys.executable, str(installer), "--scope", "user"], "second install"),
        (
            [sys.executable, str(installer), "--scope", "repo", "--patch-agents-md"],
            "repo install",
        ),
        ([sys.executable, str(installer), "--scope", "repo", "--check"], "repo check"),
    ):
        code, stdout, stderr = run_command(command, repo_target, env)
        if code != 0:
            errors.append(f"installer {label} failed:\n{stdout}{stderr}")

    installed_copies = (
        skills_home / "skills" / "wise-owl",
        repo_target / ".agents" / "skills" / "wise-owl",
    )
    fixture_cases = (
        (root / "tests" / "fixtures" / "critic_valid_blocked.json", 0),
        (root / "tests" / "fixtures" / "critic_invalid_blocked_without_blocking.json", 1),
    )
    for skill in installed_copies:
        validator = skill / "scripts" / "wise_owl_validate_packet.py"
        for fixture, expected in fixture_cases:
            command = [sys.executable, str(validator), "--type", "critic", "--file", str(fixture)]
            code, stdout, stderr = run_command(command, repo_target, env)
            if code != expected:
                errors.append(
                    f"installed validator {validator} expected exit {expected}, got {code}:\n{stdout}{stderr}"
                )

    for agents_dir in (codex_home / "agents", repo_target / ".codex" / "agents"):
        for name in AGENTS:
            if not (agents_dir / name).is_file():
                errors.append(f"installed agent is not discoverable: {agents_dir / name}")
    if not (repo_target / "AGENTS.md").is_file():
        errors.append("installed repo policy is not discoverable: AGENTS.md")
    return errors


def cache_errors(root: Path) -> list[str]:
    return [
        f"generated cache directory remains: {path.relative_to(root)}"
        for path in root.rglob("*")
        if path.is_dir() and path.name in {"__pycache__", ".pytest_cache"}
    ]


def full_verification(root: Path) -> list[str]:
    errors = validate(root)
    if errors:
        return errors
    errors.extend(compile_checks(root))
    errors.extend(unit_test_checks(root))
    errors.extend(validator_smoke(root))
    with tempfile.TemporaryDirectory() as directory:
        errors.extend(installer_smoke(root, Path(directory)))
    errors.extend(cache_errors(root))
    return errors


def print_errors(label: str, errors: list[str]) -> None:
    print(f"{label} failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify Wise Owl release readiness.")
    parser.add_argument("--static", action="store_true", help="Run file, version, and drift checks only.")
    args = parser.parse_args(argv)
    root = repo_root()
    errors = validate(root) if args.static else full_verification(root)
    if errors:
        print_errors("Static release verification" if args.static else "Release verification", errors)
        return 1
    print("Static release verification passed." if args.static else "Release verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
