"""
Pokemon card Discord bot — entrypoint.
Run: python discord_bot.py (requires DISCORD_BOT_TOKEN in .env or .env.local)
Commands: !price <card_id>, !grade <condition_notes>, !alerts, !search, !collection
"""
import os
from pathlib import Path
import asyncio

# Load .env.local or .env if present
env_path = Path(__file__).resolve().parent / ".env.local"
if not env_path.exists():
    env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
if not TOKEN:
    print("Set DISCORD_BOT_TOKEN in .env or .env.local. See .env.example.")
    raise SystemExit(1)

import discord
from discord.ext import commands, tasks

from grading.estimator import estimate_grade, assess_condition
from market.prices import get_price, get_trends
from search.cards import search_cards, get_card_by_id
from alerts.tracker import create_alert, get_user_alerts, delete_alert, check_alerts
from collection.manager import get_portfolio_summary, add_to_collection

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Alert monitor settings
ALERT_CHECK_INTERVAL_SECONDS = max(30, int(os.environ.get("ALERT_CHECK_INTERVAL_SECONDS", "300")))
ALERTS_USE_LIVE_PRICE = (os.environ.get("ALERTS_USE_LIVE_PRICE", "0").strip().lower() in ("1", "true", "yes"))


async def _send_dm(user_id: str, message: str) -> None:
    """Best-effort DM; ignores if user blocks DMs or cannot be fetched."""
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return

    try:
        user = bot.get_user(uid) or await bot.fetch_user(uid)
        if user:
            await user.send(message)
    except Exception as e:
        # Avoid crashing the loop on DM failures.
        print(f"DM failed for user {user_id}: {e}")


@tasks.loop(seconds=ALERT_CHECK_INTERVAL_SECONDS)
async def alert_monitor_loop() -> None:
    """Periodic alert checks that DM users when thresholds are crossed."""
    triggered = await asyncio.to_thread(check_alerts, None, ALERTS_USE_LIVE_PRICE)
    for t in triggered:
        msg = t.get("message") or ""
        if msg:
            await _send_dm(str(t.get("user_id") or ""), msg)


@alert_monitor_loop.error
async def _alert_monitor_error(exc: Exception) -> None:
    print(f"Alert monitor loop error: {exc}")


@bot.event
async def on_ready() -> None:
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Commands: !price <card_id>, !grade <condition_notes>, !search <query>, !alert, !portfolio")
    if not alert_monitor_loop.is_running():
        alert_monitor_loop.start()


@bot.command(name="price")
async def price_cmd(ctx: commands.Context, *, card_id: str) -> None:
    """Check price for a card (e.g. !price sv8-1)."""
    card_id = card_id.strip()
    if not card_id:
        await ctx.send("Usage: `!price <card_id>` (e.g. sv8-1 for Charizard from Prismatic Evolutions)")
        return
    price = get_price(card_id)
    card = get_card_by_id(card_id)
    
    if card:
        name = card.get("name", card_id)
        set_name = card.get("set_name", "Unknown set")
        rarity = card.get("rarity", "")
        if price is not None:
            await ctx.send(f"**{name}** ({set_name}) - {rarity}\n**Price:** ${price:.2f}\nCard ID: `{card_id}`")
        else:
            await ctx.send(f"**{name}** ({set_name}) - No price data available\nCard ID: `{card_id}`")
    else:
        if price is not None:
            await ctx.send(f"**{card_id}**: ${price:.2f}")
        else:
            await ctx.send(f"**{card_id}**: Card not found or no price data.")


@bot.command(name="grade")
async def grade_cmd(ctx: commands.Context, *, condition_notes: str) -> None:
    """Get estimated grade from condition notes (e.g. !grade light edge wear)."""
    condition_notes = condition_notes.strip()
    if not condition_notes:
        await ctx.send("Usage: `!grade <condition_notes>` (e.g. 'light edge wear, NM')")
        return
    result = assess_condition(condition_notes)
    
    response = f"**Condition:** {condition_notes}\n"
    response += f"**Estimated Grade:** PSA {result['grade']} ({result['label']})\n"
    response += f"**Confidence:** {result['confidence']}\n"
    if result['factors']:
        response += f"**Factors:** {', '.join(result['factors'][:3])}\n"
    response += f"**Recommendation:** {result['recommendation']}"
    
    await ctx.send(response)


@bot.command(name="search")
async def search_cmd(ctx: commands.Context, *, query: str) -> None:
    """Search for cards by name (e.g. !search charizard)."""
    query = query.strip()
    if not query:
        await ctx.send("Usage: `!search <card_name>` (e.g. !search charizard)")
        return
    
    results = search_cards(query, limit=5)
    
    if not results:
        await ctx.send(f"No cards found for '{query}'")
        return
    
    response = f"**Search results for '{query}':**\n\n"
    for card in results:
        name = card.get("name", "Unknown")
        card_id = card.get("id", "Unknown")
        rarity = card.get("rarity", "")
        price = card.get("tcgplayer_market")
        price_str = f"${price:.2f}" if price else "No price"
        response += f"• **{name}** ({rarity}) - {price_str}\n  ID: `{card_id}`\n\n"
    
    await ctx.send(response)


@bot.command(name="alert")
async def alert_cmd(ctx: commands.Context, action: str = "list", *, args: str = "") -> None:
    """Manage price alerts. Usage: !alert list | !alert add <card_id> <above|below|change_percent> <value> | !alert delete <id>"""
    user_id = str(ctx.author.id)
    
    if action == "list":
        alerts = get_user_alerts(user_id)
        if not alerts:
            await ctx.send("You have no price alerts. Create one with `!alert add <card_id> above 100`")
            return
        
        response = "**Your Price Alerts:**\n\n"
        for alert in alerts:
            status = "✅" if alert.is_active else "❌"
            response += f"{status} **ID {alert.id}:** {alert.card_id} {alert.condition.value} ${alert.threshold:.2f}\n"
        await ctx.send(response)
    
    elif action == "add":
        parts = args.strip().split()
        if len(parts) < 3:
            await ctx.send(
                "Usage: `!alert add <card_id> above|below <price>`\n"
                "Example: `!alert add sv8-161 above 900`\n\n"
                "Or: `!alert add <card_id> change_percent <pct>`\n"
                "Example: `!alert add sv8-161 change_percent 10`"
            )
            return
        
        card_id = parts[0]
        condition = parts[1].lower()
        try:
            threshold = float(parts[2])
        except ValueError:
            await ctx.send("Price must be a number. Example: `!alert add sv8-161 above 900`")
            return
        
        if condition not in ["above", "below", "change_percent"]:
            await ctx.send("Condition must be 'above', 'below', or 'change_percent'")
            return
        
        try:
            alert = create_alert(user_id, card_id, condition, threshold)
            await ctx.send(f"✅ Alert created! Notify when **{card_id}** goes {condition} **${threshold:.2f}**")
        except Exception as e:
            await ctx.send(f"Failed to create alert: {e}")
    
    elif action == "delete":
        try:
            alert_id = int(args.strip())
            if delete_alert(alert_id, user_id):
                await ctx.send(f"✅ Alert {alert_id} deleted")
            else:
                await ctx.send("Alert not found or doesn't belong to you")
        except ValueError:
            await ctx.send("Usage: `!alert delete <alert_id>`")
    
    elif action == "check":
        triggered = check_alerts(user_id, use_live=ALERTS_USE_LIVE_PRICE)
        if triggered:
            response = "**🔔 Triggered Alerts:**\n\n"
            for t in triggered:
                response += f"• {t['message']}\n"
            await ctx.send(response)
        else:
            await ctx.send("No alerts triggered at this time.")
    
    else:
        await ctx.send("Usage: `!alert list|add|delete|check`")


@bot.command(name="portfolio")
async def portfolio_cmd(ctx: commands.Context) -> None:
    """View your card collection portfolio summary."""
    user_id = str(ctx.author.id)
    summary = get_portfolio_summary(user_id)
    
    if summary["total_cards"] == 0:
        await ctx.send("Your collection is empty. Add cards via the web API or use `!price` to check values.")
        return
    
    response = f"**📊 Portfolio Summary for {ctx.author.name}**\n\n"
    response += f"**Total Value:** ${summary['total_value']:.2f}\n"
    response += f"**Total Cards:** {summary['total_cards']}\n"
    response += f"**Unique Cards:** {summary['unique_cards']}\n"
    
    if summary.get('profit_loss') is not None:
        emoji = "📈" if summary['profit_loss'] >= 0 else "📉"
        response += f"**Profit/Loss:** {emoji} ${summary['profit_loss']:.2f} ({summary['roi_percent']:+.1f}%)\n"
    
    if summary['sets']:
        response += f"\n**Top Sets:**\n"
        top_sets = sorted(summary['sets'].items(), key=lambda x: x[1], reverse=True)[:3]
        for set_id, count in top_sets:
            response += f"• {set_id}: {count} cards\n"
    
    await ctx.send(response)


async def main() -> None:
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
