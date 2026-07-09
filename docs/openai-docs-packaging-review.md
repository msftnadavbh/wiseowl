# OpenAI Docs Packaging Review

Date of review: 2026-07-09

## Docs Consulted

- https://developers.openai.com/codex/skills
- https://developers.openai.com/codex/plugins
- https://developers.openai.com/codex/plugins/build
- https://developers.openai.com/codex/subagents
- https://developers.openai.com/codex/concepts/subagents
- https://developers.openai.com/codex/guides/agents-md
- https://developers.openai.com/codex/concepts/customization
- https://developers.openai.com/codex/learn/best-practices
- https://developers.openai.com/codex/models
- https://developers.openai.com/codex/pricing

## Relevant Packaging Facts

- Skills are reusable workflow instructions. A skill is a directory containing `SKILL.md`; `scripts/`, `references/`, and `assets/` are allowed. `SKILL.md` must include `name` and `description`.
- Repo-local skills are discovered from `.agents/skills`; user-local skills are documented under `$HOME/.agents/skills`.
- Plugins are the installable distribution unit for reusable skills. A plugin must include `.codex-plugin/plugin.json`; `skills/`, `hooks/`, `.app.json`, `.mcp.json`, and `assets/` live at plugin root, not inside `.codex-plugin/`.
- Plugin manifests use top-level metadata such as `name`, `version`, `description`, `skills`, and `interface`. `interface` controls install-surface metadata such as display name, descriptions, capabilities, default prompts, and visual assets.
- Custom agents are TOML files under `.codex/agents/` for project scope or `~/.codex/agents/` for personal scope. Required fields are `name`, `description`, and `developer_instructions`; optional supported config keys include `nickname_candidates`, `model`, `model_reasoning_effort`, and `sandbox_mode`.
- `[agents] max_threads` and `max_depth` are documented subagent settings.
- Current Codex model docs list `gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini`, and `gpt-5.3-codex-spark`; `gpt-5.4-mini` is specifically described as suitable for subagents.
- Official subagent examples use `model_reasoning_effort = "high"` or `"medium"`; `xhigh` was not shown in the current custom-agent docs.
- AGENTS.md is documented as project guidance loaded before work. Repo-level AGENTS.md policy guidance is appropriate; workflow-specific details still belong primarily in `SKILL.md`.

## Wise Owl Compliance Status

- Skill layout matches docs: `.agents/skills/wise-owl/SKILL.md` with `references/` and `scripts/`.
- User-local installer now uses the documented `$HOME/.agents/skills/wise-owl` skill path while keeping custom agents in `~/.codex/agents`.
- Plugin skeleton matches documented shape: `.codex-plugin/plugin.json` at plugin root plus `skills/` and `assets/` outside `.codex-plugin/`.
- Plugin skill points to `./skills/`, matching manifest path rules.
- Custom agents use documented locations and fields.
- The plugin docs correctly keep the custom-agent TOML copy installer because official plugin docs do not document automatic custom-agent registration from plugin assets.
- Release archive and manifest include the launch-relevant files and exclude generated/cache/temp files.

## Gaps Found

- Prime Owl used `model_reasoning_effort = "xhigh"`. Current official custom-agent examples document `high` and `medium`, but not `xhigh`.

## Patches Made

- Changed Prime Owl `model_reasoning_effort` from `xhigh` to `high` in repo-local and plugin TOMLs.
- Updated model-diversity wording in SKILL, AGENTS policy text, docs, and installer policy text from `gpt-5.5 xhigh` to `gpt-5.5 high`.
- Added a regression test that all Wise Owl agent `model_reasoning_effort` values are documented-safe.
- Changed user-local skill install docs and installer targets to `$HOME/.agents/skills/wise-owl`.

## Unresolved Uncertainties

- The plugin docs do not list a first-class custom-agent packaging field. Keep the installer workaround unless future Codex plugin docs add direct custom-agent registration.
- Public plugin self-serve publishing is documented as coming soon, so Wise Owl is prepared as a repo/plugin skeleton rather than published.
