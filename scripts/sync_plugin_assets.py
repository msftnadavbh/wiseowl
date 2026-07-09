#!/usr/bin/env python3
"""Synchronize packaged plugin assets from canonical repository sources."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


AGENT_NAMES = ("logic_owl.toml", "guardian_owl.toml", "proof_owl.toml", "prime_owl.toml")
PUBLIC_ASSETS = (
    "wise-owl-logo.png",
    "wise-owl-logo-transparent.png",
    "wise-owl-workflow.svg",
    "wise-owl-workflow.png",
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def canonical_files(root: Path) -> dict[Path, Path]:
    sources: dict[Path, Path] = {}
    skill_source = root / ".agents" / "skills" / "wise-owl"
    skill_target = root / "wise-owl-plugin" / "skills" / "wise-owl"
    for source in skill_source.rglob("*"):
        if source.is_file() and "__pycache__" not in source.parts and source.suffix != ".pyc":
            sources[skill_target / source.relative_to(skill_source)] = source

    for name in AGENT_NAMES:
        sources[root / "wise-owl-plugin" / "assets" / "agents" / name] = root / ".codex" / "agents" / name
    for name in PUBLIC_ASSETS:
        sources[root / "wise-owl-plugin" / "assets" / name] = root / "assets" / name

    sources[root / "wise-owl-plugin" / "scripts" / "install_wise_owl.py"] = (
        root / ".agents" / "skills" / "wise-owl" / "scripts" / "wise_owl_install.py"
    )
    return sources


def managed_target_files(root: Path) -> set[Path]:
    targets: set[Path] = set()
    for directory in (
        root / "wise-owl-plugin" / "skills" / "wise-owl",
        root / "wise-owl-plugin" / "assets" / "agents",
    ):
        if directory.is_dir():
            targets.update(path for path in directory.rglob("*") if path.is_file())
    targets.add(root / "wise-owl-plugin" / "scripts" / "install_wise_owl.py")
    targets.update(root / "wise-owl-plugin" / "assets" / name for name in PUBLIC_ASSETS)
    return targets


def verify(root: Path) -> list[str]:
    errors: list[str] = []
    expected = canonical_files(root)
    for target, source in sorted(expected.items()):
        if not source.is_file():
            errors.append(f"missing canonical source: {source.relative_to(root)}")
        elif not target.is_file():
            errors.append(f"missing plugin asset: {target.relative_to(root)}")
        elif source.read_bytes() != target.read_bytes():
            errors.append(f"plugin asset drift: {target.relative_to(root)}")

    extras = managed_target_files(root) - set(expected)
    for path in sorted(extras):
        errors.append(f"unexpected managed plugin asset: {path.relative_to(root)}")
    return errors


def sync(root: Path) -> list[Path]:
    expected = canonical_files(root)
    changed: list[Path] = []
    for target, source in sorted(expected.items()):
        if target.is_file() and target.read_bytes() == source.read_bytes():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        changed.append(target)

    for path in sorted(managed_target_files(root) - set(expected)):
        path.unlink()
        changed.append(path)
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Synchronize Wise Owl plugin assets.")
    parser.add_argument("--check", action="store_true", help="Check for drift without writing files.")
    args = parser.parse_args(argv)
    root = repo_root()
    if args.check:
        errors = verify(root)
        if errors:
            print("Plugin asset verification failed:", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            return 1
        print("Plugin assets match canonical sources.")
        return 0

    changed = sync(root)
    if changed:
        print(f"Synchronized {len(changed)} plugin assets.")
    else:
        print("Plugin assets already match canonical sources.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
