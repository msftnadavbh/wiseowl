# Changelog

## v0.2.0 - Unreleased

- Made release archives reproducible, excluded symlinks and out-of-root paths, and added SHA-256 sidecars.
- Added exact non-pass JSON contracts for every reviewer and Prime Owl.
- Added critic verdict semantics, mode-aware reviewer-set validation, and duplicate-role rejection.
- Changed Lite to Logic Owl followed by Prime Owl so pass, caution, and fix-required results have accountable critic sources.
- Clarified all-rejected Prime passes; all valid v0.1 packet shapes remain valid.
- Made malformed JSON packets return validation errors instead of tracebacks.
- Hardened the release gate against missing suites and zero-test discovery.
- Extended the release gate to exercise sandboxed user and repo installations, installed validators, agent discovery, and repo policy discovery.
- Added a safe migration for the exact generated v0.1 AGENTS.md policy and controlled conflicts for customized policy blocks.
- Added installation checks, managed upgrades, and safe uninstall behavior.
- Added privacy-safe `--check --json` output with stable issue codes, manifest-scope and legacy-agent diagnostics, and explicit version/update semantics.
- Added canonical plugin asset generation with complete skill references and scripts.
- Added one deterministic release verifier and a Python 3.10, 3.12, and 3.14 CI matrix.
- Replaced the malformed demo source with schema-valid critic and Prime packets.

## v0.1.0 - 2026-07-09

- Added Wise Owl repo-local Codex skill and read-only custom agent TOMLs.
- Added stable roles: Logic Owl, Guardian Owl, Proof Owl, and Prime Owl.
- Added Lite, Standard, Security, and Full Council routing guidance.
- Added fixed `[WISE_OWL_REVIEW]` output bracket.
- Added packet validator with Prime Owl verdict semantics and source accounting.
- Added installer for repo-local and user-local Codex locations.
- Added plugin skeleton with drift-tested copied skill and agent assets.
- Added fixtures for valid, invalid, stale-source, and privacy/security review packets.
- Added docs for packaging, limitations, release preparation, and MIT licensing.
- Added release verification script, local archive helper, release manifest, and distribution docs.
