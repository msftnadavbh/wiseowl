#!/usr/bin/env python3
"""Verify Wise Owl release packaging."""

from __future__ import annotations

import sys
from pathlib import Path


AGENTS = ("logic_owl.toml", "guardian_owl.toml", "proof_owl.toml", "prime_owl.toml")

REQUIRED_FILES = (
    "README.md",
    "install.py",
    "LICENSE",
    "CHANGELOG.md",
    "AGENTS.md",
    "MANIFEST.md",
    ".gitignore",
    "assets/wise-owl-logo.png",
    "assets/wise-owl-logo-transparent.png",
    "assets/wise-owl-workflow.svg",
    "assets/wise-owl-workflow.png",
    "assets/wise-owl-install.svg",
    "assets/wise-owl-install.png",
    "assets/wise-owl-cli-demo.gif",
    ".agents/skills/wise-owl/SKILL.md",
    ".agents/skills/wise-owl/scripts/wise_owl_validate_packet.py",
    ".agents/skills/wise-owl/scripts/wise_owl_install.py",
    ".codex/config.toml",
    "docs/wise-owl.md",
    "docs/packaging.md",
    "docs/release.md",
    "docs/distribution.md",
    "docs/demo-transcript.md",
    "scripts/render_cli_demo.mjs",
    "wise-owl-plugin/.codex-plugin/plugin.json",
    "wise-owl-plugin/skills/wise-owl/SKILL.md",
    "wise-owl-plugin/scripts/install_wise_owl.py",
    "wise-owl-plugin/assets/wise-owl-logo.png",
    "wise-owl-plugin/assets/wise-owl-logo-transparent.png",
    "wise-owl-plugin/assets/wise-owl-workflow.svg",
    "wise-owl-plugin/assets/wise-owl-workflow.png",
)

REQUIRED_DIRS = (
    ".agents/skills/wise-owl",
    ".codex/agents",
    "wise-owl-plugin/assets/agents",
    "docs",
    "tests",
    "scripts",
)


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

    repo_skill = root / ".agents" / "skills" / "wise-owl" / "SKILL.md"
    plugin_skill = root / "wise-owl-plugin" / "skills" / "wise-owl" / "SKILL.md"
    if repo_skill.is_file() and plugin_skill.is_file() and repo_skill.read_bytes() != plugin_skill.read_bytes():
        errors.append("plugin skill does not match repo-local skill")

    for name in AGENTS:
        repo_agent = root / ".codex" / "agents" / name
        plugin_agent = root / "wise-owl-plugin" / "assets" / "agents" / name
        if repo_agent.is_file() and plugin_agent.is_file() and repo_agent.read_bytes() != plugin_agent.read_bytes():
            errors.append(f"plugin agent does not match repo agent: {name}")

    changelog = root / "CHANGELOG.md"
    if changelog.is_file() and "v0.1.0" not in changelog.read_text(encoding="utf-8"):
        errors.append("CHANGELOG.md does not contain v0.1.0")
    return errors


def main() -> int:
    root = Path.cwd()
    errors = validate(root)
    if errors:
        print("Release verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Release verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
