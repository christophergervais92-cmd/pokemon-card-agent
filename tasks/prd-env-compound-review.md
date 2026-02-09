# PRD: Set ANTHROPIC_API_KEY or AGENT_CMD for compound review

**Backlog #2 (this week).** Enables nightly compound review without Cursor open.

## Goal

- **Option A:** Add `ANTHROPIC_API_KEY` to `.env` or `.env.local` (and `pip install anthropic`) so `scripts/compound_review.py` can run at 10:30 PM.
- **Option B:** Set `AGENT_CMD` (e.g. `amp execute` or Claude CLI) in the launchd plist or `.env.local` so the nightly script uses that instead of Python.

## Tasks

- [x] Create `.env.example` with `ANTHROPIC_API_KEY=` (optional) and document in README or RULE.md.
- [x] If using Python path: ensure `anthropic` is in requirements or document `pip install anthropic`. (Documented in RULE.md: `pip install anthropic`.)
- [ ] Load env in launchd: add `EnvironmentVariables` with `ANTHROPIC_API_KEY` from keychain or a secure env file, or run script via `env $(cat .env.local) ./scripts/daily-compound-review.sh`.

## Notes

- Nightly job runs at 10:30 PM (launchd). Without API key or AGENT_CMD, compound review only runs on-demand in Cursor ("run compound review").
