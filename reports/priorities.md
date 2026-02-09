# Prioritized backlog (pokemon-card-agent)
# Top item = #1 for nightly auto-compound.

## This week
- Add compound learnings to RULE.md from daily context
- Set ANTHROPIC_API_KEY or AGENT_CMD for compound review

## Later
- ~~Wire real market API in `market/prices.py`~~ — Done: `market/prices.py` uses `db/` (SQLite). Seed with `scripts/seed_db.py`. Optional: TCGPlayer/eBay for live prices.
- Wire real grading in `grading/estimator.py` (API, rules, or ML)
- Implement price alerts (store + `!alerts` commands)
