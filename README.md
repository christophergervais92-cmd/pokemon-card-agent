# pokemon-card-agent

Pokemon card agent — Discord bot, grading, market automation.

## Setup

1. Copy `.env.example` to `.env` or `.env.local` and set `DISCORD_BOT_TOKEN`.
2. Install deps: `pip install -r requirements.txt`
3. **Seed the database** (sets, cards, pull rates, chase cards):
   ```bash
   python3 scripts/seed_db.py
   ```
   If the Pokémon TCG API is blocked or slow, use fallback data only:
   ```bash
   SKIP_POKEMON_API=1 python3 scripts/seed_db.py
   ```
   Optional: set `POKEMON_TCG_API_KEY` in `.env` for higher API rate limits.
4. Run: `python3 discord_bot.py`

## HTTP API (TCG Set Database UI)

Run the API from **project root** so the DB is available:

```bash
cd pokemon-card-agent
pip install -r requirements.txt   # includes flask
python3 -m api.app
# or: flask --app api.app run
```

Server: **http://127.0.0.1:5000**

| Endpoint | Description |
|----------|-------------|
| `GET /api/sets` | List sets. Query: `?series=Scarlet%20%26%20Violet` (optional). |
| `GET /api/sets/<set_id>` | Single set (e.g. logo, name, release_date). |
| `GET /api/sets/<set_id>/pull-rates` | Pull rates per pack for the set. |
| `GET /api/sets/<set_id>/chase-cards` | Chase cards. Query: `?rarity=Illustration%20Rare&limit=24` (optional). |
| `GET /api/cards/<card_id>/graded-prices` | PSA, CGC, and Beckett (BGS) graded prices for a card. |
| `GET /api/health` | Health check. |

Example: `curl http://127.0.0.1:5000/api/sets` → `{"data":[...]}`. Point your TCG Set Database frontend at this base URL.

**Search optimization (correct prices and chase cards per set):**

- **Set resolution:** `GET /api/sets/<set_id>`, pull-rates, and chase-cards accept **set id, name, or slug**. The API resolves to a canonical set_id so the same set is always used (e.g. `Destined Rivals`, `destined-rivals`, or `sv10` all return data for that set).
- **Chase cards:** Returned cards are **strictly for that set** (filtered by `set_id`), ordered by price (market then mid). Responses include `set_id` so the UI can confirm.
- **Rarity filter:** `?rarity=Illustration%20Rare`, `Special%20Art`, or `Holo` is normalized to TCG rarity strings (e.g. "Special Art" matches "Special Illustration Rare").
- **Indexes:** A composite index on `(set_id, tcgplayer_market)` keeps "top N chase cards per set" fast.

## Database

- **File:** `pokemon_tcg.db` (SQLite, created on first seed).
- **Tables:** `sets`, `cards`, `pull_rates`, `graded_prices`. Sets include `value_index` (Set Value Index). Graded prices store PSA, CGC, and Beckett (BGS) per card (PriceCharting/eBay style).
- **Fallback set IDs:** `sv8` (Prismatic Evolutions), `sv10` and `destined-rivals` (Destined Rivals), `151` (151 (2023)). Use `destined-rivals` or `sv10` for Destined Rivals; both return the same chase cards and pull rates.
- **API data:** `scripts/seed_db.py` fetches from [Pokémon TCG API v2](https://docs.pokemontcg.io/). If the API returns 403 or times out, the script seeds fallback data for Prismatic Evolutions (Jan 2025) so the agent and any TCG Set Database UI still have data.

## Discord bot commands

| Command | Example | Description |
|--------|---------|-------------|
| `!price <card_id>` | `!price sv8-1` | Current price from DB (TCGPlayer market/mid) |
| `!grade <condition_notes>` | `!grade light edge wear` | Estimated grade from condition (stub: returns placeholder until you wire `grading/estimator.py`) |
| `!alerts` | `!alerts` | Price alerts (stub: not implemented) |

Enable **Message Content Intent** for your bot in the [Discord Developer Portal](https://discord.com/developers/applications) (Bot → Privileged Gateway Intents).

## Compound review / auto-compound

- **In Cursor:** Say "run compound review" or "run auto-compound". Uses Cursor’s AI — no API key needed.
- **Nightly (optional):** If you want the 10:30 PM job to run when Cursor is closed, set `ANTHROPIC_API_KEY` or `AGENT_CMD` in `.env.local`; see RULE.md.

## Backlog

See `reports/priorities.md`. PRDs and tasks in `tasks/`.
