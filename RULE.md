# pokemon-card-agent — agent rules

Living knowledge base for this project. Updated by compound review (on-demand in Cursor or nightly script).

## Project context

- **Purpose:** Pokemon card agent — Discord bot, grading, market automation.
- **Entrypoint:** `discord_bot.py` — real Discord bot (discord.py). Commands: `!price <card_id>`, `!grade <condition_notes>`, `!alerts` (stub). Dependencies: `pip install -r requirements.txt`.
- **Modules:** `grading/` (condition, grade estimate — stub), `market/` (prices, sets, pull rates, chase cards — backed by `db/`), `db/` (SQLite: sets, cards, pull_rates). Run `python3 scripts/seed_db.py` (or `SKIP_POKEMON_API=1 python3 scripts/seed_db.py`) to populate DB.
- **Backlog:** See `reports/priorities.md`; top item is #1 for auto-compound.

## Compound review (learnings)

- **Daily context:** Paste a short summary of the day’s work in `logs/daily-context.md`. Compound review (trigger: "run compound review" in Cursor, or nightly script) merges it into this file / `.cursor/rules/`.
- **Instruction files Cursor reads:** This file (`RULE.md`) and `.cursor/rules/`. Keep patterns, gotchas, and context here so the agent gets smarter over time.

## Conventions

- Use `scripts/daily-compound-review.sh` and `scripts/compound/auto-compound.sh` for nightly runs (launchd), or trigger "run compound review" / "run auto-compound" in Cursor for on-demand agents.
- Prioritized work lives in `reports/priorities.md`; tasks/PRDs in `tasks/`.
- **Vendored Codex skills:** This repo includes Codex desktop app skills under `codex_skills/` for use in Cursor (index: `.cursor/rules/codex-skills-index.mdc`). Prefer repo-local paths; see `.cursor/rules/codex-skills-paths.mdc`.

## Compound review: Cursor vs nightly

- **In Cursor (on-demand):** Say "run compound review" or "run auto-compound" in chat. Cursor’s AI does the work. **No Anthropic key needed** — it runs locally on Cursor’s models.
- **Nightly (launchd 10:30 PM):** Scripts run when Cursor isn’t open, so they can’t use Cursor. They need either **ANTHROPIC_API_KEY** (for `compound_review.py`) or **AGENT_CMD** (e.g. Amp/Claude CLI). Only set these if you want the scheduled job to run without Cursor; otherwise use Cursor on-demand only.
