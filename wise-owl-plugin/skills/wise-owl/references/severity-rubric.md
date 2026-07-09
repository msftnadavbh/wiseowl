# Wise Owl Severity Rubric

## Severities

`blocking`: The builder must fix this before final response. Use for likely bugs, broken contracts, failed tests, data loss, exploitable security regressions, unsafe execution, missing proof for risky changes, or direct user requirement violations.

`non_blocking`: A concrete issue worth fixing soon, but not required for the requested task to be safe and complete.

`suggestion`: A useful optional improvement with low risk and no immediate correctness, safety, or validation impact.

Prime Owl must not upgrade `non_blocking` or `suggestion` critic findings to `blocking` unless the supplied evidence shows a current violation of the user request, project safety boundary, or required test/check.

Prime Owl must not merge unrelated severity/action domains. A blocking security finding about unsafe install guidance and a non-blocking maintainability finding about stale release checklist text should remain separate unless they share the same root cause and one accepted finding accurately covers both.

Concrete security/privacy boundary violations default to `blocking` only when evidence shows sensitive data crosses or persists across a trust boundary by default. Examples include third-party AI/model provider context, browser localStorage, unauthenticated API access to sensitive operational data, secrets, credentials/tokens, protected personal/student/customer data, auth bypass, production writes, sandbox/tool boundary bypass, broad cloud/source-control permissions, data exfiltration, or silent sensitive-data persistence.

If a plan or diff sends protected internal/student/customer data to a third-party model provider by default, classify it as `blocking` unless evidence is weak or the task is explicitly non-implementation brainstorming. The smallest safe action is usually to exclude sensitive fields by default, require explicit opt-in, and add a negative test.

If a plan or diff persists protected internal/student/customer data in browser localStorage by default, classify it as `blocking` unless evidence is weak or storage is explicitly limited to non-sensitive placeholders. If API routes may expose sensitive operational data without explicit auth/middleware coverage, classify it as `blocking` unless evidence is weak.

Do not make every security suggestion blocking. Concrete evidence is required.

## Rejection Reasons

`duplicate`: Another accepted finding covers the same root cause.

`no_evidence`: The critic did not cite a concrete file, function, test, command, diff hunk, or stated constraint.

`speculative`: The finding depends on a guessed future failure or broad redesign rather than visible evidence.

`style_only`: The finding is only stylistic and does not affect correctness, safety, maintainability, or scope.

`out_of_scope`: The finding is real but unrelated to the user's requested task.

`low_value`: The finding is technically true but not useful enough to change builder behavior.

`contradicted_by_evidence`: The visible code, tests, docs, or command output shows the finding is wrong.

## High-Signal Finding

```json
{
  "id": "E1",
  "severity": "blocking",
  "category": "correctness",
  "issue": "The new retry loop swallows the final exception and returns success.",
  "evidence": "src/worker.py:run_job catches Exception and exits the loop without re-raising; tests/test_worker.py only asserts no exception.",
  "impact": "Failed jobs can be reported as successful.",
  "suggested_fix": "Re-raise the last exception after retries are exhausted and add a regression test.",
  "confidence": "high"
}
```

## Noisy Finding

```json
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
```

Reject noisy findings unless the critic grounds them in evidence and explains a concrete impact.
