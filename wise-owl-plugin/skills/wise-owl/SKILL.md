---
name: wise-owl
description: Use Wise Owl when a Codex task needs a read-only multi-agent second opinion before implementation, before finalizing a diff, after failed debug loops, or for high-risk changes involving security, auth, data, concurrency, MCP/tool execution, migrations, public APIs, CI, or production behavior.
---

# Wise Owl

Wise Owl is a read-only multi-agent review workflow for Codex.

Use this skill when:
- the user explicitly asks for Wise Owl, Owl Council, Prime Owl, rubber-duck review, second opinion, critic review, hardening review, or ensemble review
- the task touches auth, security, secrets, permissions, sandboxing, MCP/tool execution, network behavior, filesystem boundaries, data persistence, migrations, concurrency, state machines, public APIs, CI/CD, deployment, or production reliability
- the implementation spans multiple files or packages
- tests failed twice and the builder may be stuck
- the user asks to finalize, verify, harden, or review a non-trivial diff

Do not use this skill for:
- typo fixes
- README-only edits
- formatting-only changes
- trivial one-line changes
- purely exploratory questions where no code change or implementation decision is being made

## Core Contract

The builder owns all edits.

Wise Owl reviewers are read-only critics. They do not edit files, run mutating commands, or request broad rewrites.

The workflow has four stable public roles and machine IDs:
- `logic_owl` / Logic Owl: correctness, contracts, edge cases, runtime behavior
- `guardian_owl` / Guardian Owl: security, privacy, permissions, secrets, unsafe operations
- `proof_owl` / Proof Owl: tests, validation, CI confidence, false-positive checks
- `prime_owl` / Prime Owl: judge that deduplicates, rejects noise, ranks severity, and produces one builder-facing review packet

Ignore Codex-generated thread names such as Euclid, Galileo, or Descartes. Reviewer packets and Prime Owl `source_ids` must use stable role IDs, for example `logic_owl:L-001`, `guardian_owl:G-001`, or `proof_owl:P-CI-001`.

## Mode Router

Before running Wise Owl, choose exactly one mode. Choose the cheapest mode that covers the risk. Escalate, never downgrade, when the task touches security, privacy, tool execution, data boundaries, auth, secrets, protected data, filesystem/network boundaries, production writes, persistence, migrations, concurrency, public API contracts, or release gates.

No Wise Owl: Use for trivial work when the user did not ask for review: typo, formatting, README-only, pure explanation, tiny copy change, or dependency metadata only.

Wise Owl Lite: Logic Owl, then Prime Owl. Use when the user asks for review, sanity-check, second opinion, or Wise Owl on low-risk work such as docs, prompts, README updates, small plans, small test-only changes, naming cleanup, or low-risk installer/docs polish. Lite is the default for low-risk review/planning requests. Lite must not pretend to be a full review: Selected reviewers are Logic Owl and Prime Owl; Guardian Owl and Proof Owl are `not spawned`. Review status is `complete-lite` only when both Logic Owl and Prime Owl return valid packets.

Wise Owl Standard: Logic Owl + Proof Owl in parallel, then Prime Owl. Use for normal feature work, multi-file non-security changes, API shape changes without sensitive data, test/CI changes, bug fixes with behavior impact, installer behavior, validator behavior, plugin packaging, and config merge logic.

Wise Owl Security: Guardian Owl, then Prime Owl. Use for narrowly security/privacy-only review, secret handling, auth boundary checks, third-party AI data exposure, or protected data review.

Wise Owl Full Council: Logic Owl + Guardian Owl + Proof Owl in parallel, then Prime Owl. Use for auth/authz, secrets/tokens, third-party AI/model provider context, protected student/customer/personal data, MCP/tool execution, filesystem/network boundaries, production writes, cloud/IaC permissions, persistence/migrations, concurrency/state machines, public API contracts, release/CI gates, or explicit "Full Council".

Wise Owl modes are policy-selected through this skill and AGENTS.md guidance, not background automation. Do not add hooks, daemons, runtime automation, a custom orchestrator, or direct model API calls.

## Compact Review Packet

Before spawning reviewers, create a compact Review Packet:
- original user request
- selected Wise Owl mode and reason
- changed files or planned files
- plan/diff summary
- relevant AGENTS.md constraints
- relevant snippets or file references only
- tests/checks run and results
- known assumptions
- exact question for each selected reviewer

Before spawn, the builder must strip raw sensitive values from the Review Packet and replace them with typed placeholders such as `[REDACTED:credential]`. Include only the location and sensitive-data type needed to review the issue.

Review Packet construction must finish before spawning critics.

For Final Review, start from `git diff --stat`, changed-file diffs, checks output, and relevant AGENTS.md constraints. Reviewers should inspect extra files only when necessary and should not rescan the entire repo unless the change affects cross-cutting contracts.

[PARALLEL_CRITIC_PHASE]
Spawn the selected critics directly from the builder. Do not delegate the council to an intermediate subagent when that would consume a reviewer slot. Submit all selected critic spawn requests before waiting so a four-slot runtime can run a Full Council without serializing Proof Owl.

Spawn selected critics concurrently where Codex supports parallel subagents:
- logic_owl
- guardian_owl
- proof_owl

Wait for valid JSON packets from all selected critics. Do not start `prime_owl` until the selected critic phase is complete or partial failure is declared.
[/PARALLEL_CRITIC_PHASE]

[NO_INTERLEAVED_WORK_DURING_OWL_PHASE]
After starting the parallel critic phase, do not perform unrelated repo inspection, extra repo reads, additional tests, ad hoc validation scripts, scope expansion, edits, or mutating commands while waiting for selected critics.

Allowed during the critic phase:
- wait for selected critic packets
- record timeout/failure/malformed-output issues
- perform minimal packet parsing or validation after a critic returns
- start Prime Owl only after all selected critic packets are received or partial failure is declared

If the Review Packet is incomplete after critics are spawned, mark the review partial or invalid, or restart with a corrected Review Packet and report the restart under `[EXECUTION_ISSUES]`.
[/NO_INTERLEAVED_WORK_DURING_OWL_PHASE]

[PRIME_REDUCTION_PHASE]
Send the Review Packet and all valid critic packets to `prime_owl`. Prime Owl must return only the Prime Owl JSON schema.

Validate Prime Owl's packet immediately. If validation fails, send the validation errors and the exact Prime schema back to the same Prime Owl for one correction attempt. Validate the corrected packet; a valid correction is the selected Prime packet and the review may complete. If it still fails, stop and report the review as partial. Do not start a second council or silently repair JSON on Prime Owl's behalf.
[/PRIME_REDUCTION_PHASE]

Lifecycle rules:
- Lite is complete-lite only when both Logic Owl and Prime Owl return valid packets. If Logic Owl fails or returns a malformed packet, the review is partial and Prime Owl must not turn empty input into a completed Lite review.
- Full Council is complete only when Logic Owl, Guardian Owl, Proof Owl, and Prime Owl packets are valid.
- If a critic fails, times out, returns malformed JSON, or cannot be closed cleanly, the run is partial. Prime Owl makes the run partial only when its single correction attempt also fails validation.
- Prime Owl may judge available packets only when the builder labels the result as partial.
- Do not say "all critics returned" unless all selected critics returned valid packets.

Plan Review:
Use before implementation when the plan is risky or ambiguous.

Final Review:
Use after implementation and after relevant tests/checks have run.

Stuck Review:
Use after two failed debug attempts. Ask the owls to focus on the failed command output, likely false assumptions, and missing reproduction steps.

## Reviewer Input Packet

When spawning reviewers, give each reviewer:
- original user request
- current plan or final diff summary
- relevant files changed
- tests/checks run and results
- known constraints from AGENTS.md
- open questions or assumptions
- explicit instruction to stay read-only

## Required Critic Output Schema

Each critic must return:

```json
{
  "role": "logic_owl | guardian_owl | proof_owl",
  "verdict": "pass | concerns | blocked",
  "findings": [
    {
      "id": "short-stable-id",
      "severity": "blocking | non_blocking | suggestion",
      "category": "correctness | security | testability | maintainability | scope | ci",
      "issue": "specific issue",
      "evidence": "file/function/test/command evidence",
      "impact": "why this matters",
      "suggested_fix": "minimal fix",
      "confidence": "high | medium | low"
    }
  ],
  "notes": []
}
```

Critic verdicts are strict: use `pass` only when `findings` is empty, `concerns` when findings exist but none are blocking, and `blocked` when at least one finding is blocking. `evidence` must be one non-empty string, never an array.

If there are no meaningful findings, return exactly:

```json
{
  "role": "<logic_owl | guardian_owl | proof_owl>",
  "verdict": "pass",
  "findings": [],
  "notes": ["No meaningful issues found."]
}
```

Pass/no-finding critic results must still validate against the same schema. `notes` is required even on pass. A raw `pass` packet with missing `notes` is malformed.

Critic `notes` must be a list of non-empty strings. Pass packets must include `notes: ["No meaningful issues found."]`.

## Prime Owl Rules

Prime Owl receives all critic outputs and produces one review packet for the builder.

Prime Owl must:
- stay read-only
- not edit files
- not run commands
- not output markdown or commentary outside the required JSON object
- deduplicate overlapping findings
- merge findings only when they share the same root cause and the merged severity/category accurately applies to every source ID
- not merge a blocking security finding with non-blocking documentation or release-checklist hygiene merely because both mention docs
- account for every critic finding exactly once
- reject findings without evidence
- reject style-only findings unless they affect correctness, safety, or maintainability
- reject speculative findings that require broad redesign
- rank accepted findings by severity
- preserve the smallest safe fix
- include rejected findings with reasons
- avoid inventing unrelated findings or becoming a fourth critic
- only create a new finding when directly implied by critic evidence or obvious from the supplied plan/diff context
- not convert non-blocking findings into blocking findings unless evidence shows the plan violates the user request, a project safety boundary, or a required test/check
- classify concrete security/privacy boundary violations as `blocking` when they involve third-party AI/model providers, secrets, credentials/tokens, protected personal/student/customer data, auth bypass, production writes, sandbox/tool boundary bypass, broad cloud/source-control permissions, data exfiltration, or silent persistence of sensitive data
- classify protected internal/student/customer data sent to a third-party model provider by default as `blocking`, unless evidence is weak or the scope is explicitly non-implementation brainstorming
- classify protected internal/student/customer data persisted in browser localStorage by default as `blocking`, unless evidence is weak or storage is limited to non-sensitive placeholders
- classify sensitive operational API routes without explicit auth/middleware coverage as `blocking`, unless evidence is weak
- keep severity evidence-based; do not make every security suggestion blocking

Prime Owl verdicts are strict:
- `pass`: no accepted findings remain
- `caution`: accepted findings exist, but none are blocking
- `fix_required`: at least one accepted finding is blocking

Every critic finding must be accepted, merged into an accepted finding with its `source_id` preserved, or rejected. No `source_id` may appear twice.

Prime Owl accepted-finding `evidence` must be one non-empty string. Use `required_builder_action`; never use `required_fix`. Use only the categories and rejection reasons shown below.

Prime Owl output:

```json
{
  "verdict": "pass | fix_required | caution",
  "accepted_findings": [
    {
      "source_ids": ["logic_owl:E1"],
      "severity": "blocking | non_blocking | suggestion",
      "category": "correctness | security | testability | maintainability | scope | ci",
      "issue": "specific issue",
      "evidence": "evidence",
      "impact": "impact",
      "required_builder_action": "minimal action"
    }
  ],
  "rejected_findings": [
    {
      "source_ids": ["guardian_owl:S2"],
      "reason": "duplicate | no_evidence | speculative | style_only | out_of_scope | low_value | contradicted_by_evidence",
      "explanation": "short reason"
    }
  ],
  "builder_instructions": [
    "Apply only blocking accepted findings unless the user requested broader cleanup.",
    "After edits, rerun the relevant checks.",
    "Report what was accepted, rejected, and verified."
  ]
}
```

If critics returned no findings, Prime Owl must return exactly:

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

If every critic finding is rejected, the verdict is still `pass`. Prime Owl must keep every rejected `source_id` in `rejected_findings` so source accounting remains complete:

```json
{
  "verdict": "pass",
  "accepted_findings": [],
  "rejected_findings": [
    {
      "source_ids": ["proof_owl:P-001"],
      "reason": "low_value",
      "explanation": "The finding is grounded but does not change builder behavior."
    }
  ],
  "builder_instructions": ["No accepted findings remain."]
}
```

Pass Prime Owl results must still validate against the Prime Owl schema. A pass may contain `rejected_findings` when every critic finding was rejected. Do not return `role`, `findings`, or `notes`; do not omit `accepted_findings`, `rejected_findings`, or `builder_instructions`. A raw `pass` packet missing those required fields is malformed.

## Packet Validation

Validate every returned packet before trusting it. `--mode` also enforces the exact critic role set and rejects duplicate roles:

```bash
python3 scripts/wise_owl_validate_packet.py --type critic --file critic.json
python3 scripts/wise_owl_validate_packet.py --type prime --file prime.json --mode standard --critics logic.json proof.json
```

Mode role sets are `lite` with Logic Owl, `standard` with Logic Owl and Proof Owl, `security` with Guardian Owl, and `full` with all three critics. Without `--critics` or `--mode`, Prime validation is syntax/schema-only and must not be reported as source accounting.

## Builder Rules After Prime Owl

The builder must:
1. Apply all blocking accepted findings.
2. Optionally apply non-blocking findings only when low-risk and clearly useful.
3. Avoid broad rewrites unless Prime Owl explicitly marked them blocking.
4. Rerun relevant checks.
5. Final response must use this shape:

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

If a role was not used in the selected mode, say `not spawned`. Execution issues must mention failed subagent start, timeout, malformed packet, missing critic packet, failed packet validation, failed or unclean agent closure, Prime Owl not run, fallback behavior used, or a recovered Prime correction. A recovered Prime correction may complete; unrecovered validation failures and all other listed reviewer failures require `Review status: partial`.

Empty bracket sections are allowed as `none`.

Report model diversity honestly. Examples: `Model diversity: all selected reviewers configured with gpt-5.5`; `Model diversity: Prime Owl gpt-5.5 high, Logic Owl/Proof Owl gpt-5.4-mini high`; or `Model diversity: unavailable, runtime did not expose actual model names`.

Default TOML policy is configurable: Prime Owl defaults to `gpt-5.5` with high reasoning when available, Guardian Owl defaults to `gpt-5.5` high, and Logic Owl/Proof Owl default to `gpt-5.4-mini` high when available. If those models are unavailable, use the configured model fallback. Do not build external model routing or direct model API calls.

For detailed schemas, severity rules, and examples, read `references/finding-schema.md` and `references/severity-rubric.md` when preparing or validating packets.
