<p align="center">
  <img src="assets/wise-owl-logo.png" alt="Wise Owl logo" width="260">
</p>

# Wise Owl

**Multi-agent second-opinion review workflow for Codex.**

Status: `v0.1.0`

Wise Owl is a lightweight Codex skill + custom-agent workflow for disciplined review before risky edits or release gates. The builder remains the only editor. Logic Owl, Guardian Owl, and Proof Owl are read-only critics; Prime Owl reduces their packets into one builder-facing decision.

It exists to make reviews less noisy: critics return strict JSON, Prime Owl rejects weak findings, and the builder applies only accepted blocking items unless the user asks for broader cleanup.

Wise Owl is not a daemon, hosted service, background hook, runtime framework, custom orchestrator, or direct model API client.

## Quick Start

Repo-local install is the safest first path:

```bash
python3 .agents/skills/wise-owl/scripts/wise_owl_install.py --scope repo --dry-run --patch-agents-md
python3 .agents/skills/wise-owl/scripts/wise_owl_install.py --scope repo --patch-agents-md
```

User-local install should also be previewed first:

```bash
python3 .agents/skills/wise-owl/scripts/wise_owl_install.py --scope user --dry-run
python3 .agents/skills/wise-owl/scripts/wise_owl_install.py --scope user
```

User-local install writes the skill to `~/.agents/skills/wise-owl`, custom agents to `~/.codex/agents`, and config to `~/.codex/config.toml`. Use `--force` only after reviewing target paths and intentionally overwriting or migrating legacy Wise Owl files.

## Modes

- **Lite**: Prime Owl only for low-risk review, sanity-checks, docs, prompts, README updates, and small plans.
- **Standard**: Logic Owl + Proof Owl, then Prime Owl for normal implementation, validator, installer, packaging, and CI/test changes.
- **Security**: Guardian Owl, then Prime Owl for narrowly security/privacy-focused review.
- **Full Council**: Logic Owl + Guardian Owl + Proof Owl, then Prime Owl for high-risk or cross-boundary work.

Parallel critic execution depends on Codex runtime support. Wise Owl only provides prompt/runtime guidance, agent TOMLs, schemas, docs, fixtures, and validator scripts.

## Roles

- **Logic Owl** (`logic_owl`): correctness, contracts, edge cases, runtime behavior.
- **Guardian Owl** (`guardian_owl`): security, privacy, permissions, secrets, unsafe operations.
- **Proof Owl** (`proof_owl`): tests, validation, CI confidence, false-positive checks.
- **Prime Owl** (`prime_owl`): judge that deduplicates, rejects noise, ranks severity, and produces one review packet.

## Validator Examples

```bash
python3 .agents/skills/wise-owl/scripts/wise_owl_validate_packet.py \
  --type critic \
  --file tests/fixtures/critic_valid_logic_pass.json

python3 .agents/skills/wise-owl/scripts/wise_owl_validate_packet.py \
  --type prime \
  --file tests/fixtures/prime_valid_pass_empty.json

python3 .agents/skills/wise-owl/scripts/wise_owl_validate_packet.py \
  --type prime \
  --file tests/fixtures/prime_valid_current_fix_required_api_auth_and_storage.json \
  --critics tests/fixtures/critic_current_guardian_owl_api_auth_and_storage.json \
            tests/fixtures/critic_current_proof_owl_persistence_and_routes.json
```

Without `--critics`, Prime Owl validation is syntax/schema-only and source accounting is not checked.

## Packaging

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
python3 -m py_compile \
  .agents/skills/wise-owl/scripts/wise_owl_validate_packet.py \
  .agents/skills/wise-owl/scripts/wise_owl_install.py \
  wise-owl-plugin/scripts/install_wise_owl.py \
  scripts/verify_release.py \
  scripts/build_release_archive.py
python3 scripts/verify_release.py
python3 scripts/build_release_archive.py
```

The release archive is generated locally under `dist/` and should generally not be committed.

The plugin skeleton under `wise-owl-plugin/` packages the skill and plugin assets. Custom-agent TOMLs still need to be copied into Codex-discovered locations by the installer unless future Codex plugin docs add first-class custom-agent registration.

## Known Limitations

- Model names are configurable and depend on models available in the local Codex environment.
- Model diversity depends on available Codex models.
- Parallel execution depends on Codex runtime support.
- Read-only reviewer instructions complement, but do not replace, runtime sandbox and approval policy.
- Plugin custom-agent TOMLs may still need installer copy into Codex-discovered locations.

## Docs

- [docs/wise-owl.md](docs/wise-owl.md): workflow, modes, schemas, and limitations.
- [docs/packaging.md](docs/packaging.md): install, uninstall, plugin skeleton, and release checklist.
- [docs/distribution.md](docs/distribution.md): package contents and archive expectations.
- [docs/release.md](docs/release.md): v0.1.0 release validation.

## License

MIT. The MIT license decision is recorded in [docs/LICENSE_DECISION.md](docs/LICENSE_DECISION.md).
