# Task 5 Implementation Report

## Outcome

Implemented secure, interruption-safe per-file installer replacement while preserving the existing `write_planned(...) -> list[Path]` interface.

## TDD Evidence

- RED: the two focused tests failed because `atomic_write_text` and the `tempfile` integration did not exist and direct `Path.write_text()` never reached the injected `os.replace()` interruption.
- GREEN: both focused tests passed after the minimal standard-library implementation.
- Regression: all installer tests, the complete unit suite, the release verifier, and plugin asset drift checks passed.

## Implementation

- Added `atomic_write_text(path, content)` using an exclusive same-directory `tempfile.mkstemp()` file.
- Kept the temporary file at `0600` while writing, then flushed and file-synced it before applying the destination mode and calling `os.replace()`.
- Preserved modes for existing destinations; new `config.toml` files use `0600`, and other new text files use `0644`.
- Removed temporary files in a `finally` block after success or failure.
- Routed planned installer writes and preserved-manifest uninstall rewrites through the atomic helper.
- Preserved manifest-last ordering.
- Added controlled `OSError` handling to install and uninstall CLI paths.
- Documented the exact boundary: complete per-file old-or-new bytes under process interruption, without cross-file rollback, directory-fsync, or power-loss durability claims.

## Tests Added

- `test_atomic_write_preserves_bytes_modes_and_cleanup`
  - same-directory exclusive temporary creation through `mkstemp`
  - `0600` temporary mode while populated
  - flush/file sync execution
  - existing-mode preservation
  - new config/text modes
  - complete old bytes and cleanup after injected replacement failure
  - controlled CLI write failure without traceback
- `test_interrupted_upgrade_retries_same_candidate`
  - failure after several successful replacements
  - no orphan temporary files
  - old manifest remains because it is ordered last
  - real `--check` diagnoses the partial install
  - same-candidate retry succeeds without force
  - manifest replacement occurs last
  - real `--check` passes after retry

## Verification

```text
Focused tests: 2 passed
Installer suite: 69 passed
Full suite: 157 passed
Release verification passed.
Plugin assets match canonical sources.
git diff --check: clean
```

## Generated Assets

Synchronized canonical installer changes to:

- `wise-owl-plugin/scripts/install_wise_owl.py`
- `wise-owl-plugin/skills/wise-owl/scripts/wise_owl_install.py`
