## Wise Owl Review Policy

Use the `wise-owl` skill for non-trivial review, finalization, hardening, second-opinion, or stuck-debug tasks.

Choose the cheapest mode that covers the risk. Escalate, never downgrade, when the task touches security, privacy, tool execution, data boundaries, auth, secrets, protected data, filesystem/network boundaries, production writes, persistence, migrations, concurrency, public API contracts, or release gates.

Modes:
- No Wise Owl: trivial typo, formatting, README-only, pure explanation, tiny copy change, or dependency metadata only when the user did not ask for review.
- Wise Owl Lite: Prime Owl only for low-risk review, sanity-check, second-opinion, docs, prompts, README updates, small plans, small test-only changes, naming cleanup, or low-risk installer/docs polish.
- Wise Owl Standard: Logic Owl + Proof Owl in parallel, then Prime Owl for normal implementation, non-security multi-file changes, API shape changes without sensitive data, test/CI changes, bug fixes, installer behavior, validator behavior, plugin packaging, or config merge logic.
- Wise Owl Security: Guardian Owl, then Prime Owl for narrowly security/privacy-only review, secret handling, auth boundary checks, third-party AI data exposure, or protected data review.
- Wise Owl Full Council: Logic Owl + Guardian Owl + Proof Owl in parallel, then Prime Owl for auth/authz, secrets/tokens, third-party AI/model provider context, protected student/customer/personal data, MCP/tool execution, filesystem/network boundaries, production writes, cloud/IaC permissions, persistence/migrations, concurrency/state machines, public API contracts, release/CI gates, or explicit Full Council.

Lite mode must not pretend to be a full review: Selected reviewers is Prime Owl only; Logic Owl, Guardian Owl, and Proof Owl are `not spawned`; Review status is `complete-lite` when Prime Owl returns a valid packet.

Wise Owl reviewers are read-only. The builder owns all edits. Wise Owl remains a lightweight Codex skill + custom-agent workflow with validator support, fixtures, docs, and installer behavior; do not add runtime automation, background hooks, daemons, custom orchestrators, direct model API calls, or scheduling tests.

Every Wise Owl final response must use the `[WISE_OWL_REVIEW]` bracket, include mode, mode selection reason, selected reviewers, model diversity, Prime Owl verdict, accepted findings, rejected findings, execution issues, and builder actions.

Before spawning critics, finish the compact Review Packet. After `[PARALLEL_CRITIC_PHASE]` starts, do not perform unrelated repo inspection, extra repo reads, additional tests, ad hoc validation scripts, scope expansion, edits, or mutating commands while waiting for selected critics. If the packet is incomplete after spawn, mark the review partial/invalid or restart explicitly and report it under `[EXECUTION_ISSUES]`.

Report model diversity honestly, for example `all selected reviewers configured with gpt-5.5`, `Prime Owl gpt-5.5 high; Logic Owl/Proof Owl gpt-5.4-mini high`, or `unavailable`.

If any selected reviewer fails, times out, returns malformed JSON, fails packet validation, or cannot be closed cleanly, set `Review status: partial`. Do not claim Prime Owl adjudication if Prime Owl was not run.

Empty bracket sections may be `none`.
