# Wise Owl Safety And Operations Design

## Goal

Add five focused improvements to the unreleased Wise Owl v0.2 package: safe release-archive boundaries, privacy-minimized review evidence, machine-readable installation diagnostics, installed-copy release smoke tests, and interruption-safe installer writes.

## Scope

The package stays a local Codex skill plus custom-agent workflow. It remains standard-library-only and keeps version metadata at `0.2.0 - Unreleased`. This work does not add hooks, daemons, runtime orchestration, direct model calls, dashboards, reviewer roles, marketplace publishing, or a report-bundle format.

## 1. Release Archive Boundary And Integrity

The archive builder must refuse every symlink selected from the release tree, including symlinks whose targets remain inside the repository. It must also reject any selected path whose resolved location is outside the resolved repository root before calling `stat()` or `read_bytes()`.

This protects a static release tree from accidental path escape. It does not claim protection from a concurrent path-swap race while the archive is being built.

The existing deterministic ZIP metadata remains unchanged. Successful builds also write `wise-owl-v<version>.zip.sha256` containing the lowercase SHA-256 digest and archive filename. Reproducibility tests build into two independent output directories and compare archive bytes and digests.

## 2. Review-Context Minimization

Before reviewers are spawned, the builder must remove raw secrets, tokens, credentials, and protected personal values from the Review Packet. Evidence should name the location and data type and substitute a typed placeholder such as `[REDACTED:credential]`.

Critic prompts must not repeat sensitive values in evidence. Prime Owl must not preserve or repeat a leaked value from critic input. This is best-effort instruction hygiene, not a mechanical sanitizer or confidentiality boundary. Packet schemas remain unchanged.

Contract tests verify that canonical skills, policies, reviewer prompts, Prime prompt, documentation, and generated plugin copies contain consistent guidance and no conflicting guarantee.

## 3. Privacy-Safe Version-Aware Check JSON

`install.py --check --json` emits exactly one JSON document on stdout for normal check success or failure. Check failures do not emit human diagnostics on stderr. The existing default human output and exit codes remain compatible.

The JSON object contains:

- `ok`: whether installation-health errors are absent.
- `scope`: `repo` or `user`.
- `installed_version`: manifest package version or `null`.
- `candidate_version`: version bundled with a distinct invoking distribution or `null`.
- `update_available`: `true` only when a parseable candidate is newer; `false` when equal or older; otherwise `null`.
- `issue_codes`: sorted stable codes.
- `issues`: allowlisted objects containing `code` and optional managed relative `subject` only.
- `suggested_action`: `install`, `upgrade`, `repair`, `review`, or `none`.

The structured result is built directly from allowlisted issue objects, never by parsing human error strings. It must not expose absolute home paths, raw invalid manifest keys, control characters, or raw exception text.

Version rules are explicit:

- No installed manifest: `installed_version=null`, `update_available=null`, action `install`.
- Both versions are three-part numeric versions: compare integer tuples; candidate newer means `true`, equal or older means `false`.
- Candidate unavailable: `candidate_version=null`, `update_available=null`, code `candidate_version_unknown`.
- Either known version is not orderable: `update_available=null`, code `version_unorderable`.

Installation checks also diagnose manifest scope mismatch and legacy `owl_*` agent files. `--json` is accepted only with `--check`.

## 4. Installed-Copy Offline Smoke

The release verifier must exercise both user and repo installation lifecycles inside temporary sandboxes. For each scope it installs and checks the package, then runs the validator script from the installed skill against one known-valid critic packet and one known-invalid critic packet.

Repo scope also patches and verifies the generated Wise Owl policy and installed agent TOMLs. The smoke remains offline and never invokes Codex or a model.

## 5. Secure Per-File Installer Replacement

Every changed installer target is written through an exclusively created same-directory temporary file. The temporary file remains mode `0600` while populated, is flushed and file-synced, receives the intended final mode, and is atomically replaced with `os.replace()`. Existing target modes are preserved; new `config.toml` files use `0600`; other new text files use `0644`. Temporary files are removed in `finally` blocks.

The ownership manifest remains last in write order. The guarantee is limited to preventing torn individual files during process interruption. It is not a cross-file transaction and does not promise power-loss durability.

Failure-injection tests interrupt after multiple replacements and prove:

- each touched file contains either complete old or complete new bytes;
- no temporary file remains;
- permissions are not weakened;
- `--check` diagnoses a partial installation;
- retrying the same candidate succeeds because already-matching candidate bytes are accepted.

## Compatibility And Release Policy

- Existing human CLI output and exit codes remain the default.
- Existing valid v0.1 packet shapes remain valid.
- Packet schemas and stable reviewer role IDs do not change; Lite routing adds the existing Logic Owl role.
- Plugin mirrors remain generated from canonical sources.
- `v0.2.0` remains unreleased; tagging and publishing are outside this work.

## Verification

Each behavior is implemented test-first in the existing unittest modules. Final proof is:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
PYTHONDONTWRITEBYTECODE=1 python3 scripts/sync_plugin_assets.py --check
PYTHONDONTWRITEBYTECODE=1 python3 scripts/verify_release.py
git diff --check
```
