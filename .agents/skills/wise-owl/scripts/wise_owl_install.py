#!/usr/bin/env python3
"""Install Wise Owl skill and agent files."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_GUARDIAN_MODEL = "gpt-5.5"
DEFAULT_PRIME_MODEL = "gpt-5.5"
AGENT_NAMES = ("logic_owl", "guardian_owl", "proof_owl", "prime_owl")
LEGACY_AGENT_NAMES = ("owl_eyes", "owl_guard", "owl_proof")
MANIFEST_NAME = ".wise-owl-install.json"
MANIFEST_SCHEMA_VERSION = 1

AGENTS_POLICY = """## Wise Owl Review Policy

Use the `wise-owl` skill for non-trivial review, finalization, hardening, second-opinion, or stuck-debug tasks.

Choose the cheapest mode that covers the risk. Escalate, never downgrade, when the task touches security, privacy, tool execution, data boundaries, auth, secrets, protected data, filesystem/network boundaries, production writes, persistence, migrations, concurrency, public API contracts, or release gates.

Modes:
- No Wise Owl: trivial typo, formatting, README-only, pure explanation, tiny copy change, or dependency metadata only when the user did not ask for review.
- Wise Owl Lite: Logic Owl, then Prime Owl for low-risk review, sanity-check, second-opinion, docs, prompts, README updates, small plans, small test-only changes, naming cleanup, or low-risk installer/docs polish.
- Wise Owl Standard: Logic Owl + Proof Owl in parallel, then Prime Owl for normal implementation, non-security multi-file changes, API shape changes without sensitive data, test/CI changes, bug fixes, installer behavior, validator behavior, plugin packaging, or config merge logic.
- Wise Owl Security: Guardian Owl, then Prime Owl for narrowly security/privacy-only review, secret handling, auth boundary checks, third-party AI data exposure, or protected data review.
- Wise Owl Full Council: Logic Owl + Guardian Owl + Proof Owl in parallel, then Prime Owl for auth/authz, secrets/tokens, third-party AI/model provider context, protected student/customer/personal data, MCP/tool execution, filesystem/network boundaries, production writes, cloud/IaC permissions, persistence/migrations, concurrency/state machines, public API contracts, release/CI gates, or explicit Full Council.

Lite mode must not pretend to be a full review: Selected reviewers are Logic Owl and Prime Owl; Guardian Owl and Proof Owl are `not spawned`. Review status is `complete-lite` only when both Logic Owl and Prime Owl return valid packets. If Logic Owl fails or returns a malformed packet, the review is partial and Prime Owl must not turn empty input into a completed Lite review.

Wise Owl reviewers are read-only. The builder owns all edits. Wise Owl remains a lightweight Codex skill + custom-agent workflow with validator support, fixtures, docs, and installer behavior; do not add runtime automation, background hooks, daemons, custom orchestrators, direct model API calls, or scheduling tests.

Every Wise Owl final response must use the `[WISE_OWL_REVIEW]` bracket, include mode, mode selection reason, selected reviewers, model diversity, Prime Owl verdict, accepted findings, rejected findings, execution issues, and builder actions.

Before spawning critics, finish the compact Review Packet. After `[PARALLEL_CRITIC_PHASE]` starts, do not perform unrelated repo inspection, extra repo reads, additional tests, ad hoc validation scripts, scope expansion, edits, or mutating commands while waiting for selected critics. If the packet is incomplete after spawn, mark the review partial/invalid or restart explicitly and report it under `[EXECUTION_ISSUES]`.

Report model diversity honestly, for example `all selected reviewers configured with gpt-5.5`, `Prime Owl gpt-5.5 high; Logic Owl/Proof Owl gpt-5.4-mini high`, or `unavailable`.

If any selected reviewer fails, times out, returns malformed JSON, fails packet validation, or cannot be closed cleanly, set `Review status: partial`. Do not claim Prime Owl adjudication if Prime Owl was not run.

Empty bracket sections may be `none`.
"""

AGENTS_POLICY_V0_1 = """## Wise Owl Review Policy

Use the `wise-owl` skill for non-trivial review, finalization, hardening, second-opinion, or stuck-debug tasks.

Choose the cheapest mode that covers the risk. Escalate, never downgrade, when the task touches security, privacy, tool execution, data boundaries, auth, secrets, protected data, filesystem/network boundaries, production writes, persistence, migrations, concurrency, public API contracts, or release gates.

Modes:
- No Wise Owl: trivial typo, formatting, README-only, pure explanation, tiny copy change, or dependency metadata only when the user did not ask for review.
- Wise Owl Lite: Prime Owl only for low-risk review, sanity-check, second-opinion, docs, prompts, README updates, small plans, small test-only changes, naming cleanup, or low-risk installer/docs polish.
- Wise Owl Standard: Logic Owl + Proof Owl in parallel, then Prime Owl for normal implementation, non-security multi-file changes, API shape changes without sensitive data, test/CI changes, bug fixes, installer behavior, validator behavior, plugin packaging, or config merge logic.
- Wise Owl Security: Guardian Owl, then Prime Owl for narrowly security/privacy-only review, secret handling, auth boundary checks, third-party AI data exposure, or protected data review.
- Wise Owl Full Council: Logic Owl + Guardian Owl + Proof Owl in parallel, then Prime Owl for auth/authz, secrets/tokens, third-party AI/model provider context, protected student/customer/personal data, MCP/tool execution, filesystem/network boundaries, production writes, cloud/IaC permissions, persistence/migrations, concurrency/state machines, public API contracts, release/CI gates, or explicit Full Council.

Lite mode must not pretend to be a full review: Selected reviewers is Prime Owl only; Logic Owl, Guardian Owl, and Proof Owl are `not spawned`; Review status is `complete-lite` when Prime Owl returns a valid packet.

Wise Owl reviewers are read-only. The builder owns all edits. Wise Owl remains a lightweight Codex skill + custom-agent workflow with validator support, fixtures, docs, and installer behavior; do not add runtime automation, background hooks, daemons, custom orchestrators, direct model API calls, or scheduling tests.

Every Wise Owl final response must use the `[WISE_OWL_REVIEW]` bracket, include mode, mode selection reason, selected reviewers, model diversity, Prime Owl verdict, accepted findings, rejected findings, execution issues, and builder actions.

Before spawning critics, finish the compact Review Packet. After `[PARALLEL_CRITIC_PHASE]` starts, do not perform unrelated repo inspection, extra repo reads, additional tests, ad hoc validation scripts, scope expansion, edits, or mutating commands while waiting for selected critics. If the packet is incomplete after spawn, mark the review partial/invalid or restart explicitly and report it under `[EXECUTION_ISSUES]`.

Report model diversity honestly, for example `all selected reviewers configured with gpt-5.5`, `Prime Owl gpt-5.5 high; Logic Owl/Proof Owl gpt-5.4-mini high`, or `unavailable`.

If any selected reviewer fails, times out, returns malformed JSON, fails packet validation, or cannot be closed cleanly, set `Review status: partial`. Do not claim Prime Owl adjudication if Prime Owl was not run.

Empty bracket sections may be `none`.
"""

AGENTS_POLICY_HEADING = re.compile(
    r"^[ \t]{0,3}##[ \t]+wise[ \t]+owl[ \t]+review[ \t]+policy(?:[ \t]+#+)?[ \t]*$",
    re.IGNORECASE,
)


def repo_root_from_script() -> Path:
    script = Path(__file__).resolve()
    for parent in script.parents:
        if (parent / ".agents" / "skills" / "wise-owl").is_dir() and (parent / ".codex" / "agents").is_dir():
            return parent
        if (parent / "skills" / "wise-owl").is_dir() and (parent / "assets" / "agents").is_dir():
            return parent
    return script.parents[4]


def template_source_roots(template_root: Path) -> tuple[Path, Path]:
    repo_skill = template_root / ".agents" / "skills" / "wise-owl"
    repo_agents = template_root / ".codex" / "agents"
    if repo_skill.is_dir() and repo_agents.is_dir():
        return repo_skill, repo_agents

    plugin_skill = template_root / "skills" / "wise-owl"
    plugin_agents = template_root / "assets" / "agents"
    if plugin_skill.is_dir() and plugin_agents.is_dir():
        return plugin_skill, plugin_agents
    raise FileNotFoundError(f"Wise Owl templates not found under {template_root}")


def package_version(template_root: Path) -> str:
    candidates = (
        template_root / "wise-owl-plugin" / ".codex-plugin" / "plugin.json",
        template_root / ".codex-plugin" / "plugin.json",
    )
    for path in candidates:
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        version = data.get("version")
        if isinstance(version, str) and version.strip():
            return version
    installed_manifests = (
        template_root / ".agents" / "skills" / "wise-owl" / MANIFEST_NAME,
        template_root / "skills" / "wise-owl" / MANIFEST_NAME,
    )
    for path in installed_manifests:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        version = data.get("package_version") if isinstance(data, dict) else None
        if isinstance(version, str) and version.strip():
            return version
    return "development"


def merge_config(existing: str) -> str:
    lines = existing.splitlines()
    agents_at = None
    next_section = len(lines)

    for index, line in enumerate(lines):
        stripped = line.strip()
        if not (stripped.startswith("[") and stripped.endswith("]")):
            continue
        if stripped == "[agents]":
            agents_at = index
            next_section = len(lines)
            continue
        if agents_at is not None and index > agents_at:
            next_section = index
            break

    if agents_at is None:
        prefix = existing.rstrip()
        block = "[agents]\nmax_threads = 6\nmax_depth = 1\n"
        return f"{prefix}\n\n{block}" if prefix else block

    section = lines[agents_at + 1 : next_section]
    keys = {line.split("=", 1)[0].strip() for line in section if "=" in line}
    additions: list[str] = []
    if "max_threads" not in keys:
        additions.append("max_threads = 6")
    if "max_depth" not in keys:
        additions.append("max_depth = 1")
    if not additions:
        return existing if existing.endswith("\n") else existing + "\n"

    return "\n".join(lines[:next_section] + additions + lines[next_section:]) + "\n"


def agents_policy_state(existing: str) -> str:
    heading_count = sum(1 for line in existing.splitlines() if AGENTS_POLICY_HEADING.fullmatch(line))
    if heading_count == 0:
        return "absent"
    if heading_count == 1 and existing.count(AGENTS_POLICY) == 1:
        return "current"
    if heading_count == 1 and existing.count(AGENTS_POLICY_V0_1) == 1:
        return "v0.1"
    return "conflict"


def patch_agents_md(existing: str) -> str:
    state = agents_policy_state(existing)
    if state == "current":
        return existing if existing.endswith("\n") else existing + "\n"
    if state == "v0.1":
        upgraded = existing.replace(AGENTS_POLICY_V0_1, AGENTS_POLICY, 1)
        return upgraded if upgraded.endswith("\n") else upgraded + "\n"
    if state == "conflict":
        raise ValueError("AGENTS.md contains a customized or ambiguous Wise Owl Review Policy; refusing to overwrite it")
    prefix = existing.rstrip()
    return f"{prefix}\n\n{AGENTS_POLICY}" if prefix else AGENTS_POLICY


def replace_model(toml: str, model: str) -> str:
    model_literal = json.dumps(model)
    lines = []
    replaced = False
    for line in toml.splitlines():
        if line.startswith("model = "):
            lines.append(f"model = {model_literal}")
            replaced = True
        else:
            lines.append(line)
    if not replaced:
        lines.insert(0, f"model = {model_literal}")
    return "\n".join(lines) + "\n"


def agent_model_for(name: str, model: str, prime_model: str) -> str:
    if name == "prime_owl":
        return prime_model
    if name == "guardian_owl" and model == DEFAULT_MODEL:
        return DEFAULT_GUARDIAN_MODEL
    return model


def target_paths(
    scope: str,
    repo_root: Path,
    codex_home: Path,
    user_skills_home: Path | None = None,
) -> tuple[Path, Path, Path]:
    if scope == "repo":
        return repo_root / ".agents" / "skills" / "wise-owl", repo_root / ".codex" / "agents", repo_root / ".codex" / "config.toml"
    user_skills_home = user_skills_home or codex_home.parent / ".agents"
    return user_skills_home / "skills" / "wise-owl", codex_home / "agents", codex_home / "config.toml"


def allowed_install_roots(
    scope: str,
    repo_root: Path,
    codex_home: Path,
    user_skills_home: Path | None = None,
    include_repo: bool = False,
) -> tuple[Path, ...]:
    if scope == "repo":
        return (repo_root,)
    roots = (codex_home, user_skills_home or codex_home.parent / ".agents")
    return roots + ((repo_root,) if include_repo else ())


def legacy_agent_paths(agents_dir: Path) -> list[Path]:
    return [agents_dir / f"{name}.toml" for name in LEGACY_AGENT_NAMES if (agents_dir / f"{name}.toml").exists()]


def source_files(template_root: Path, model: str, prime_model: str) -> dict[Path, str]:
    skill_root, agents_root = template_source_roots(template_root)

    files: dict[Path, str] = {}
    for path in skill_root.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc" and path.name != MANIFEST_NAME:
            files[path.relative_to(skill_root)] = path.read_text(encoding="utf-8")

    for name in AGENT_NAMES:
        filename = f"{name}.toml"
        agent_model = agent_model_for(name, model, prime_model)
        files[Path("..") / ".." / ".codex-agents" / filename] = replace_model(
            (agents_root / filename).read_text(encoding="utf-8"),
            agent_model,
        )
    return files


def plan_install(
    scope: str,
    repo_root: Path,
    codex_home: Path,
    model: str,
    prime_model: str,
    patch_agents: bool,
    template_root: Path | None = None,
    user_skills_home: Path | None = None,
) -> dict[Path, str]:
    template_root = template_root or repo_root_from_script()
    skill_dir, agents_dir, config_path = target_paths(scope, repo_root, codex_home, user_skills_home)
    planned: dict[Path, str] = {}

    for relative, content in source_files(template_root, model, prime_model).items():
        if relative.parts[:2] == ("..", ".."):
            planned[agents_dir / relative.name] = content
        else:
            planned[skill_dir / relative] = content

    planned[config_path] = merge_config(config_path.read_text(encoding="utf-8") if config_path.exists() else "")
    if patch_agents:
        agents_md = repo_root / "AGENTS.md"
        planned[agents_md] = patch_agents_md(agents_md.read_text(encoding="utf-8") if agents_md.exists() else "")
    return planned


def content_digest(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def managed_key(path: Path, skill_dir: Path, agents_dir: Path) -> str | None:
    try:
        return f"skill/{path.relative_to(skill_dir).as_posix()}"
    except ValueError:
        pass
    try:
        relative = path.relative_to(agents_dir)
    except ValueError:
        return None
    if relative.name in {f"{name}.toml" for name in AGENT_NAMES} and len(relative.parts) == 1:
        return f"agent/{relative.as_posix()}"
    return None


def path_for_managed_key(key: str, skill_dir: Path, agents_dir: Path) -> Path | None:
    prefix, separator, relative = key.partition("/")
    if not separator or not relative or relative.startswith("/") or ".." in Path(relative).parts:
        return None
    if prefix == "skill":
        return skill_dir / relative
    if prefix == "agent" and len(Path(relative).parts) == 1:
        return agents_dir / relative
    return None


def load_install_manifest(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid managed install manifest at {path}: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ValueError(f"invalid managed install manifest at {path}: unsupported schema")
    files = data.get("files")
    if not isinstance(files, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in files.items()):
        raise ValueError(f"invalid managed install manifest at {path}: files must map paths to hashes")
    return data


def manifest_content(scope: str, version: str, files: dict[str, str]) -> str:
    data = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "package_version": version,
        "scope": scope,
        "files": dict(sorted(files.items())),
    }
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def previous_managed_hashes(
    manifest: dict[str, Any] | None,
    skill_dir: Path,
    agents_dir: Path,
) -> dict[Path, str]:
    hashes: dict[Path, str] = {}
    if not manifest:
        return hashes
    for key, digest in manifest["files"].items():
        path = path_for_managed_key(key, skill_dir, agents_dir)
        if path is not None:
            hashes[path] = digest
    return hashes


def stale_managed_hashes(
    manifest: dict[str, Any] | None,
    current_keys: set[str],
    skill_dir: Path,
    agents_dir: Path,
) -> dict[Path, str]:
    stale: dict[Path, str] = {}
    if not manifest:
        return stale
    for key, digest in manifest["files"].items():
        if key in current_keys:
            continue
        path = path_for_managed_key(key, skill_dir, agents_dir)
        if path is not None:
            stale[path] = digest
    return stale


def preflight_stale_files(stale_hashes: dict[Path, str], force: bool) -> None:
    if force:
        return
    conflicts = [path for path, digest in sorted(stale_hashes.items()) if path.exists() and file_digest(path) != digest]
    if conflicts:
        joined = ", ".join(str(path) for path in conflicts)
        raise FileExistsError(f"refusing to remove locally modified managed files: {joined}")


def ensure_safe_write_targets(planned: dict[Path, str], allowed_roots: tuple[Path, ...]) -> None:
    resolved_roots = tuple(root.resolve() for root in allowed_roots)
    for path in planned:
        resolved = path.resolve(strict=False)
        inside_boundary = any(resolved == root or root in resolved.parents for root in resolved_roots)
        if path.is_symlink():
            raise ValueError(f"refusing symlink write target: {path} -> {resolved}")
        if not inside_boundary:
            raise ValueError(f"refusing write target outside install roots: {path} -> {resolved}")


def remove_stale_files(stale_hashes: dict[Path, str], dry_run: bool) -> list[Path]:
    stale = [path for path in sorted(stale_hashes) if path.exists()]
    if not dry_run:
        for path in stale:
            path.unlink()
    return stale


def preflight_conflicts(
    planned: dict[Path, str],
    force: bool,
    previous_hashes: dict[Path, str] | None = None,
) -> None:
    if force:
        return
    previous_hashes = previous_hashes or {}
    conflicts: list[Path] = []
    for path, content in sorted(planned.items()):
        if path.name in {"config.toml", "AGENTS.md", MANIFEST_NAME}:
            continue
        if not path.exists() or path.read_text(encoding="utf-8") == content:
            continue
        previous_digest = previous_hashes.get(path)
        if previous_digest is None or file_digest(path) != previous_digest:
            conflicts.append(path)
    if conflicts:
        joined = ", ".join(str(path) for path in conflicts)
        if previous_hashes:
            raise FileExistsError(f"refusing to overwrite locally modified managed files: {joined}")
        raise FileExistsError(f"refusing to overwrite existing files; use --force: {joined}")


def write_planned(
    planned: dict[Path, str],
    dry_run: bool,
    force: bool,
    previous_hashes: dict[Path, str] | None = None,
) -> list[Path]:
    if not dry_run:
        preflight_conflicts(planned, force, previous_hashes)
    changed: list[Path] = []
    ordered = sorted(planned.items(), key=lambda item: (item[0].name == MANIFEST_NAME, str(item[0])))
    for path, content in ordered:
        old = path.read_text(encoding="utf-8") if path.exists() else None
        if old == content:
            continue
        changed.append(path)
        if not dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    return changed


def handle_legacy_agents(agents_dir: Path, dry_run: bool, force: bool) -> list[Path]:
    legacy = legacy_agent_paths(agents_dir)
    if not legacy:
        return []
    if not force:
        print(
            "Warning: legacy Wise Owl agent TOMLs are present; rerun with --force to remove: "
            + ", ".join(str(path) for path in legacy),
            file=sys.stderr,
        )
        return []
    if not dry_run:
        for path in legacy:
            path.unlink()
    return legacy


def install(
    scope: str,
    repo_root: Path,
    codex_home: Path,
    user_skills_home: Path | None = None,
    dry_run: bool = False,
    force: bool = False,
    patch_agents: bool = False,
    model: str = DEFAULT_MODEL,
    prime_model: str = DEFAULT_PRIME_MODEL,
    template_root: Path | None = None,
) -> list[Path]:
    planned = plan_install(scope, repo_root, codex_home, model, prime_model, patch_agents, template_root, user_skills_home)
    skill_dir, agents_dir, _ = target_paths(scope, repo_root, codex_home, user_skills_home)
    manifest_path = skill_dir / MANIFEST_NAME
    previous_manifest = load_install_manifest(manifest_path) if manifest_path.exists() else None
    previous_hashes = previous_managed_hashes(previous_manifest, skill_dir, agents_dir)
    managed_files = {
        key: content_digest(content)
        for path, content in planned.items()
        if (key := managed_key(path, skill_dir, agents_dir)) is not None
    }
    stale_hashes = stale_managed_hashes(previous_manifest, set(managed_files), skill_dir, agents_dir)
    template_root = template_root or repo_root_from_script()
    planned[manifest_path] = manifest_content(scope, package_version(template_root), managed_files)
    if not dry_run:
        ensure_safe_write_targets(
            planned,
            allowed_install_roots(scope, repo_root, codex_home, user_skills_home, include_repo=patch_agents),
        )
        preflight_stale_files(stale_hashes, force)
    changed = write_planned(planned, dry_run, force, previous_hashes)
    changed.extend(remove_stale_files(stale_hashes, dry_run))
    if not dry_run:
        remove_empty_skill_dirs(skill_dir)
    changed.extend(handle_legacy_agents(agents_dir, dry_run, force))
    return changed


def parse_toml(path: Path) -> dict[str, Any] | None:
    try:
        import tomllib
    except ModuleNotFoundError:
        return None
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def check_install(
    scope: str,
    repo_root: Path,
    codex_home: Path,
    user_skills_home: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    skill_dir, agents_dir, config_path = target_paths(scope, repo_root, codex_home, user_skills_home)
    allowed_roots = allowed_install_roots(scope, repo_root, codex_home, user_skills_home)
    skill_path = skill_dir / "SKILL.md"
    if not skill_path.is_file():
        errors.append(f"missing skill: {skill_path}")
    else:
        skill = skill_path.read_text(encoding="utf-8")
        frontmatter = skill.split("---", 2)[1] if skill.count("---") >= 2 else ""
        if "name: wise-owl" not in frontmatter or "description:" not in frontmatter:
            errors.append(f"invalid skill frontmatter: {skill_path}")

    for name in AGENT_NAMES:
        path = agents_dir / f"{name}.toml"
        if not path.is_file():
            errors.append(f"missing agent TOML: {path.name}")
            continue
        parsed = parse_toml(path)
        if parsed == {}:
            errors.append(f"invalid agent TOML: {path.name}")
        elif parsed is not None:
            if parsed.get("name") != name:
                errors.append(f"agent name mismatch: {path.name}")
            if parsed.get("sandbox_mode") != "read-only":
                errors.append(f"agent is not read-only: {path.name}")
            if not isinstance(parsed.get("developer_instructions"), str) or not parsed["developer_instructions"].strip():
                errors.append(f"missing developer_instructions: {path.name}")
        else:
            text = path.read_text(encoding="utf-8")
            if f'name = "{name}"' not in text or 'sandbox_mode = "read-only"' not in text or "developer_instructions" not in text:
                errors.append(f"invalid agent TOML: {path.name}")

    if not config_path.is_file():
        errors.append(f"missing config: {config_path}")
    else:
        config = parse_toml(config_path)
        if config == {}:
            errors.append(f"invalid config TOML: {config_path}")
        elif config is not None:
            agents = config.get("agents")
            if not isinstance(agents, dict) or "max_threads" not in agents or "max_depth" not in agents:
                errors.append(f"config is missing [agents] max_threads/max_depth: {config_path}")
        else:
            text = config_path.read_text(encoding="utf-8")
            if "[agents]" not in text or "max_threads" not in text or "max_depth" not in text:
                errors.append(f"config is missing [agents] max_threads/max_depth: {config_path}")

    agents_md = repo_root / "AGENTS.md"
    if scope == "repo" and agents_md.is_file():
        policy_state = agents_policy_state(agents_md.read_text(encoding="utf-8"))
        if policy_state == "v0.1":
            errors.append(f"obsolete v0.1 Wise Owl Review Policy in {agents_md}; rerun with --patch-agents-md")
        elif policy_state == "conflict":
            errors.append(f"customized or ambiguous Wise Owl Review Policy in {agents_md}; review it manually")

    manifest_path = skill_dir / MANIFEST_NAME
    manifest_safe = True
    if manifest_path.is_symlink():
        errors.append(f"managed install manifest must not be a symlink: {manifest_path}")
        manifest_safe = False
    else:
        try:
            ensure_safe_write_targets({manifest_path: ""}, allowed_roots)
        except ValueError as exc:
            errors.append(str(exc))
            manifest_safe = False
    if manifest_safe and not manifest_path.is_file():
        errors.append(f"missing managed install manifest: {manifest_path}")
    elif manifest_safe:
        try:
            manifest = load_install_manifest(manifest_path)
        except ValueError as exc:
            errors.append(str(exc))
        else:
            for key, expected_digest in manifest["files"].items():
                path = path_for_managed_key(key, skill_dir, agents_dir)
                if path is None:
                    errors.append(f"invalid managed path in manifest: {key}")
                elif path.is_symlink():
                    errors.append(f"managed file must not be a symlink: {path}")
                else:
                    try:
                        ensure_safe_write_targets({path: ""}, allowed_roots)
                    except ValueError as exc:
                        errors.append(str(exc))
                    else:
                        if not path.is_file():
                            errors.append(f"missing managed file: {path}")
                        elif file_digest(path) != expected_digest:
                            errors.append(f"locally modified managed file: {path}")
    return errors


def remove_empty_skill_dirs(skill_dir: Path) -> None:
    if not skill_dir.exists():
        return
    directories = sorted((path for path in skill_dir.rglob("*") if path.is_dir()), key=lambda path: len(path.parts), reverse=True)
    directories.append(skill_dir)
    for directory in directories:
        try:
            directory.rmdir()
        except OSError:
            pass


def uninstall(
    scope: str,
    repo_root: Path,
    codex_home: Path,
    user_skills_home: Path | None = None,
    dry_run: bool = False,
) -> tuple[list[Path], list[Path]]:
    skill_dir, agents_dir, _ = target_paths(scope, repo_root, codex_home, user_skills_home)
    manifest_path = skill_dir / MANIFEST_NAME
    allowed_roots = allowed_install_roots(scope, repo_root, codex_home, user_skills_home)
    ensure_safe_write_targets({manifest_path: ""}, allowed_roots)
    if not manifest_path.is_file():
        raise FileNotFoundError(f"managed install manifest not found: {manifest_path}")
    manifest = load_install_manifest(manifest_path)
    managed_paths = {
        path: ""
        for key in manifest["files"]
        if (path := path_for_managed_key(key, skill_dir, agents_dir)) is not None
    }
    ensure_safe_write_targets(managed_paths, allowed_roots)
    removed: list[Path] = []
    preserved: list[Path] = []
    preserved_files: dict[str, str] = {}
    for key, expected_digest in sorted(manifest["files"].items()):
        path = path_for_managed_key(key, skill_dir, agents_dir)
        if path is None or not path.exists():
            continue
        if file_digest(path) != expected_digest:
            preserved.append(path)
            preserved_files[key] = expected_digest
            continue
        removed.append(path)
        if not dry_run:
            path.unlink()

    if preserved_files:
        if not dry_run:
            manifest_path.write_text(
                manifest_content(scope, str(manifest.get("package_version", "unknown")), preserved_files),
                encoding="utf-8",
            )
    else:
        removed.append(manifest_path)
        if not dry_run:
            manifest_path.unlink(missing_ok=True)
    if not dry_run:
        remove_empty_skill_dirs(skill_dir)
    return removed, preserved


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog=os.environ.get("WISE_OWL_INSTALL_PROG"), description="Install Wise Owl for Codex.")
    parser.add_argument(
        "--scope",
        choices=["repo", "user"],
        default="user",
        help="Install scope (default: user; repo uses current working directory).",
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="Verify an existing installation without changing files.")
    action.add_argument("--uninstall", action="store_true", help="Remove unchanged Wise Owl-owned files.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--patch-agents-md", action="store_true")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--prime-model", default=DEFAULT_PRIME_MODEL)
    parser.add_argument("--verbose", action="store_true", help="List every changed path.")
    return parser.parse_args(argv)


def print_target_summary(
    scope: str,
    repo_root: Path,
    codex_home: Path,
    user_skills_home: Path,
) -> None:
    skill_dir, agents_dir, config_path = target_paths(scope, repo_root, codex_home, user_skills_home)
    print("Targets:")
    print(f"  Skill:  {skill_dir}")
    print(f"  Agents: {agents_dir}")
    print(f"  Config: {config_path}")


def main() -> int:
    args = parse_args()
    repo_root = Path(os.environ.get("WISE_OWL_REPO_ROOT", Path.cwd())).resolve()
    codex_home = Path(os.environ.get("WISE_OWL_CODEX_HOME", Path.home() / ".codex")).expanduser().resolve()
    user_skills_home = Path(os.environ.get("WISE_OWL_USER_SKILLS_HOME", Path.home() / ".agents")).expanduser().resolve()
    template_root = Path(os.environ.get("WISE_OWL_TEMPLATE_ROOT", repo_root_from_script())).resolve()
    if args.check:
        errors = check_install(args.scope, repo_root, codex_home, user_skills_home)
        if errors:
            print(f"Wise Owl check failed for {args.scope} scope:", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            return 1
        print(f"Wise Owl check passed for {args.scope} scope.")
        return 0
    if args.uninstall:
        try:
            removed, preserved = uninstall(args.scope, repo_root, codex_home, user_skills_home, args.dry_run)
        except (FileNotFoundError, ValueError) as exc:
            print(f"Wise Owl uninstall failed: {exc}", file=sys.stderr)
            return 1
        label = "Would remove (dry run)" if args.dry_run else "Removed"
        print(f"{label} {len(removed)} Wise Owl-owned files.")
        if preserved:
            print("Preserved locally modified files:", file=sys.stderr)
            for path in preserved:
                print(f"- {path}", file=sys.stderr)
        print("Shared config.toml and AGENTS.md entries were left unchanged.")
        return 1 if preserved else 0
    try:
        changed = install(
            args.scope,
            repo_root,
            codex_home,
            user_skills_home=user_skills_home,
            dry_run=args.dry_run,
            force=args.force,
            patch_agents=args.patch_agents_md,
            model=args.model,
            prime_model=args.prime_model,
            template_root=template_root,
        )
    except (FileExistsError, ValueError) as exc:
        print(f"Wise Owl install failed: {exc}", file=sys.stderr)
        return 1
    if args.dry_run:
        print(f"Wise Owl dry run for {args.scope} scope.")
        print_target_summary(args.scope, repo_root, codex_home, user_skills_home)
        print(f"Would change {len(changed)} files.")
        if args.verbose:
            for path in changed:
                print(path)
        print("No files were written.")
        return 0

    print(f"Updated {len(changed)} files." if changed else "Wise Owl is already up to date.")
    if args.verbose:
        for path in changed:
            print(path)
    print(f"Wise Owl installed for {args.scope} scope.")
    print("Restart or reopen Codex.")
    print('Then ask: "Use Wise Owl Standard to review this change."')
    print("Run this installer with --check to verify anytime.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
