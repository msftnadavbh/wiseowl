# Wise Owl Safety And Operations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement five approved safety and operator improvements without changing Wise Owl's role model, packet schemas, runtime architecture, or unreleased v0.2 version.

**Architecture:** Extend the existing archive, installer, release-verifier, prompt, and test surfaces in place. Structured installation issues become the single source for both human and JSON check output; generated plugin files continue to come only from `scripts/sync_plugin_assets.py`.

**Tech Stack:** Python 3.10+ standard library, unittest, TOML agent prompts, Markdown documentation.

## Global Constraints

- Keep plugin version `0.2.0` and changelog status `Unreleased`.
- Use only the Python standard library; add no dependencies.
- Add no hooks, daemons, runtime orchestrators, direct model calls, dashboards, reviewer roles, marketplace publishing, or report-bundle format.
- Preserve existing human CLI output and exit codes unless a task explicitly defines the new `--json` path.
- Preserve all valid v0.1 packet shapes and stable reviewer role IDs; mode routing may reuse existing roles.
- Treat redaction as best-effort instruction hygiene, not a mechanical sanitizer or confidentiality guarantee.
- Treat installer replacement as per-file torn-write/process-interruption safety, not a cross-file transaction or power-loss guarantee.
- Follow TDD: each production behavior starts with a focused failing test and a confirmed expected failure.

---

### Task 1: Secure And Checksum Release Archives

**Files:**
- Modify: `scripts/build_release_archive.py`
- Modify: `tests/test_release_scripts.py`
- Modify: `docs/release.md`
- Modify: `docs/distribution.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Produces: `should_include(path: Path, root: Path | None = None) -> bool`
- Produces: `archive_sha256(path: Path) -> str`
- Produces: `write_checksum(path: Path) -> Path`
- Preserves: `build_archive(root: Path, output_dir: Path) -> Path`

- [ ] **Step 1: Write failing archive-boundary and checksum tests**

Add tests that create internal and external symlinks under a temporary release root, assert neither appears in `iter_files()`, build archives into two output directories, compare bytes, and verify checksum sidecars contain `<digest>  <archive-name>`.

- [ ] **Step 2: Run the focused tests and confirm RED**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_release_scripts.ReleaseScriptTests.test_archive_rejects_symlinks tests.test_release_scripts.ReleaseScriptTests.test_archive_build_is_reproducible_and_checksummed
```

Expected: failure because symlinks are followed and checksum helpers do not exist.

- [ ] **Step 3: Implement the minimal archive changes**

Reject `path.is_symlink()`, reject resolved paths outside `root.resolve()`, retain fixed `ZipInfo`, compute SHA-256 in chunks, and write the sidecar after a successful build.

- [ ] **Step 4: Run focused and module tests**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_release_scripts.py'
```

Expected: all release-script tests pass.

- [ ] **Step 5: Update release documentation and commit**

```bash
git add scripts/build_release_archive.py tests/test_release_scripts.py docs/release.md docs/distribution.md CHANGELOG.md
git commit -m "feat: secure Wise Owl release archives"
```

### Task 2: Minimize Sensitive Review Context

**Files:**
- Modify: `.agents/skills/wise-owl/SKILL.md`
- Modify: `.codex/agents/logic_owl.toml`
- Modify: `.codex/agents/guardian_owl.toml`
- Modify: `.codex/agents/proof_owl.toml`
- Modify: `.codex/agents/prime_owl.toml`
- Modify: `.agents/skills/wise-owl/scripts/wise_owl_install.py`
- Modify: `AGENTS.md`
- Modify: `docs/wise-owl.md`
- Modify: `tests/test_wise_owl_install.py`
- Generated: `wise-owl-plugin/**`

**Interfaces:**
- Preserves critic and Prime JSON schemas.
- Adds the exact placeholder example `[REDACTED:credential]` to canonical guidance.

- [ ] **Step 1: Write failing prompt-contract tests**

Require all critic prompts to instruct location/type evidence without raw sensitive values, Prime to avoid preserving leaked values, SKILL/AGENTS policy to minimize Review Packets before spawn, and docs to call the guidance best-effort rather than sanitization.

- [ ] **Step 2: Run the focused test and confirm RED**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_wise_owl_install.WiseOwlInstallTests.test_review_evidence_guidance_is_privacy_minimized
```

Expected: failure because the guidance is absent.

- [ ] **Step 3: Add minimal canonical guidance**

Update canonical prompts, SKILL, AGENTS policy text embedded in the installer, root AGENTS policy, and workflow docs. Do not add packet fields or claim enforcement.

- [ ] **Step 4: Regenerate plugin copies and run tests**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/sync_plugin_assets.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_wise_owl_install.py'
PYTHONDONTWRITEBYTECODE=1 python3 scripts/sync_plugin_assets.py --check
```

Expected: prompt tests pass and generated assets match.

- [ ] **Step 5: Commit**

```bash
git add .agents .codex AGENTS.md docs/wise-owl.md tests/test_wise_owl_install.py wise-owl-plugin
git commit -m "feat: minimize sensitive review evidence"
```

### Task 3: Add Privacy-Safe Version-Aware Check JSON

**Files:**
- Modify: `.agents/skills/wise-owl/scripts/wise_owl_install.py`
- Modify: `tests/test_wise_owl_install.py`
- Modify: `README.md`
- Modify: `docs/packaging.md`
- Modify: `docs/wise-owl.md`
- Modify: `CHANGELOG.md`
- Generated: `wise-owl-plugin/scripts/install_wise_owl.py`
- Generated: `wise-owl-plugin/skills/wise-owl/scripts/wise_owl_install.py`

**Interfaces:**
- Produces: `CheckIssue(code: str, message: str, subject: str | None = None)`
- Produces: `collect_check_issues(...) -> list[CheckIssue]`
- Preserves: `check_install(...) -> list[str]`
- Produces: `check_json_result(...) -> dict[str, Any]`
- Adds CLI: `install.py --check --json`

- [ ] **Step 1: Write failing JSON contract tests**

Cover one-document stdout, empty stderr on normal check failures, stable issue codes/subjects, no absolute paths/raw keys/control characters/exceptions, manifest scope mismatch, legacy agents, `--json` without `--check`, and existing human output compatibility.

- [ ] **Step 2: Write failing version truth-table tests**

Cover not installed, candidate unknown, equal, candidate newer, installed newer, and unorderable version strings. Assert only candidate-newer yields `true`; equal/older yields `false`; all unknown cases yield `null` with the defined code.

- [ ] **Step 3: Run focused tests and confirm RED**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_wise_owl_install.WiseOwlInstallTests.test_check_json_is_privacy_safe tests.test_wise_owl_install.WiseOwlInstallTests.test_check_json_version_truth_table
```

Expected: failure because `--json`, structured issues, and version semantics do not exist.

- [ ] **Step 4: Implement structured issues as the source of truth**

Add an immutable `CheckIssue` dataclass. Move check branches to `collect_check_issues()`, render existing strings through `check_install()`, and serialize only `code` plus optional allowlisted `subject` in JSON.

- [ ] **Step 5: Implement version and CLI semantics**

Add bundled-candidate detection that does not fall back to the installed manifest, numeric three-part parsing, the explicit truth table, `--json` validation, and single-document output.

- [ ] **Step 6: Run installer tests and sync generated assets**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_wise_owl_install.py'
PYTHONDONTWRITEBYTECODE=1 python3 scripts/sync_plugin_assets.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/sync_plugin_assets.py --check
```

Expected: installer tests pass and assets match.

- [ ] **Step 7: Document and commit**

```bash
git add .agents/skills/wise-owl/scripts/wise_owl_install.py tests/test_wise_owl_install.py README.md docs/packaging.md docs/wise-owl.md CHANGELOG.md wise-owl-plugin
git commit -m "feat: add structured Wise Owl install checks"
```

### Task 4: Exercise Installed Copies In Release Verification

**Files:**
- Modify: `scripts/verify_release.py`
- Modify: `tests/test_release_scripts.py`
- Modify: `docs/release.md`
- Modify: `docs/packaging.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Extends: `installer_smoke(root: Path, sandbox: Path) -> list[str]`

- [ ] **Step 1: Write failing installed-copy smoke tests**

Use a temporary sandbox to assert user and repo installs/checks run, installed validators accept a valid critic and reject an invalid critic, repo AGENTS policy exists, and installed agent TOMLs exist.

- [ ] **Step 2: Run the focused test and confirm RED**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_release_scripts.ReleaseScriptTests.test_installer_smoke_exercises_installed_user_and_repo_copies
```

Expected: failure because current smoke covers only user install/check/reinstall.

- [ ] **Step 3: Extend the existing smoke minimally**

Reuse `run_command()`, existing fixtures, and existing sandbox environment. Add repo install/check with policy patch and run validator scripts from both installed skill paths.

- [ ] **Step 4: Run release tests and full verifier**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_release_scripts.py'
PYTHONDONTWRITEBYTECODE=1 python3 scripts/verify_release.py
```

Expected: release tests and verifier pass.

- [ ] **Step 5: Document and commit**

```bash
git add scripts/verify_release.py tests/test_release_scripts.py docs/release.md docs/packaging.md CHANGELOG.md
git commit -m "test: exercise installed Wise Owl copies"
```

### Task 5: Make Installer Writes Secure And Interruption-Safe Per File

**Files:**
- Modify: `.agents/skills/wise-owl/scripts/wise_owl_install.py`
- Modify: `tests/test_wise_owl_install.py`
- Modify: `docs/packaging.md`
- Modify: `docs/wise-owl.md`
- Modify: `CHANGELOG.md`
- Generated: `wise-owl-plugin/scripts/install_wise_owl.py`
- Generated: `wise-owl-plugin/skills/wise-owl/scripts/wise_owl_install.py`

**Interfaces:**
- Produces: `atomic_write_text(path: Path, content: str) -> None`
- Preserves: `write_planned(...) -> list[Path]`

- [ ] **Step 1: Write failing atomic-write tests**

Assert exclusive same-directory temp files, mode `0600` while populated, preserved existing modes, new config mode `0600`, other new text mode `0644`, complete old-or-new bytes after injected replacement failure, no orphan temp, and controlled CLI failure.

- [ ] **Step 2: Write failing partial-upgrade retry test**

Inject failure after several replacements, assert `--check` reports partial state, rerun the same candidate without force, and assert install/check succeeds with manifest written last.

- [ ] **Step 3: Run focused tests and confirm RED**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_wise_owl_install.WiseOwlInstallTests.test_atomic_write_preserves_bytes_modes_and_cleanup tests.test_wise_owl_install.WiseOwlInstallTests.test_interrupted_upgrade_retries_same_candidate
```

Expected: failure because writes use `Path.write_text()` directly.

- [ ] **Step 4: Implement minimal per-file replacement**

Use `tempfile.mkstemp(dir=path.parent)`, `os.fdopen()`, flush, `os.fsync()`, `os.chmod()`, `os.replace()`, and `finally` cleanup. Keep manifest ordering. Catch `OSError` in CLI entry points for controlled output. Do not add rollback or directory-fsync claims.

- [ ] **Step 5: Run installer tests and sync**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_wise_owl_install.py'
PYTHONDONTWRITEBYTECODE=1 python3 scripts/sync_plugin_assets.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/sync_plugin_assets.py --check
```

Expected: installer tests pass and assets match.

- [ ] **Step 6: Document and commit**

```bash
git add .agents/skills/wise-owl/scripts/wise_owl_install.py tests/test_wise_owl_install.py docs/packaging.md docs/wise-owl.md CHANGELOG.md wise-owl-plugin
git commit -m "feat: make Wise Owl installer writes atomic"
```

### Task 6: Final Synchronization And Verification

**Files:**
- Verify all changed files.

**Interfaces:**
- Consumes all prior task outputs; produces no new public API.

- [ ] **Step 1: Regenerate and verify plugin assets**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/sync_plugin_assets.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/sync_plugin_assets.py --check
```

- [ ] **Step 2: Run the complete test and release gates**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
PYTHONDONTWRITEBYTECODE=1 python3 scripts/verify_release.py
git diff --check
```

Expected: all tests pass, release verification passes, and no whitespace errors are reported.

- [ ] **Step 3: Inspect final state**

```bash
git status --short --branch
git diff --stat main...HEAD
```

Expected: only intended branch commits and no uncommitted generated drift.

- [ ] **Step 4: Run Wise Owl Full Council final review**

Build a complete Review Packet from the branch diff and fresh checks. Validate every critic and Prime packet with `--mode full` and full source accounting. Apply accepted blockers and rerun affected checks.
