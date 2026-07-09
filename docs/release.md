# Wise Owl Release

Wise Owl v0.1.0 is a local Codex skill and custom-agent workflow. It is not a hosted service, daemon, background hook, custom orchestrator, or direct model API client.

## Checklist

- Confirm `README.md`, `LICENSE`, `CHANGELOG.md`, `AGENTS.md`, `MANIFEST.md`, `docs/`, `tests/`, `.agents/`, `.codex/agents/`, `scripts/`, and `wise-owl-plugin/` are present.
- Run the pre-release validation commands below.
- Build `dist/wise-owl-v0.1.0.zip`.
- Inspect `dist/` and confirm no generated cache dirs remain.
- Commit only after the checks pass.
- Tag only after review.
- For the first public push, verify or add the intended remote, rename the branch to `main`, push `main`, then push only `v0.1.0`.

## Validation

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
python3 -m py_compile \
  install.py \
  .agents/skills/wise-owl/scripts/wise_owl_validate_packet.py \
  .agents/skills/wise-owl/scripts/wise_owl_install.py \
  wise-owl-plugin/scripts/install_wise_owl.py \
  scripts/verify_release.py \
  scripts/build_release_archive.py
PLAYWRIGHT_NODE_MODULES=/tmp/wiseowl-playwright/node_modules node scripts/render_cli_demo.mjs
python3 scripts/verify_release.py
python3 scripts/build_release_archive.py
find . -type d \( -name "__pycache__" -o -name ".pytest_cache" \) -print
```

Plugin drift:

```bash
cmp .agents/skills/wise-owl/SKILL.md wise-owl-plugin/skills/wise-owl/SKILL.md
for f in logic_owl.toml guardian_owl.toml proof_owl.toml prime_owl.toml; do
  cmp ".codex/agents/$f" "wise-owl-plugin/assets/agents/$f"
done
```

## Dogfood

Use Wise Owl Standard on a small docs or validator change. Expect Logic Owl and Proof Owl critic packets, then a Prime Owl packet. Pass packets must include required schema fields.

## Package Contents

The release archive should match `MANIFEST.md`: repo-local skill, custom agent TOMLs, plugin skeleton, docs, tests, scripts, install shortcut, license, changelog, README, AGENTS policy, and assets. README launch assets include the static install/workflow previews and the Codex CLI replay GIF.

## Publish

```bash
git remote -v
git remote add origin git@github.com:OWNER/REPO.git
git branch -M main
git push -u origin main
git tag v0.1.0
git push origin v0.1.0
```

If the remote already exists, inspect it first and do not force-push. Push only the intended `v0.1.0` tag, not all local tags.

## Install

Repo-local:

```bash
python3 .agents/skills/wise-owl/scripts/wise_owl_install.py --scope repo --patch-agents-md
```

User-local:

```bash
python3 .agents/skills/wise-owl/scripts/wise_owl_install.py --scope user --dry-run
python3 .agents/skills/wise-owl/scripts/wise_owl_install.py --scope user
```

Use `--force` only for reviewed overwrite or legacy migration.

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

## Do Not Publish

Do not publish `.git/`, `dist/` drafts, caches, virtualenvs, `.env*`, logs, temporary run artifacts, or local credentials.

## Rollback

Delete the installed skill and agent TOMLs, then restore the previous release archive or git tag. For a bad tag, delete the local tag and remote tag only after confirming no users depend on it.

## Limitations

Parallel execution depends on Codex runtime support. Read-only reviewer instructions complement, but do not replace, runtime sandboxing. Plugin users still need custom agent TOMLs copied into Codex-discovered locations.
