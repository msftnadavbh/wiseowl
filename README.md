<p align="center">
  <img src="assets/wise-owl-logo-transparent.png" alt="Wise Owl logo" width="190">
</p>

<h1 align="center">Wise Owl</h1>

<p align="center">
  <strong>A second-opinion review ritual for Codex, ready in one minute.</strong>
</p>

<p align="center">
  <a href="#install-in-60-seconds">Install</a>
  &nbsp;|&nbsp;
  <a href="#watch-it-work">Demo</a>
  &nbsp;|&nbsp;
  <a href="docs/wise-owl.md">Workflow guide</a>
  &nbsp;|&nbsp;
  <a href="docs/packaging.md">Docs</a>
  &nbsp;|&nbsp;
  <a href="LICENSE">MIT</a>
</p>

Wise Owl gives Codex a sharper pre-ship moment. Ask for a review, let focused read-only reviewers inspect the diff, and get one Prime Owl verdict instead of a pile of loose opinions.

Use it when a change matters enough that "looks fine" is not enough.

<p align="center">
  <img src="assets/wise-owl-workflow.png" alt="Wise Owl workflow preview">
</p>

## Install In 60 Seconds

```bash
git clone https://github.com/msftnadavbh/wiseowl.git
cd wiseowl

python3 install.py --dry-run
python3 install.py
```

Restart or reopen Codex, then ask:

```text
Use Wise Owl Standard to review this change before I finalize.
```

That is the whole first run. The dry run previews the install, and the normal run adds the Wise Owl skill, the custom reviewer agents, and the small Codex config merge.

<p align="center">
  <img src="assets/wise-owl-install.png" alt="Wise Owl install preview">
</p>

## Why You'll Keep It

- One calm final check before you ship.
- Reviewers with clear jobs: logic, safety, proof, and judgment.
- Prime Owl filters the noise and turns review into an action list.
- Works from normal Codex prompts, no new app to babysit.
- Local-first package: skill files, custom-agent TOMLs, docs, fixtures, and validator support.
- Your setup lives in your Codex environment, without a separate Wise Owl account or dashboard.

## Watch It Work

<p align="center">
  <img src="assets/wise-owl-cli-demo.gif" alt="Wise Owl Codex CLI demo">
</p>

Start from a normal Codex prompt. Wise Owl Standard selects reviewers, collects read-only feedback, and returns a Prime Owl verdict with one final action list. The demo is based on a disposable-repo Codex CLI run; the source excerpt is in [docs/demo-transcript.md](docs/demo-transcript.md).

## Pick The Right Review

| Mode | Reviewers | Use It For |
| --- | --- | --- |
| Lite | Prime Owl only | Quick sanity checks, docs, prompts, small plans |
| Standard | Logic Owl + Proof Owl, then Prime Owl | Normal implementation, tests, packaging, installer changes |
| Security | Guardian Owl, then Prime Owl | Auth, privacy, secrets, permissions, sensitive data |
| Full Council | Logic Owl + Guardian Owl + Proof Owl, then Prime Owl | Release gates, public APIs, filesystem/network boundaries, high-risk changes |

Ask in plain language:

```text
Use Wise Owl Lite to sanity-check this README change.
```

```text
Use Wise Owl Full Council for this release gate.
```

## Meet The Owls

- **Logic Owl** checks correctness, contracts, edge cases, and runtime behavior.
- **Guardian Owl** checks security, privacy, permissions, secrets, and unsafe operations.
- **Proof Owl** checks tests, validation, CI confidence, and evidence quality.
- **Prime Owl** judges the critic output, rejects weak findings, ranks real issues, and gives Codex one builder-facing packet.

## What Gets Installed

- `~/.agents/skills/wise-owl`: the Codex skill.
- `~/.codex/agents`: the read-only custom reviewer TOMLs.
- `~/.codex/config.toml`: a safe merge for Codex agent settings.

First-time installs should use the dry run and normal install shown above. `--force` exists for intentional overwrites or legacy agent cleanup.

## Docs

- [docs/wise-owl.md](docs/wise-owl.md): workflow, modes, schemas, and examples.
- [docs/packaging.md](docs/packaging.md): install, uninstall, plugin skeleton, and release checklist.
- [docs/distribution.md](docs/distribution.md): package contents and archive expectations.
- [docs/release.md](docs/release.md): maintainer validation and release commands.

## License

MIT licensed.
