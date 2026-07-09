# Wise Owl Finding Schema

Wise Owl reviewers must return compact JSON packets with concrete evidence. The schema is intentionally small so Prime Owl can judge output without parsing prose.

Use stable role IDs only. Ignore generated thread names such as Euclid, Galileo, Descartes, or Bacon. A finding from a thread named Euclid that is acting as Logic Owl is still `logic_owl:E1`.

## Critic Packet

Allowed roles:
- `logic_owl`
- `guardian_owl`
- `proof_owl`

Allowed verdicts:
- `pass`
- `concerns`
- `blocked`

Allowed severities:
- `blocking`
- `non_blocking`
- `suggestion`

Allowed categories:
- `correctness`
- `security`
- `testability`
- `maintainability`
- `scope`
- `ci`

Required critic fields:
- `role`
- `verdict`
- `findings`
- `notes`

`notes` must be a list of non-empty strings. Pass packets must include `notes: ["No meaningful issues found."]`.

Required fields for each critic finding:
- `id`
- `severity`
- `category`
- `issue`
- `evidence`
- `impact`
- `suggested_fix`
- `confidence`

`evidence` must be a non-empty string citing a file path, function, test, command output, diff hunk, or stated constraint.

Finding IDs must be unique within each critic packet.

Valid critic packet:

```json
{
  "role": "logic_owl",
  "verdict": "concerns",
  "findings": [
    {
      "id": "E1",
      "severity": "blocking",
      "category": "correctness",
      "issue": "The retry loop reports success after all retries fail.",
      "evidence": "src/worker.py:run_job catches Exception after the final retry and falls through to return True.",
      "impact": "Failed jobs can be reported as successful.",
      "suggested_fix": "Re-raise the last exception after retries are exhausted.",
      "confidence": "high"
    }
  ],
  "notes": []
}
```

Valid critic pass packet:

```json
{
  "role": "logic_owl",
  "verdict": "pass",
  "findings": [],
  "notes": ["No meaningful issues found."]
}
```

Pass/no-finding critic results must still validate against the critic schema. `notes` is required even when `findings` is empty. A raw pass packet with missing, empty, blank, null, or non-string `notes` entries is a malformed critic packet.

Invalid critic packet:

```json
{
  "role": "logic_owl",
  "verdict": "blocked",
  "findings": [
    {
      "id": "E2",
      "severity": "blocking",
      "category": "maintainability",
      "issue": "This code could be cleaner.",
      "evidence": "",
      "impact": "Code quality.",
      "suggested_fix": "Refactor it.",
      "confidence": "low"
    }
  ],
  "notes": []
}
```

## Prime Owl Packet

Allowed verdicts:
- `pass`
- `fix_required`
- `caution`

Verdict semantics:
- `pass`: no accepted findings remain
- `caution`: accepted findings exist, but none are blocking
- `fix_required`: at least one accepted finding has severity `blocking`

Required Prime Owl fields:
- `verdict`
- `accepted_findings`
- `rejected_findings`
- `builder_instructions`

Required fields for each accepted finding:
- `source_ids`
- `severity`
- `category`
- `issue`
- `evidence`
- `impact`
- `required_builder_action`

Required fields for each rejected finding:
- `source_ids`
- `reason`
- `explanation`

Allowed rejection reasons:
- `duplicate`
- `no_evidence`
- `speculative`
- `style_only`
- `out_of_scope`
- `low_value`
- `contradicted_by_evidence`

Prime Owl must account for every critic finding exactly once:
- accepted directly in `accepted_findings.source_ids`
- merged into an accepted finding with its original `source_id` preserved
- rejected in `rejected_findings.source_ids`

`source_ids` must be machine role/finding IDs such as `logic_owl:L-001`, `guardian_owl:G-001`, or `proof_owl:P-CI-001`. Do not use display names, generated thread names, or legacy IDs such as `owl_guard:OG1`. A `source_id` must not appear twice across accepted and rejected findings.

Prime Owl may merge findings only when they share the same root cause and the merged severity/category accurately applies to every `source_id`. Do not merge a blocking security finding with a non-blocking documentation or release-checklist hygiene finding merely because both mention docs.

Valid Prime Owl packet:

```json
{
  "verdict": "fix_required",
  "accepted_findings": [
    {
      "source_ids": ["logic_owl:E1"],
      "severity": "blocking",
      "category": "correctness",
      "issue": "The retry loop reports success after all retries fail.",
      "evidence": "src/worker.py:run_job catches Exception after the final retry and falls through to return True.",
      "impact": "Failed jobs can be reported as successful.",
      "required_builder_action": "Re-raise the last exception after retries are exhausted and add a regression test."
    }
  ],
  "rejected_findings": [
    {
      "source_ids": ["guardian_owl:S2"],
      "reason": "no_evidence",
      "explanation": "The finding did not cite a file, command, diff, or stated constraint."
    }
  ],
  "builder_instructions": [
    "Apply all blocking accepted findings.",
    "Rerun relevant checks after edits."
  ]
}
```

Valid Prime Owl pass packet:

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

Pass/no-finding Prime Owl results must still validate against the Prime Owl schema. A raw pass packet with missing `accepted_findings`, `rejected_findings`, or `builder_instructions` is malformed. A critic-style Prime pass packet with `role`, `findings`, or `notes` is also malformed.

Invalid Prime Owl packet:

```json
{
  "verdict": "fix_required",
  "accepted_findings": [
    {
      "source_ids": ["proof_owl:T1"],
      "severity": "blocking",
      "category": "testability",
      "issue": "Tests seem weak.",
      "evidence": "",
      "impact": "Confidence is lower."
    }
  ],
  "rejected_findings": []
}
```

## Prime Owl Reduction Examples

Good reduction:

```json
{
  "verdict": "caution",
  "accepted_findings": [
    {
      "source_ids": ["logic_owl:E1", "proof_owl:T1"],
      "severity": "non_blocking",
      "category": "testability",
      "issue": "The plan depends on a clean security snapshot but does not name the exact commands that produced it.",
      "evidence": "logic_owl:E1 cites a dirty baseline concern; proof_owl:T1 cites an npm audit clean claim without command output.",
      "impact": "The builder could report confidence without a repeatable proof trail.",
      "required_builder_action": "Record the exact checks and dirty-baseline caveat before finalizing."
    }
  ],
  "rejected_findings": [
    {
      "source_ids": ["guardian_owl:S1"],
      "reason": "no_evidence",
      "explanation": "The security concern did not cite a file, command, or policy boundary."
    }
  ],
  "builder_instructions": ["Revise the plan around the accepted non-blocking proof concern."]
}
```

Bad overreach:

```json
{
  "verdict": "fix_required",
  "accepted_findings": [
    {
      "source_ids": ["Euclid:E1"],
      "severity": "blocking",
      "category": "security",
      "issue": "Rewrite the deployment system.",
      "evidence": "General security best practice.",
      "impact": "Security may improve.",
      "required_builder_action": "Redesign deployment before continuing."
    }
  ],
  "rejected_findings": [],
  "builder_instructions": ["Perform a broad rewrite."]
}
```

Problems: generated thread name instead of stable role ID, ungrounded evidence, severity escalation, broad rewrite, and missing accounting for the original critic IDs.

Bad over-merge:

```json
{
  "verdict": "fix_required",
  "accepted_findings": [
    {
      "source_ids": ["guardian_owl:G-001", "proof_owl:P-003"],
      "severity": "blocking",
      "category": "security",
      "issue": "Installation docs need release cleanup.",
      "evidence": "guardian_owl:G-001 is about unsafe --force guidance; proof_owl:P-003 is about stale release checklist text.",
      "impact": "The merged severity/category misrepresents the release checklist finding.",
      "required_builder_action": "Rewrite all docs as a blocking security fix."
    }
  ],
  "rejected_findings": [],
  "builder_instructions": ["Do not merge unrelated severity/action domains this way."]
}
```

Correct split:

```json
{
  "verdict": "fix_required",
  "accepted_findings": [
    {
      "source_ids": ["guardian_owl:G-001"],
      "severity": "blocking",
      "category": "security",
      "issue": "User-local install docs present --force as the default path.",
      "evidence": "guardian_owl:G-001 cites docs/packaging.md user-local install guidance.",
      "impact": "Users may overwrite or migrate files without reviewing targets.",
      "required_builder_action": "Document dry-run and non-force install first; reserve --force for reviewed migration."
    },
    {
      "source_ids": ["proof_owl:P-003"],
      "severity": "non_blocking",
      "category": "maintainability",
      "issue": "Release checklist text is stale.",
      "evidence": "proof_owl:P-003 cites license checklist wording that no longer matches the MIT license decision.",
      "impact": "External users may see contradictory release guidance.",
      "required_builder_action": "Update the checklist wording."
    }
  ],
  "rejected_findings": [],
  "builder_instructions": ["Fix the blocking installer-doc guidance first, then clean the stale checklist."]
}
```

Security/privacy escalation example:

Bad reduction:

```json
{
  "verdict": "caution",
  "accepted_findings": [
    {
      "source_ids": ["guardian_owl:G-PRIV-001"],
      "severity": "non_blocking",
      "category": "security",
      "issue": "Student attendance and follow-up notes are sent to OpenRouter by default.",
      "evidence": "The plan sends attendance and follow-up notes to a third-party model provider without exclusion or opt-in.",
      "impact": "Protected internal student data could leave the trusted boundary.",
      "required_builder_action": "Consider filtering sensitive fields."
    }
  ],
  "rejected_findings": [],
  "builder_instructions": ["Maybe improve privacy later."]
}
```

Good reduction:

```json
{
  "verdict": "fix_required",
  "accepted_findings": [
    {
      "source_ids": ["guardian_owl:G-PRIV-001"],
      "severity": "blocking",
      "category": "security",
      "issue": "Student attendance and follow-up notes are sent to OpenRouter by default.",
      "evidence": "The plan sends attendance and follow-up notes to a third-party model provider without exclusion or opt-in.",
      "impact": "Protected internal student data could leave the trusted boundary.",
      "required_builder_action": "Exclude sensitive fields by default, require explicit opt-in, and add a negative test."
    }
  ],
  "rejected_findings": [],
  "builder_instructions": ["Apply the blocking privacy boundary fix before finalizing."]
}
```

## Validator With Critics

Validate Prime Owl accounting against source critic packets:

```bash
python3 .agents/skills/wise-owl/scripts/wise_owl_validate_packet.py --type prime --file prime.json --critics critic1.json critic2.json critic3.json
```

When `--critics` is provided, validation fails on missing source findings, unknown source IDs, duplicate source IDs, malformed critic packets, and duplicate critic finding IDs.
