# Wise Owl

Wise Owl is a Codex-native second-opinion workflow. It gives a builder one disciplined review packet instead of a noisy pile of raw critic output.

```text
Builder creates plan or diff
  -> Owl Council reviews in parallel
     -> Logic Owl checks correctness
     -> Guardian Owl checks security and safety
     -> Proof Owl checks tests and validation
  -> Prime Owl judges critic output
  -> Builder fixes accepted blocking findings
```

The builder remains the only agent that edits files. The owls are read-only reviewers. Prime Owl is a reducer and judge, not a builder.

Generated Codex thread names are ignored. A reviewer named Euclid or Galileo still reports its stable Wise Owl role: `logic_owl`, `guardian_owl`, `proof_owl`, or `prime_owl`.

## Quick Start

Use one of these prompts in Codex:

```text
Use Wise Owl to review this implementation plan before editing.
```

```text
Use Wise Owl Final Review before finalizing. Spawn Logic Owl, Guardian Owl, and Proof Owl, then have Prime Owl judge their output.
```

```text
We hit two failed test loops. Use Wise Owl Stuck Review to find the wrong assumption.
```

```text
Use Wise Owl for this auth change. Apply only Prime Owl blocking findings.
```

## Architecture

- `wise-owl` skill: workflow instructions and output schemas.
- `logic_owl`: read-only correctness reviewer.
- `guardian_owl`: read-only security and safety reviewer.
- `proof_owl`: read-only testing and validation reviewer.
- `prime_owl`: read-only judge that deduplicates, rejects noise, ranks severity, and returns one builder-facing packet.
- `wise_owl_validate_packet.py`: validates critic and Prime Owl JSON packets.
- `wise_owl_install.py`: copies the repo-local skill and agent TOMLs into repo or user Codex locations.

## Mode Router

Wise Owl mode selection is policy-guided through SKILL.md and AGENTS.md, not a deterministic background hook. Choose the cheapest mode that covers the risk. Escalate for security, privacy, tool execution, data boundaries, auth, secrets, protected data, filesystem/network boundaries, production writes, persistence, migrations, concurrency, public API contracts, or release gates.

- No Wise Owl: trivial typo, formatting, README-only, pure explanation, tiny copy change, or dependency metadata only when the user did not ask for review.
- Wise Owl Lite: Logic Owl, then Prime Owl for low-risk review, sanity-check, second-opinion, docs, prompts, README updates, small plans, small test-only changes, naming cleanup, or low-risk installer/docs polish. Lite must not pretend to be full review: Selected reviewers are Logic Owl and Prime Owl; Guardian Owl and Proof Owl are `not spawned`. Review status is `complete-lite` only when both Logic Owl and Prime Owl return valid packets.
- Wise Owl Standard: Logic Owl + Proof Owl in parallel, then Prime Owl for normal implementation, non-security multi-file changes, API shape changes without sensitive data, test/CI changes, bug fixes, installer behavior, validator behavior, plugin packaging, or config merge logic.
- Wise Owl Security: Guardian Owl, then Prime Owl for narrowly security/privacy-only review, secret handling, auth boundary checks, third-party AI data exposure, or protected data review.
- Wise Owl Full Council: Logic Owl + Guardian Owl + Proof Owl in parallel, then Prime Owl for auth/authz, secrets/tokens, third-party AI/model provider context, protected student/customer/personal data, MCP/tool execution, filesystem/network boundaries, production writes, cloud/IaC permissions, persistence/migrations, concurrency/state machines, public API contracts, release/CI gates, or explicit Full Council.

Parallel critic execution is prompt/runtime guidance where Codex supports it, not a local scheduler. Lite runs Logic Owl and then Prime Owl. Standard runs Logic Owl and Proof Owl together; Full Council runs Logic Owl, Guardian Owl, and Proof Owl together. Prime Owl runs only after selected critic packets are received or the run is declared partial.

## Compact Review Packet

Before spawning reviewers, create a compact Review Packet with the user request, selected mode and reason, changed/planned files, plan or diff summary, relevant AGENTS.md constraints, targeted snippets or file references, checks run, known assumptions, and exact reviewer questions.

Before spawn, strip raw sensitive values from the Review Packet and replace them with typed placeholders such as `[REDACTED:credential]`; provide only the location and sensitive-data type needed for review. Critics and Prime Owl should not repeat a raw value if one leaks into their inputs. This is best-effort instruction hygiene, not sanitizer or confidentiality enforcement.

Review Packet construction must finish before spawning critics. After the parallel critic phase starts, the builder must not perform extra repo reads, additional tests, ad hoc validation scripts, scope expansion, edits, or mutating commands while waiting. Allowed work is limited to waiting for packets, recording execution issues, minimal packet parsing/validation after packets return, and starting Prime Owl after all selected packets arrive or partial failure is declared. If context is insufficient after spawn, mark the run partial/invalid or restart explicitly and report that under `[EXECUTION_ISSUES]`.

For Final Review, start from `git diff --stat`, changed-file diffs, test/check output, and relevant AGENTS.md constraints. Do not rescan the entire repo unless the change affects cross-cutting contracts.

## Full Council Flow

1. Spawn `logic_owl`, `guardian_owl`, and `proof_owl` in parallel.
2. Collect one valid JSON critic packet from each reviewer.
3. Validate packet shape and stable source IDs.
4. Send the valid packets to `prime_owl`.
5. Prime Owl accepts, merges, or rejects every critic finding exactly once.
6. Builder applies accepted blocking findings, reruns checks, and reports execution issues.

Full Council is complete only when all three critic packets and the Prime Owl packet are valid.

## Verdict Semantics

Critic verdicts are strict:
- `pass`: use pass only when `findings` is empty.
- `concerns`: findings exist, but none are blocking.
- `blocked`: at least one finding is blocking.

Prime Owl verdicts are strict:
- `pass`: no accepted findings remain.
- `caution`: accepted findings exist, but none are blocking.
- `fix_required`: at least one accepted finding is blocking.

Prime Owl must not return `fix_required` for only `non_blocking` or `suggestion` accepted findings.

Prime Owl may merge findings only when they share the same root cause and the merged severity/category accurately applies to every source ID. Do not merge a blocking security finding with a non-blocking release checklist or documentation-hygiene finding merely because both mention docs. Split them, or reject the weaker finding as duplicate only when the accepted finding fully covers the same root cause without changing its meaning.

Critic and accepted-finding `evidence` must be one non-empty string, not an array. Prime Owl must use `required_builder_action`, never `required_fix`.

## Pass Packets

Pass/no-finding results must still validate against the same JSON schemas.

Critic `notes` must be a list of non-empty strings. Critics must include this exact note on pass:

```json
{
  "role": "logic_owl",
  "verdict": "pass",
  "findings": [],
  "notes": ["No meaningful issues found."]
}
```

A raw critic pass packet with missing, empty, blank, null, or non-string `notes` entries is malformed.

If critics returned no findings, Prime Owl must return this exact pass packet:

```json
{
  "verdict": "pass",
  "accepted_findings": [],
  "rejected_findings": [],
  "builder_instructions": [
    "No Wise Owl accepted findings remain.",
    "Proceed with final response, including checks run and execution issues."
  ]
}
```

If every critic finding is rejected, the verdict is still `pass`; keep each rejected source in `rejected_findings` so accounting remains complete:

```json
{
  "verdict": "pass",
  "accepted_findings": [],
  "rejected_findings": [
    {
      "source_ids": ["proof_owl:P-CI-001"],
      "reason": "low_value",
      "explanation": "The final response already records the exact command and output."
    }
  ],
  "builder_instructions": ["No accepted findings remain."]
}
```

A raw Prime pass packet missing `accepted_findings`, `rejected_findings`, or `builder_instructions` is malformed. A critic-style Prime pass packet with `role`, `findings`, or `notes` is also malformed.

## Security And Privacy Severity

Concrete security/privacy boundary violations default to `blocking` when they involve third-party AI/model providers, secrets, credentials/tokens, protected personal/student/customer data, auth bypass, production writes, sandbox/tool boundary bypass, broad cloud/source-control permissions, data exfiltration, or silent sensitive-data persistence.

Example: if internal student attendance or follow-up notes would be sent to OpenRouter by default, Prime Owl should mark that finding `blocking`. Protected data persisted in browser localStorage by default, unauthenticated API access to sensitive operational data, secrets, credentials, production writes, and sandbox/tool boundary bypasses are also blocking with concrete evidence. The smallest safe builder action is to exclude sensitive fields by default, require explicit opt-in, and add a negative test. Weak evidence, placeholders, or pure brainstorming can stay lower severity. Do not make every security suggestion blocking.

## Repo-Local Install

From this repo:

```bash
python3 .agents/skills/wise-owl/scripts/wise_owl_install.py --scope repo --patch-agents-md
```

Repo scope intentionally targets the current working directory. This lets a standalone Wise Owl checkout install into another repository. Set `WISE_OWL_REPO_ROOT` when the target should not be the current directory.

Preview without writing:

```bash
python3 .agents/skills/wise-owl/scripts/wise_owl_install.py --scope repo --dry-run --patch-agents-md
python3 .agents/skills/wise-owl/scripts/wise_owl_install.py --scope repo --check
```

## User-Local Install

By default, user install targets:
- `~/.agents/skills/wise-owl`
- `~/.codex/agents`
- `~/.codex/config.toml`

```bash
python3 .agents/skills/wise-owl/scripts/wise_owl_install.py --scope user
python3 .agents/skills/wise-owl/scripts/wise_owl_install.py --scope user --check
```

Add `--json` to `--check` for a single privacy-safe automation result. The result includes health, scope, installed and separately bundled candidate versions, update availability, sorted issue codes, allowlisted issue objects, and one of `install`, `upgrade`, `repair`, `review`, or `none`. It never serializes absolute paths, invalid manifest keys, control characters, or raw exceptions. Checks also report manifest scope mismatch and legacy `owl_*` agent files. `--json` without `--check` is an argument error.

Override paths for testing or unusual local Codex layouts:

```bash
WISE_OWL_CODEX_HOME=/path/to/.codex WISE_OWL_USER_SKILLS_HOME=/path/to/.agents python3 .agents/skills/wise-owl/scripts/wise_owl_install.py --scope user
```

Installer migration behavior: if legacy `owl_eyes.toml`, `owl_guard.toml`, or `owl_proof.toml` files exist in the target agent directory, the installer warns. Rerun with `--force` to remove those legacy TOMLs while installing `logic_owl.toml`, `guardian_owl.toml`, `proof_owl.toml`, and `prime_owl.toml`.

Successful installs create a managed install manifest inside the skill directory. Later installs can update unchanged Wise Owl-owned files without `--force`, while local modifications remain protected. Use `--uninstall` to remove unchanged owned files; shared `config.toml` and `AGENTS.md` content is left intact.

## Plugin Skeleton

The plugin skeleton lives in `wise-owl-plugin/`.

It packages:
- `wise-owl-plugin/.codex-plugin/plugin.json`
- `wise-owl-plugin/skills/wise-owl/SKILL.md`
- `wise-owl-plugin/assets/agents/*.toml`
- `wise-owl-plugin/scripts/install_wise_owl.py`

The plugin installer copies custom agent TOMLs into Codex-discovered locations because agent discovery is file-location based.

## Modes

Plan Review: Use before implementation when a plan is risky or ambiguous.

Final Review: Use after implementation and after relevant tests/checks have run.

Stuck Review: Use after two failed debug attempts. Ask reviewers to focus on failed command output, likely false assumptions, and missing reproduction steps.

Example Plan Review:

```text
Use Wise Owl Plan Review for this security-hardening plan. Treat dirty branch baseline ambiguity, a clean dependency-audit snapshot, and the documented security model as supplied context. Return partial status if any critic packet is missing.
```

Example Final Review:

```text
Use Wise Owl Final Review. Critics should verify that the docs/security model was reviewed, the audit/check commands are named, and no blocker remains. Prime Owl should return caution if concerns are real but non-blocking.
```

Example Stuck Review:

```text
Use Wise Owl Stuck Review after these two failed check loops. Focus on the wrong assumption, missing reproduction step, or unclean baseline.
```

## Partial Reviews And Brackets

Report a review as partial when any reviewer fails to start, times out, returns malformed output, cannot be closed cleanly, or fails packet validation.

Prime Owl may judge available packets only if the final answer says the run was partial. Do not say all three critics returned unless all three valid packets were received and parsed.

Every Wise Owl final response must use this bracket:

```text
[WISE_OWL_REVIEW]
Mode:
Mode selection reason:
Review status:
Selected reviewers:
Model diversity:
Prime Owl verdict:

[REVIEW_PACKET]
Task:
Changed files:
Constraints:
Checks run:
Known assumptions:

[CRITIC_RESULTS]
Logic Owl:
Guardian Owl:
Proof Owl:

[ACCEPTED_FINDINGS]
- ...

[REJECTED_FINDINGS]
- ...

[EXECUTION_ISSUES]
- ...

[BUILDER_ACTIONS]
- ...

[/WISE_OWL_REVIEW]
```

Execution issues should name failed subagent start, timeout, malformed packet, missing critic packet, failed packet validation, failed or unclean agent closure, Prime Owl not run, or fallback behavior used.

Complete example:

```text
[WISE_OWL_REVIEW]
Mode: Wise Owl Standard
Mode selection reason: validator behavior changed; no security/privacy boundary touched
Review status: complete
Selected reviewers: Logic Owl, Proof Owl, Prime Owl
Model diversity: Prime Owl gpt-5.5 high; Logic Owl and Proof Owl gpt-5.4-mini high
Prime Owl verdict: caution

[REVIEW_PACKET]
Task: final review of validator patch
Changed files: .agents/skills/wise-owl/scripts/wise_owl_validate_packet.py, tests/test_wise_owl_validate_packet.py
Constraints: stdlib-only, read-only reviewers
Checks run: python3 -m unittest discover -s tests
Known assumptions: no external service calls

[CRITIC_RESULTS]
Logic Owl: complete
Guardian Owl: not spawned
Proof Owl: complete

[ACCEPTED_FINDINGS]
- proof_owl:P-CI-001: Record the exact security check command.

[REJECTED_FINDINGS]
- guardian_owl:G-LOW-001: low_value

[EXECUTION_ISSUES]
- None.

[BUILDER_ACTIONS]
- Record the exact command and rerun tests.

[/WISE_OWL_REVIEW]
```

Partial example:

```text
[WISE_OWL_REVIEW]
Mode: Wise Owl Full Council
Mode selection reason: protected data and API auth boundary touched
Review status: partial
Selected reviewers: Logic Owl, Guardian Owl, Proof Owl, Prime Owl
Model diversity: unavailable, runtime did not expose actual model names
Prime Owl verdict: caution, partial inputs only

[REVIEW_PACKET]
Task: review protected data flow
Changed files: app/routes.py, tests/test_routes.py
Constraints: no protected data leaves trusted boundary by default
Checks run: route tests
Known assumptions: Guardian Owl timed out

[CRITIC_RESULTS]
Logic Owl: complete
Guardian Owl: timed out
Proof Owl: complete

[ACCEPTED_FINDINGS]
- proof_owl:P-CI-001: Record the exact security check command.

[REJECTED_FINDINGS]
- None.

[EXECUTION_ISSUES]
- Guardian Owl timed out; Full Council review is partial.

[BUILDER_ACTIONS]
- Treat review confidence as degraded.

[/WISE_OWL_REVIEW]
```

Lite example:

```text
[WISE_OWL_REVIEW]
Mode: Wise Owl Lite
Mode selection reason: low-risk README review requested
Review status: complete-lite
Selected reviewers: Logic Owl, Prime Owl
Model diversity: Prime Owl gpt-5.5 high; Logic Owl gpt-5.4-mini high
Prime Owl verdict: pass

[REVIEW_PACKET]
Task: sanity-check README copy
Changed files: README.md
Constraints: none
Checks run: none
Known assumptions: docs-only

[CRITIC_RESULTS]
Logic Owl: complete
Guardian Owl: not spawned
Proof Owl: not spawned

[ACCEPTED_FINDINGS]
- none

[REJECTED_FINDINGS]
- none

[EXECUTION_ISSUES]
- none

[BUILDER_ACTIONS]
- none

[/WISE_OWL_REVIEW]
```

## When To Use

Use Wise Owl for non-trivial changes involving:
- auth, authorization, authentication, security, secrets, permissions, or sandboxing
- MCP/tool execution
- filesystem or network boundaries
- persistence, migrations, concurrency, idempotency, or state machines
- public API or CLI behavior
- CI/CD, deployment, or production reliability
- multi-file refactors
- repeated failed debug loops

## When Not To Use

Do not use Wise Owl for typos, README-only edits, formatting-only changes, trivial one-line fixes, simple dependency bumps, or small UI copy edits.

## Customize Models

Default TOML policy is configurable and does not call external model APIs. Prime Owl defaults to `gpt-5.5` with high reasoning when available, Guardian Owl defaults to `gpt-5.5` high, and Logic Owl/Proof Owl default to `gpt-5.4-mini` high when available. If these models are unavailable, use the configured fallback.

Use installer flags:

```bash
python3 .agents/skills/wise-owl/scripts/wise_owl_install.py --scope repo --model gpt-5.4-mini --prime-model gpt-5.5
```

Scripts cannot reliably detect the active interactive Codex model, so final review brackets must report model diversity honestly, for example `all selected reviewers configured with gpt-5.5`, `Prime Owl gpt-5.5 high; critics gpt-5.4-mini high`, or `unavailable`.

## Customize Reviewer Prompts

Edit the TOML files in `.codex/agents/` or the plugin assets in `wise-owl-plugin/assets/agents/`. Keep reviewers read-only and evidence-based.

## Validate Review Packets

```bash
python3 .agents/skills/wise-owl/scripts/wise_owl_validate_packet.py --type critic --file critic.json
python3 .agents/skills/wise-owl/scripts/wise_owl_validate_packet.py --type prime --file prime.json
python3 .agents/skills/wise-owl/scripts/wise_owl_validate_packet.py --type prime --file prime.json --critics critic1.json critic2.json critic3.json
python3 .agents/skills/wise-owl/scripts/wise_owl_validate_packet.py --type prime --file prime.json --require-critics --critics critic1.json critic2.json
python3 .agents/skills/wise-owl/scripts/wise_owl_validate_packet.py --type prime --file prime.json --mode lite --critics logic.json
python3 .agents/skills/wise-owl/scripts/wise_owl_validate_packet.py --type prime --file prime.json --mode standard --critics logic.json proof.json
python3 .agents/skills/wise-owl/scripts/wise_owl_validate_packet.py --type prime --file prime.json --mode security --critics guardian.json
python3 .agents/skills/wise-owl/scripts/wise_owl_validate_packet.py --type prime --file prime.json --mode full --critics logic.json guardian.json proof.json
```

Without `--critics` or `--mode`, Prime validation is syntax/schema-only and prints that source accounting was not checked. With `--critics`, validation checks that every critic finding is accepted, merged, or rejected exactly once, using stable role IDs such as `guardian_owl:G-001`. `--mode` additionally requires the exact selected reviewer set and rejects duplicate roles. Use mode-aware full-accounting validation for release checks.

## First-Use Learnings

- Stable role IDs matter more than generated thread names.
- Prime Owl must reduce critic output, not become another critic.
- A clean check snapshot is useful only when the exact command and baseline caveat are recorded.
- Partial council runs are still useful, but must be labeled partial.
- Lifecycle cleanup failures belong in `Execution issues`, not hidden in prose.

## Design Boundaries

- Wise Owl stays a local Codex skill and custom-agent workflow. It does not call model APIs directly or run background services.
- Parallel execution and available models depend on the active Codex runtime.
- Read-only reviewer instructions complement Codex sandbox and approval policy.
- The plugin installer copies custom agent TOMLs into Codex-discovered locations.
- Lite and Standard optimize for speed; Full Council provides the broadest coverage.
- Partial reviews remain useful only when their reduced confidence is reported explicitly.
