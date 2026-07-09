#!/usr/bin/env python3
"""Build the Wise Owl v0.1.0 release zip."""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path


VERSION = "v0.1.0"
ARCHIVE_NAME = f"wise-owl-{VERSION}.zip"
ROOT_FILES = ("README.md", "LICENSE", "CHANGELOG.md", "AGENTS.md", "MANIFEST.md", ".gitignore")
ROOT_DIRS = (".agents", "docs", "tests", "scripts", "wise-owl-plugin", "assets")
CODEX_FILES = (".codex/config.toml",)
CODEX_AGENT_DIR = Path(".codex/agents")
EXCLUDED_PARTS = {".git", "dist", "build", "coverage", "__pycache__", ".pytest_cache", ".venv", "venv", "node_modules", "tmp", "temp"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log"}
EXCLUDED_NAMES = {".DS_Store"}


def should_include(path: Path) -> bool:
    if any(part in EXCLUDED_PARTS for part in path.parts):
        return False
    if path.name in EXCLUDED_NAMES or path.suffix in EXCLUDED_SUFFIXES:
        return False
    if path.name.startswith(".env"):
        return False
    return path.is_file()


def iter_files(root: Path) -> list[Path]:
    files: set[Path] = set()
    for relative in ROOT_FILES + CODEX_FILES:
        path = root / relative
        if should_include(path):
            files.add(path.relative_to(root))
    if CODEX_AGENT_DIR.is_dir():
        for path in (root / CODEX_AGENT_DIR).rglob("*"):
            if should_include(path):
                files.add(path.relative_to(root))
    for relative in ROOT_DIRS:
        base = root / relative
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if should_include(path):
                files.add(path.relative_to(root))
    return sorted(files, key=lambda p: p.as_posix())


def main() -> int:
    root = Path.cwd()
    verifier = root / "scripts" / "verify_release.py"
    result = subprocess.run([sys.executable, str(verifier)], cwd=root)
    if result.returncode != 0:
        return result.returncode

    files = iter_files(root)
    dist = root / "dist"
    dist.mkdir(exist_ok=True)
    archive = dist / ARCHIVE_NAME
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        for relative in files:
            handle.write(root / relative, relative.as_posix())
    print(f"{archive} ({len(files)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
