# Wise Owl Packaging

Wise Owl is a Codex skill + custom-agent workflow. It is not a daemon, runtime framework, hosted service, background hook, custom orchestrator, or direct model API client.

Parallel critic execution depends on Codex runtime support. The repo only ships instructions, custom agent TOMLs, validator scripts, fixtures, docs, and installer behavior.

## Repo-Local Install

Recommended flow: dry-run first, then run the non-force install. Use `--force` only after reviewing the target paths and intentionally overwriting or migrating legacy Wise Owl files.

Repo scope intentionally targets the current working directory. Run the installer from the repository that should receive Wise Owl, or set `WISE_OWL_REPO_ROOT` explicitly.

```bash
python3 .agents/skills/wise-owl/scripts/wise_owl_install.py --scope repo --patch-agents-md
```

Dry run:

```bash
python3 .agents/skills/wise-owl/scripts/wise_owl_install.py --scope repo --dry-run --patch-agents-md
```

## User-Local Install

Fast path from the repository root:

```bash
python3 install.py --dry-run
python3 install.py
python3 install.py --check
```

The shortcut defaults to `--scope user` and delegates to the same hardened installer below. Python 3.10+ is supported, with no third-party Python packages required.

Dry run:

```bash
python3 .agents/skills/wise-owl/scripts/wise_owl_install.py --scope user --dry-run
```

Install:

```bash
python3 .agents/skills/wise-owl/scripts/wise_owl_install.py --scope user
python3 .agents/skills/wise-owl/scripts/wise_owl_install.py --scope user --check
```

Default user-local targets:

- `~/.agents/skills/wise-owl`
- `~/.codex/agents`
- `~/.codex/config.toml`

Use `--force` only after reviewing the dry-run output and intentionally overwriting existing Wise Owl files or removing legacy `owl_*` TOMLs. Custom root overrides from environment variables are intended for tests or unusual local Codex layouts; dry-run first so the resolved roots are visible before a non-dry-run install.

Each completed install writes a managed install manifest at `.wise-owl-install.json` inside the installed skill. It stores hashes only for Wise Owl-owned skill and agent files. A later install upgrades files whose current hashes still match and refuses to overwrite local modifications.

Override for testing:

```bash
WISE_OWL_CODEX_HOME=/tmp/codex-home WISE_OWL_USER_SKILLS_HOME=/tmp/agents-home python3 .agents/skills/wise-owl/scripts/wise_owl_install.py --scope user
```

## Plugin Skeleton

The plugin skeleton is under `wise-owl-plugin/`.

It packages:

- `wise-owl-plugin/.codex-plugin/plugin.json`
- `wise-owl-plugin/skills/wise-owl/SKILL.md`
- `wise-owl-plugin/skills/wise-owl/references/*`
- `wise-owl-plugin/skills/wise-owl/scripts/*`
- `wise-owl-plugin/assets/agents/*.toml`
- `wise-owl-plugin/assets/wise-owl-logo.png`
- `wise-owl-plugin/assets/wise-owl-logo-transparent.png`
- `wise-owl-plugin/assets/wise-owl-workflow.svg`
- `wise-owl-plugin/assets/wise-owl-workflow.png`
- `wise-owl-plugin/scripts/install_wise_owl.py`

Custom agent TOMLs still need to be copied into Codex-discovered locations. Use:

```bash
python3 wise-owl-plugin/scripts/install_wise_owl.py --scope user --dry-run
python3 wise-owl-plugin/scripts/install_wise_owl.py --scope user
```

Use plugin `--force` only for reviewed overwrites or legacy migration.

Plugin files are generated from canonical repository sources. Synchronize them after changing the skill, agents, installer, or packaged images:

```bash
python3 scripts/sync_plugin_assets.py
python3 scripts/sync_plugin_assets.py --check
```

## Uninstall

Repo-local installs created by the installer:

```bash
python3 install.py --scope repo --uninstall
```

User-local:

```bash
python3 install.py --uninstall
```

The uninstaller removes only files whose hashes still match the managed install manifest. Locally modified files are preserved and reported. Shared `config.toml` and `AGENTS.md` content is intentionally left unchanged.

Preview uninstall without writing:

```bash
python3 install.py --uninstall --dry-run
```

Older installations without a managed manifest are not guessed at. Review the dry run and use `--force` once to establish ownership, or review and remove their files manually.

## Operational Notes

- Subagents add latency and token cost.
- Parallel execution depends on Codex runtime support.
- Lite and Standard are faster but reduce coverage compared with Full Council.
- Scripts cannot reliably know the active interactive Codex model.
- Read-only reviewer instructions complement, but do not replace, Codex runtime sandbox and approval policy.
- Plugin assets are generated from canonical repo-local sources and protected by byte-for-byte drift checks.
- Partial review must be treated as degraded confidence.
- Wise Owl mode selection is policy-guided through `SKILL.md` and `AGENTS.md`, not a background hook.

## Release Checklist

- Run `python3 scripts/verify_release.py`.
- Confirm the verifier runs unit, compile, packet, plugin drift, and sandboxed installer checks.
- Optionally regenerate the CLI demo when its source transcript or renderer changes.
- Confirm user-local install removes legacy `owl_*` TOMLs only when `--force` is intentionally used.
- Confirm the root `LICENSE` file is present and MIT is selected in `docs/LICENSE_DECISION.md`.
- Resolve the `v0.2.0` Unreleased heading and date only when publishing that release.
- Tag and publish only after the above pass.
