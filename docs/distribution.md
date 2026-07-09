# Wise Owl Distribution

Wise Owl ships as files: a Codex skill, custom agent TOMLs, docs, tests, scripts, and a plugin skeleton. It is not a hosted service, daemon, hook, or direct model API client.

## GitHub Repo

Publish the repository after validation:

```bash
python3 scripts/verify_release.py
git tag v0.1.0
git remote -v
git remote add origin git@github.com:OWNER/REPO.git
git branch -M main
git push -u origin main
git push origin v0.1.0
```

Do not push until the working tree is reviewed and the release archive has been inspected.

## Zip Or Tarball

Build the local zip:

```bash
python3 scripts/build_release_archive.py
```

The archive is written to `dist/wise-owl-v0.1.0.zip`. A tarball can be built from the same included file set if needed.

## Include

- Root files: `README.md`, `install.py`, `LICENSE`, `CHANGELOG.md`, `AGENTS.md`, `MANIFEST.md`, `.gitignore`
- Wise Owl skill under `.agents/skills/wise-owl/`
- Repo-local custom agents under `.codex/agents/`
- `.codex/config.toml`
- Plugin skeleton under `wise-owl-plugin/`
- `docs/`, `tests/`, `scripts/`
- `assets/wise-owl-logo.png`
- `assets/wise-owl-logo-transparent.png`
- `assets/wise-owl-workflow.svg`
- `assets/wise-owl-workflow.png`
- `assets/wise-owl-install.svg`
- `assets/wise-owl-install.png`
- Plugin logo asset under `wise-owl-plugin/assets/wise-owl-logo.png`
- Plugin transparent logo asset under `wise-owl-plugin/assets/wise-owl-logo-transparent.png`
- Plugin workflow screenshot asset under `wise-owl-plugin/assets/wise-owl-workflow.svg`
- Plugin workflow screenshot asset under `wise-owl-plugin/assets/wise-owl-workflow.png`

## Exclude

- `.git/`
- `__pycache__/`, `.pytest_cache/`, `*.pyc`
- `.DS_Store`
- `.venv/`, `venv/`
- `.env`, `.env.*`
- `node_modules/`
- `dist/`, `build/`, `coverage/`
- logs and temporary run artifacts

## Plugin Skeleton

`wise-owl-plugin/` packages the skill, plugin manifest, copied agent TOML assets, logo assets, a workflow screenshot asset, and a plugin installer. Plugin users still need custom agent TOMLs copied into Codex-discovered locations; the plugin installer does that copy.

## User-Local Caveat

User-local install writes the skill to `~/.agents/skills/wise-owl`, custom agents to `~/.codex/agents`, and config to `~/.codex/config.toml`. Run `--dry-run` first. Use `--force` only after reviewing target paths.
