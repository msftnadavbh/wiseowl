# Wise Owl Release

Wise Owl v0.2.0 is an unreleased local Codex skill and custom-agent workflow. It is not a hosted service, daemon, background hook, custom orchestrator, or direct model API client.

Python 3.10+ is supported. The Python tooling uses only the standard library.

## Release Gate

Run the canonical gate from any working directory:

```bash
python3 scripts/verify_release.py
```

The gate checks required files, version metadata, complete plugin drift, Python compilation, all unit tests with a nonzero discovery count, direct valid and invalid packet fixtures, and generated cache cleanliness. Its fully sandboxed installer smoke test exercises user install/check/reinstall and repo install/check lifecycles, discovers installed agent TOMLs and the repo policy, and runs each installed validator copy against known valid and invalid critic fixtures.

Static-only verification is available for fast packaging checks:

```bash
python3 scripts/verify_release.py --static
```

GitHub Actions runs the same full command on Python 3.10, 3.12, and 3.14.

## Plugin Sync

Plugin skill files, custom-agent TOMLs, the standalone installer, and packaged images are generated from canonical repository sources:

```bash
python3 scripts/sync_plugin_assets.py
python3 scripts/sync_plugin_assets.py --check
```

The full release gate includes the check command.

## Demo Asset

The CLI replay is optional for normal CI. Regenerate it only when `docs/demo-transcript.md` or `scripts/render_cli_demo.mjs` changes:

```bash
PLAYWRIGHT_NODE_MODULES=/tmp/wiseowl-playwright/node_modules node scripts/render_cli_demo.mjs
```

The transcript contains schema-valid Logic Owl, Proof Owl, and Prime Owl packets and is validated by the unit suite.

## Build

Build the local archive only after the gate passes:

```bash
python3 scripts/build_release_archive.py
```

The version comes from `wise-owl-plugin/.codex-plugin/plugin.json`, must be a safe filename component, and produces the direct output children `dist/wise-owl-v0.2.0.zip` and `dist/wise-owl-v0.2.0.zip.sha256`. Archive entries use fixed metadata for reproducible builds. For a static release tree, the builder excludes symlinks and rejects selected paths that resolve outside the release root. This protection does not cover concurrent path replacement while the archive is being built. Verify the sidecar with `(cd dist && shasum -a 256 -c wise-owl-v0.2.0.zip.sha256)`, then inspect the archive before tagging.

## Dogfood

Run Wise Owl Standard on the final diff. Validate Logic Owl and Proof Owl packets, then validate Prime Owl with `--mode standard` and both critic files. Report partial status if any selected reviewer or packet fails.

## Publish Checklist

- Resolve the `v0.2.0 - Unreleased` changelog heading with the release date.
- Run `python3 scripts/verify_release.py`.
- Build, checksum-verify, and inspect `dist/wise-owl-v0.2.0.zip`.
- Confirm `git status` contains only intended release changes.
- Commit and tag only after review.
- Push only the intended branch and `v0.2.0` tag.

```bash
git remote -v
git tag v0.2.0
git push origin main
git push origin v0.2.0
```

Do not force-push. Do not publish `.git/`, `dist/` drafts, caches, virtualenvs, `.env*`, logs, temporary artifacts, or credentials.

## Install Check

```bash
python3 install.py --dry-run
python3 install.py
python3 install.py --check
```

## Uninstall

```bash
python3 install.py --uninstall --dry-run
python3 install.py --uninstall
```

Only unchanged Wise Owl-owned files are removed. Locally modified files are preserved, and shared `config.toml` and `AGENTS.md` content remains in place for manual review.

Parallel execution depends on Codex runtime support. Read-only reviewer instructions complement Codex sandboxing and approval policy.
