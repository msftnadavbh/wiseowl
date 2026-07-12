# Task 2 Report: Minimize Sensitive Review Context

## Status

Implemented the best-effort privacy instruction contract without changing critic or Prime packet schemas, reviewer roles, or release versioning.

## RED evidence

Command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_wise_owl_install.WiseOwlInstallTests.test_review_evidence_guidance_is_privacy_minimized
```

Result: `FAILED (failures=4)`. The expected assertions failed because the three critic prompts lacked location/type-only sensitive evidence guidance, Prime lacked raw-value suppression guidance, and the canonical builder/docs surfaces lacked the pre-spawn redaction contract.

## GREEN evidence

Focused test: `Ran 1 test ... OK`.

Module suite: `Ran 62 tests ... OK`.

Full suite: `Ran 149 tests ... OK`.

Generated asset check: `Plugin assets match canonical sources.`

Diff hygiene: `git diff --check` passed.

## Files

- Added the prompt-contract test in `tests/test_wise_owl_install.py`.
- Updated canonical critic and Prime prompts in `.codex/agents/`.
- Updated canonical builder guidance in `.agents/skills/wise-owl/SKILL.md`, `AGENTS.md`, and the installer policy.
- Updated `docs/wise-owl.md` to state this is best-effort instruction hygiene, not sanitizer or confidentiality enforcement.
- Synchronized generated copies under `wise-owl-plugin/`.

## Self-review

- The exact `[REDACTED:credential]` placeholder appears on all required canonical surfaces.
- Critics are instructed to cite location and sensitive-data type without raw values; Prime is instructed not to preserve or repeat leaked values.
- No JSON packet fields, roles, or schema wording changed.
- `CHANGELOG.md` remains `v0.2.0 - Unreleased`; plugin version remains `0.2.0`.
- No sanitizer, confidentiality guarantee, runtime hook, or enforcement mechanism was added.

## Concerns

None. The contract is intentionally instruction-only and best effort.
