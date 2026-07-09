# Wise Owl CLI Demo Transcript

This file records the source excerpt used for `assets/wise-owl-cli-demo.gif`.

The GIF is an animated walkthrough based on a real Codex CLI run in a disposable demo repo. Non-Wise-Owl local setup warnings were omitted from the animation so the README can focus on the workflow. Wise Owl remains a Codex skill + custom-agent workflow, not a daemon, hosted service, runtime framework, custom orchestrator, or direct model API client.

## Command Shape

```bash
codex -s read-only -a never exec -C <disposable-demo-repo> --color never --ephemeral \
  "Use Wise Owl Standard to review this small packaging docs diff before finalizing. Stay read-only. Be concise. Return a short CLI-friendly review summary with selected reviewers and Prime Owl verdict."
```

## Clean Transcript Excerpt

```text
Read-only Wise Owl Standard review complete.

selected_reviewers: logic_owl, proof_owl, prime_owl
prime_owl_verdict: caution
accepted_findings: 1 non_blocking
finding: README now references wise-owl-workflow.png / plugin manifest screenshots, but this checkout only has README.md and codex-output.txt; no PNG or manifest evidence is present.
recommended_action: remove/narrow the note, or add/provide the missing PNG/manifest proof before finalizing.
checks: git status, git diff, rg --files, README inspection
tests: not run; docs-only diff
worktree: M README.md, ?? codex-output.txt
execution_note: critic packets were schema-malformed, and one accidental early Prime Owl result was ignored.
```

## Replay Notes

- The GIF presents the flow as a short visual summary.
- The real run used a read-only sandbox and did not mutate the Wise Owl repo.
- Local setup warnings unrelated to Wise Owl were omitted from the README animation.
- The source run surfaced execution issues, which is useful: Wise Owl should report malformed or partial review packets instead of hiding them.
