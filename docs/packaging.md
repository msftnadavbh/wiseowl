# Wise Owl Packaging

Wise Owl is a Codex skill + custom-agent workflow. It is not a daemon, runtime framework, hosted service, background hook, custom orchestrator, or direct model API client.

Parallel critic execution depends on Codex runtime support. The repo only ships instructions, custom agent TOMLs, validator scripts, fixtures, docs, and installer behavior.

## Repo-Local Install

Recommended flow: dry-run first, then run the non-force install. Use `--force` only after reviewing the target paths and intentionally overwriting or migrating legacy Wise Owl files.

```bash
python3 .agents/skills/wise-owl/scripts/wise_owl_install.py --scope repo --patch-agents-md
```

Dry run:

```bash
python3 .agents/skills/wise-owl/scripts/wise_owl_install.py --scope repo --dry-run --patch-agents-md
```

## User-Local Install

Dry run:

```bash
python3 .agents/skills/wise-owl/scripts/wise_owl_install.py --scope user --dry-run
```

Install:

```bash
python3 .agents/skills/wise-owl/scripts/wise_owl_install.py --scope user
```

Default user-local targets:

- `~/.agents/skills/wise-owl`
- `~/.codex/agents`
- `~/.codex/config.toml`

Use `--force` only after reviewing the dry-run output and intentionally overwriting existing Wise Owl files or removing legacy `owl_*` TOMLs. Custom root overrides from environment variables are intended for tests or unusual local Codex layouts; dry-run first so the resolved roots are visible before a non-dry-run install.

Override for testing:

```bash
WISE_OWL_CODEX_HOME=/tmp/codex-home WISE_OWL_USER_SKILLS_HOME=/tmp/agents-home python3 .agents/skills/wise-owl/scripts/wise_owl_install.py --scope user
```

## Plugin Skeleton

The plugin skeleton is under `wise-owl-plugin/`.

It packages:

- `wise-owl-plugin/.codex-plugin/plugin.json`
- `wise-owl-plugin/skills/wise-owl/SKILL.md`
- `wise-owl-plugin/assets/agents/*.toml`
- `wise-owl-plugin/assets/wise-owl-logo.png`
- `wise-owl-plugin/scripts/install_wise_owl.py`

Custom agent TOMLs still need to be copied into Codex-discovered locations. Use:

```bash
python3 wise-owl-plugin/scripts/install_wise_owl.py --scope user --dry-run
python3 wise-owl-plugin/scripts/install_wise_owl.py --scope user
```

Use plugin `--force` only for reviewed overwrites or legacy migration.

## Uninstall

Repo-local:

```bash
rm -rf .agents/skills/wise-owl
rm -f .codex/agents/logic_owl.toml .codex/agents/guardian_owl.toml .codex/agents/proof_owl.toml .codex/agents/prime_owl.toml
```

User-local:

```bash
rm -rf ~/.agents/skills/wise-owl
rm -f ~/.codex/agents/logic_owl.toml ~/.codex/agents/guardian_owl.toml ~/.codex/agents/proof_owl.toml ~/.codex/agents/prime_owl.toml
```

If legacy files exist, remove them too:

```bash
rm -f ~/.codex/agents/owl_eyes.toml ~/.codex/agents/owl_guard.toml ~/.codex/agents/owl_proof.toml
```

## Known Limitations

- Subagents add latency and token cost.
- Parallel execution depends on Codex runtime support.
- Lite and Standard are faster but reduce coverage compared with Full Council.
- Scripts cannot reliably know the active interactive Codex model.
- Read-only reviewer instructions complement, but do not replace, Codex runtime sandbox and approval policy.
- Plugin assets duplicate repo-local assets and are protected by drift tests.
- Partial review must be treated as degraded confidence.
- Wise Owl mode selection is policy-guided through `SKILL.md` and `AGENTS.md`, not a background hook.

## Release Checklist

- Run `python3 -m unittest discover -s tests`.
- Run `python3 -m py_compile` on all Wise Owl Python scripts.
- Run plugin drift `cmp` checks.
- Run direct validator checks for valid and invalid fixtures.
- Run installer checks in a temp directory.
- Confirm user-local install removes legacy `owl_*` TOMLs only when `--force` is intentionally used.
- Confirm the root `LICENSE` file is present and MIT is selected in `docs/LICENSE_DECISION.md`.
- Update `CHANGELOG.md` v0.1.0 date.
- Tag and publish only after the above pass.
