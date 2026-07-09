#!/usr/bin/env python3
"""Install Wise Owl skill and agent files."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_GUARDIAN_MODEL = "gpt-5.5"
DEFAULT_PRIME_MODEL = "gpt-5.5"
AGENT_NAMES = ("logic_owl", "guardian_owl", "proof_owl", "prime_owl")
LEGACY_AGENT_NAMES = ("owl_eyes", "owl_guard", "owl_proof")

AGENTS_POLICY = """## Wise Owl Review Policy

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


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[4]


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


def patch_agents_md(existing: str) -> str:
    if "## Wise Owl review policy" in existing or "## Wise Owl Review Policy" in existing:
        return existing if existing.endswith("\n") else existing + "\n"
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


def legacy_agent_paths(agents_dir: Path) -> list[Path]:
    return [agents_dir / f"{name}.toml" for name in LEGACY_AGENT_NAMES if (agents_dir / f"{name}.toml").exists()]


def source_files(template_root: Path, model: str, prime_model: str) -> dict[Path, str]:
    skill_root = template_root / ".agents" / "skills" / "wise-owl"
    agents_root = template_root / ".codex" / "agents"
    if not skill_root.exists():
        raise FileNotFoundError(f"Wise Owl skill templates not found at {skill_root}")
    if not agents_root.exists():
        raise FileNotFoundError(f"Wise Owl agent templates not found at {agents_root}")

    files: dict[Path, str] = {}
    for path in skill_root.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
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


def preflight_conflicts(planned: dict[Path, str], force: bool) -> None:
    if force:
        return
    conflicts: list[Path] = []
    for path, content in sorted(planned.items()):
        if path.name in {"config.toml", "AGENTS.md"}:
            continue
        if path.exists() and path.read_text(encoding="utf-8") != content:
            conflicts.append(path)
    if conflicts:
        joined = ", ".join(str(path) for path in conflicts)
        raise FileExistsError(f"refusing to overwrite existing files; use --force: {joined}")


def write_planned(planned: dict[Path, str], dry_run: bool, force: bool) -> list[Path]:
    if not dry_run:
        preflight_conflicts(planned, force)
    changed: list[Path] = []
    for path, content in sorted(planned.items()):
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
    _, agents_dir, _ = target_paths(scope, repo_root, codex_home, user_skills_home)
    changed = write_planned(planned, dry_run, force)
    changed.extend(handle_legacy_agents(agents_dir, dry_run, force))
    return changed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install Wise Owl for Codex.")
    parser.add_argument("--scope", choices=["repo", "user"], required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--patch-agents-md", action="store_true")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--prime-model", default=DEFAULT_PRIME_MODEL)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(os.environ.get("WISE_OWL_REPO_ROOT", Path.cwd())).resolve()
    codex_home = Path(os.environ.get("WISE_OWL_CODEX_HOME", Path.home() / ".codex")).expanduser().resolve()
    user_skills_home = Path(os.environ.get("WISE_OWL_USER_SKILLS_HOME", Path.home() / ".agents")).expanduser().resolve()
    template_root = Path(os.environ.get("WISE_OWL_TEMPLATE_ROOT", repo_root_from_script())).resolve()
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
    label = "Would change (dry run)" if args.dry_run else "Changed"
    if changed:
        print(f"{label}:")
        for path in changed:
            print(path)
    else:
        print("No changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
