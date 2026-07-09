# Wise Owl CLI Demo Transcript

This file records the schema-valid source excerpt used for `assets/wise-owl-cli-demo.gif`.

The walkthrough is based on a Codex CLI review in a disposable demo repo. Non-Wise-Owl setup noise was omitted so the animation can focus on the review flow. Wise Owl remains a Codex skill + custom-agent workflow, not a daemon, hosted service, runtime framework, custom orchestrator, or direct model API client.

## Command Shape

```bash
codex -s read-only -a never exec -C <disposable-demo-repo> --color never --ephemeral \
  "Use Wise Owl Standard to review this small packaging docs diff before finalizing. Stay read-only."
```

## Logic Owl

```json
{
  "role": "logic_owl",
  "verdict": "concerns",
  "findings": [
    {
      "id": "L-001",
      "severity": "non_blocking",
      "category": "correctness",
      "issue": "The README references a workflow image that is not present in the demo checkout.",
      "evidence": "README.md references assets/wise-owl-workflow.png, while rg --files shows no matching file.",
      "impact": "The rendered README would show a broken image.",
      "suggested_fix": "Add the referenced image or remove the reference before finalizing.",
      "confidence": "high"
    }
  ],
  "notes": []
}
```

## Proof Owl

```json
{
  "role": "proof_owl",
  "verdict": "pass",
  "findings": [],
  "notes": ["No meaningful issues found."]
}
```

## Prime Owl

```json
{
  "verdict": "caution",
  "accepted_findings": [
    {
      "source_ids": ["logic_owl:L-001"],
      "severity": "non_blocking",
      "category": "correctness",
      "issue": "The README references a missing workflow image.",
      "evidence": "logic_owl:L-001 cites the README path and the rg --files result from the disposable checkout.",
      "impact": "The public README would display a broken image.",
      "required_builder_action": "Add the workflow image or remove its README reference before finalizing."
    }
  ],
  "rejected_findings": [],
  "builder_instructions": ["Resolve the accepted image reference before finalizing the docs change."]
}
```

## CLI Summary

```text
Read-only Wise Owl Standard review complete.

selected_reviewers: logic_owl, proof_owl, prime_owl
prime_owl_verdict: caution
accepted_findings: 1 non_blocking
packet_validation: critic and Prime packets valid
recommended_action: add the referenced workflow image or remove the README reference
checks: git status, git diff, rg --files, README inspection
tests: not run; docs-only diff
```

The real run used a read-only sandbox and did not mutate the Wise Owl repository. Parallel reviewer execution depended on Codex runtime support.
