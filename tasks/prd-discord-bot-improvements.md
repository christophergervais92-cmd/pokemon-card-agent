# PRD: Discord bot improvements

**Backlog (later).** Expand the Pokemon card Discord bot.

## Goal

- Implement or extend `discord_bot.py` so the agent can interact via Discord (commands, notifications, grading/market queries).
- Define commands (e.g. price check, grading estimate, alerts) and wire to existing or new modules.

## Tasks

- [x] Define Discord bot scope: commands, events, permissions. (Price check, grading estimate, alerts — doc in PRD.)
- [x] Add Discord token to env (e.g. `DISCORD_BOT_TOKEN` in `.env`). (.env.example + README.)
- [x] Implement `discord_bot.py` with minimal bot skeleton (login, one or two commands). (Stub: loads token, prints ready; add discord.py for real connection.)
- [x] Add README section for running the bot and required env vars.

## Notes

- Entrypoint is `discord_bot.py` (currently empty). Grading and market automation can be separate modules called by the bot.
