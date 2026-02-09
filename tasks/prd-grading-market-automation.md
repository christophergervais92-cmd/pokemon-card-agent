# PRD: Grading / market automation

**Backlog (later).** Automate grading estimates and market data for Pokemon cards.

## Goal

- **Grading:** Integrate or stub grading logic (e.g. condition assessment, estimated grade).
- **Market:** Integrate or stub market data (prices, trends) for cards.
- Expose via Discord bot or standalone scripts.

## Tasks

- [x] Identify grading source (API, manual rules, ML) and define interface. (Stub in `grading/estimator.py`.)
- [x] Identify market data source (e.g. TCGPlayer, eBay, internal DB) and define interface. (Stub in `market/prices.py`.)
- [x] Add modules (e.g. `grading/`, `market/`) and wire to `discord_bot.py` or CLI. (Modules added; wire in bot when commands are implemented.)
- [x] Document in RULE.md and README. (RULE.md updated; README has run instructions.)

## Notes

- Can start with stubs and fill in real APIs later. RULE.md should record decisions (rate limits, auth, etc.).
