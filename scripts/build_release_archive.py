#!/usr/bin/env python3
"""Build the Wise Owl release zip."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT_FILES = ("README.md", "install.py", "LICENSE", "CHANGELOG.md", "AGENTS.md", "MANIFEST.md", ".gitignore")
ROOT_DIRS = (".agents", ".github", "docs", "tests", "scripts", "wise-owl-plugin", "assets")
CODEX_FILES = (".codex/config.toml",)
CODEX_AGENT_DIR = Path(".codex/agents")
EXCLUDED_PARTS = {".git", "dist", "build", "coverage", "superpowers", "__pycache__", ".pytest_cache", ".venv", "venv", "node_modules", "tmp", "temp"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log"}
EXCLUDED_NAMES = {".DS_Store", ".wise-owl-install.json"}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def release_version(root: Path) -> str:
    manifest = root / "wise-owl-plugin" / ".codex-plugin" / "plugin.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    version = data.get("version")
    if not isinstance(version, str) or not version.strip():
        raise ValueError(f"plugin manifest has no valid version: {manifest}")
    return version


def archive_name(root: Path) -> str:
    return f"wise-owl-v{release_version(root)}.zip"


def should_include(path: Path, root: Path | None = None) -> bool:
    try:
        parts = path.relative_to(root).parts if root is not None else path.parts
    except ValueError:
        return False
    if any(part in EXCLUDED_PARTS for part in parts):
        return False
    if path.name in EXCLUDED_NAMES or path.suffix in EXCLUDED_SUFFIXES:
        return False
    if path.name.startswith(".env"):
        return False
    if root is not None:
        current = root
        for part in parts:
            current /= part
            if current.is_symlink():
                return False
        try:
            path.resolve().relative_to(root.resolve())
        except ValueError:
            return False
    elif path.is_symlink():
        return False
    return path.is_file()


def iter_files(root: Path) -> list[Path]:
    files: set[Path] = set()
    for relative in ROOT_FILES + CODEX_FILES:
        path = root / relative
        if should_include(path, root):
            files.add(path.relative_to(root))
    agents_dir = root / CODEX_AGENT_DIR
    if agents_dir.is_dir():
        for path in agents_dir.rglob("*"):
            if should_include(path, root):
                files.add(path.relative_to(root))
    for relative in ROOT_DIRS:
        base = root / relative
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if should_include(path, root):
                files.add(path.relative_to(root))
    return sorted(files, key=lambda path: path.as_posix())


def build_archive(root: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / archive_name(root)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        for relative in iter_files(root):
            source = root / relative
            info = zipfile.ZipInfo(relative.as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            mode = 0o755 if source.stat().st_mode & 0o111 else 0o644
            info.external_attr = mode << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            handle.writestr(info, source.read_bytes())
    write_checksum(archive)
    return archive


def archive_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_checksum(path: Path) -> Path:
    checksum = path.with_name(f"{path.name}.sha256")
    checksum.write_text(f"{archive_sha256(path)}  {path.name}\n", encoding="utf-8")
    return checksum


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Wise Owl release archive.")
    parser.add_argument("--list", action="store_true", help="List selected files without writing an archive.")
    parser.add_argument("--output-dir", type=Path, help="Archive output directory (default: repo dist/).")
    args = parser.parse_args(argv)
    root = repo_root()
    if args.list:
        for path in iter_files(root):
            print(path.as_posix())
        return 0

    verifier = root / "scripts" / "verify_release.py"
    result = subprocess.run([sys.executable, str(verifier)], cwd=root, check=False)
    if result.returncode != 0:
        return result.returncode

    archive = build_archive(root, (args.output_dir or root / "dist").resolve())
    print(f"{archive} ({len(iter_files(root))} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
