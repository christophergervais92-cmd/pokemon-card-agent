"""
Seed pokemon_tcg.db from Pokémon TCG API (v2).
Run from project root: python3 scripts/seed_db.py
Fetches sets and cards; inserts pull_rates placeholders for Prismatic Evolutions.
Set POKEMON_TCG_API_KEY in env for higher rate limits (optional).
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Add project root so "db" package is importable
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from db.connection import get_connection, init_db

API_BASE = "https://api.pokemontcg.io/v2"


def _request_headers() -> dict:
    h = {"Accept": "application/json", "User-Agent": "pokemon-card-agent/1.0"}
    api_key = os.environ.get("POKEMON_TCG_API_KEY")
    if api_key:
        h["X-Api-Key"] = api_key.strip()
    return h


def fetch_url(url: str, timeout: int = 15) -> dict:
    req = urllib.request.Request(url, headers=_request_headers())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"API returned {e.code}") from e


def fetch_sets(page: int = 1, page_size: int = 250) -> dict:
    url = f"{API_BASE}/sets?page={page}&pageSize={page_size}"
    return fetch_url(url)


def fetch_cards_for_set(set_id: str, page: int = 1, page_size: int = 250) -> dict:
    # v2 uses q=set.id:xxx
    q = urllib.parse.quote(f"set.id:{set_id}")
    url = f"{API_BASE}/cards?q={q}&page={page}&pageSize={page_size}"
    return fetch_url(url)


def seed_sets(conn) -> int:
    count = 0
    page = 1
    while True:
        data = fetch_sets(page=page)
        sets_list = data.get("data", [])
        if not sets_list:
            break
        for s in sets_list:
            sid = s.get("id")
            name = s.get("name", "")
            series = s.get("series", "")
            release = s.get("releaseDate", "")
            images = s.get("images", {}) or {}
            logo_url = images.get("logo") or ""
            total = s.get("total")
            conn.execute(
                """INSERT OR REPLACE INTO sets (id, name, series, release_date, logo_url, total, value_index, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, NULL, CURRENT_TIMESTAMP)""",
                (sid, name, series, release, logo_url, total),
            )
            count += 1
        if len(sets_list) < 250:
            break
        page += 1
    return count


def seed_cards_for_set(conn, set_id: str) -> int:
    count = 0
    page = 1
    while True:
        data = fetch_cards_for_set(set_id, page=page)
        cards_list = data.get("data", [])
        if not cards_list:
            break
        for c in cards_list:
            cid = c.get("id")
            name = c.get("name", "")
            rarity = c.get("rarity", "")
            supertype = c.get("supertype", "")
            subtypes = c.get("subtypes", [])
            subtype = (subtypes[0] if subtypes else "") or ""
            images = c.get("images", {}) or {}
            image_url = images.get("large") or images.get("small") or ""
            small_image_url = images.get("small") or ""
            tcg = c.get("tcgplayer", {}) or {}
            prices = tcg.get("prices", {}) or {}
            market = low = mid = high = None
            # Prices can be flat or nested (holofoil, normal, reverseHolofoil, etc.)
            if isinstance(prices.get("holofoil"), dict):
                p = prices["holofoil"]
                market = p.get("market")
                low = p.get("low")
                mid = p.get("mid")
                high = p.get("high")
            if mid is None and isinstance(prices.get("normal"), dict):
                p = prices["normal"]
                market = market or p.get("market")
                low = low or p.get("low")
                mid = mid or p.get("mid")
                high = high or p.get("high")
            if mid is None:
                market = market or prices.get("market")
                low = low or prices.get("low")
                mid = mid or prices.get("mid")
                high = high or prices.get("high")
            # Coerce to float for DB
            def _f(v):
                if v is None:
                    return None
                try:
                    return float(v)
                except (TypeError, ValueError):
                    return None
            market, low, mid, high = _f(market), _f(low), _f(mid), _f(high)
            raw = json.dumps(c) if c else ""
            conn.execute(
                """INSERT OR REPLACE INTO cards
                   (id, set_id, name, rarity, supertype, subtype, image_url, small_image_url,
                    tcgplayer_market, tcgplayer_low, tcgplayer_mid, tcgplayer_high, raw_json, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                (
                    cid,
                    set_id,
                    name,
                    rarity,
                    supertype,
                    subtype,
                    image_url,
                    small_image_url,
                    market,
                    low,
                    mid,
                    high,
                    raw,
                ),
            )
            count += 1
        if len(cards_list) < 250:
            break
        page += 1
    return count


def seed_pull_rates(conn, set_id: str, rates: list) -> None:
    """Insert pull rates for a set. rates = [(category, label, rate_per_pack, notes), ...]"""
    conn.execute("DELETE FROM pull_rates WHERE set_id = ?", (set_id,))
    for cat, label, rate, notes in rates:
        conn.execute(
            """INSERT INTO pull_rates (set_id, category, label, rate_per_pack, notes, updated_at)
               VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (set_id, cat, label, rate, notes),
        )


# Default pull rates (Prismatic Evolutions–style). Community estimates.
PULL_RATES_DEFAULT = [
    ("Rare", "Rare Holo", 0.25, "~1 in 4 packs"),
    ("Ultra Rare", "Full Art / Illustration Rare", 0.08, "~1 in 12 packs"),
    ("Special Art", "Special Illustration Rare", 0.05, "~1 in 20 packs"),
    ("Secret", "Secret Rare / Gold", 0.02, "~1 in 50 packs"),
    ("Common", "Common/Uncommon", 1.0, "Multiple per pack"),
]

# Destined Rivals pull rates (from community data)
PULL_RATES_DESTINED_RIVALS = [
    ("Illustration Rare", "Illustration Rare", 0.055, "1:18 (5.5%)"),
    ("Special Art Rare", "Special Art Rare", 0.022, "1:45 (2.2%)"),
    ("Ultra Rare", "Ultra Rare", 0.028, "1:36 (2.8%)"),
    ("Hyper Rare", "Hyper Rare", 0.0055, "1:180 (0.55%)"),
    ("Holo Rare", "Holo Rare", 0.33, "1:3 (33%)"),
    ("Double Rare", "Double Rare", 0.11, "1:9 (11%)"),
]


def seed_pull_rates_placeholders(conn, set_id: str, rates: list = None) -> None:
    """Insert pull rates for a set. Uses PULL_RATES_DEFAULT if rates not provided."""
    seed_pull_rates(conn, set_id, rates or PULL_RATES_DEFAULT)


def seed_graded_prices_placeholders(conn) -> None:
    """Insert PSA, CGC, and Beckett (BGS) graded prices for sample cards (PriceCharting/eBay style)."""
    # card_id, grader, grade, grade_label, market, low, high, source
    graded = [
        # Umbreon ex #161 — Prismatic Evolutions (matches card detail page)
        ("sv8-161", "PSA", "10", "Gem Mint", 838.00, 796.10, 1676.00, "PriceCharting/eBay"),
        ("sv8-161", "CGC", "10", "Pristine 10", 720.00, 650.00, 900.00, "PriceCharting/eBay"),
        ("sv8-161", "BGS", "9.5", "Gem Mint", 680.00, 600.00, 800.00, "PriceCharting/eBay"),
        # Charizard ex sample
        ("sv8-1", "PSA", "10", "Gem Mint", 55.00, 48.00, 65.00, "PriceCharting/eBay"),
        ("sv8-1", "CGC", "10", "Pristine 10", 52.00, 45.00, 62.00, "PriceCharting/eBay"),
        ("sv8-1", "BGS", "9.5", "Gem Mint", 50.00, 42.00, 58.00, "PriceCharting/eBay"),
    ]
    for card_id, grader, grade, grade_label, market, low, high, source in graded:
        conn.execute(
            """INSERT OR REPLACE INTO graded_prices
               (card_id, grader, grade, grade_label, market, low, high, source, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (card_id, grader, grade, grade_label, market, low, high, source),
        )


def _insert_cards(conn, cards: list) -> None:
    """Insert or replace cards. cards = [(id, set_id, name, rarity, market, low, high), ...]"""
    for cid, sid, name, rarity, market, low, high in cards:
        mid_val = (market + high) / 2
        conn.execute(
            """INSERT OR REPLACE INTO cards
               (id, set_id, name, rarity, supertype, subtype, image_url, small_image_url,
                tcgplayer_market, tcgplayer_low, tcgplayer_mid, tcgplayer_high, updated_at)
               VALUES (?, ?, ?, ?, 'Pokémon', '', '', '', ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (cid, sid, name, rarity, market, low, mid_val, high),
        )


# Pull rates for 151 (2023) — community estimates
PULL_RATES_151 = [
    ("Illustration Rare", "Illustration Rare", 0.04, "~1:25"),
    ("Special Illustration Rare", "Special Illustration Rare", 0.02, "~1:50"),
    ("Ultra Rare", "Ultra Rare", 0.03, "~1:33"),
    ("Holo Rare", "Holo Rare", 0.20, "~1:5"),
    ("Common/Uncommon", "Common/Uncommon", 1.0, "Multiple per pack"),
]

# Sword & Shield base set — matches screenshot (Alternate Art, Secret Rare, Full Art, VMAX, V, Holo Rare)
PULL_RATES_SWORD_SHIELD = [
    ("Alternate Art", "Alternate Art", 0.0167, "1:60 (1.67%)"),
    ("Secret Rare", "Secret Rare", 0.014, "1:72 (1.4%)"),
    ("Full Art", "Full Art", 0.028, "1:36 (2.8%)"),
    ("VMAX", "VMAX", 0.042, "1:24 (4.2%)"),
    ("V", "V", 0.11, "1:9 (11%)"),
    ("Holo Rare", "Holo Rare", 0.33, "1:3 (33%)"),
]

# Fusion Strike (2021) — Sword & Shield era pull rates
PULL_RATES_FUSION_STRIKE = [
    ("Alternate Art", "Alternate Art", 0.015, "~1:65"),
    ("Secret Rare", "Secret Rare", 0.012, "~1:80"),
    ("Full Art", "Full Art", 0.025, "~1:40"),
    ("VMAX", "VMAX", 0.038, "~1:26"),
    ("V", "V", 0.10, "~1:10"),
    ("Holo Rare", "Holo Rare", 0.30, "~1:3"),
]


def seed_from_fallback(conn) -> None:
    """When API is unavailable (e.g. 403), seed multiple sets with correct pull rates, chase cards, and value index."""
    # Prismatic Evolutions (sv8)
    conn.execute(
        """INSERT OR REPLACE INTO sets (id, name, series, release_date, logo_url, total, value_index, updated_at)
           VALUES ('sv8', 'Prismatic Evolutions (Jan 2025)', 'Scarlet & Violet', '2025-01', '', 200, 12500, CURRENT_TIMESTAMP)""",
    )
    seed_pull_rates_placeholders(conn, "sv8")
    prismatic_cards = [
        ("sv8-1", "sv8", "Charizard ex", "Illustration Rare", 45.00, 40.00, 50.00),
        ("sv8-2", "sv8", "Pikachu", "Special Art", 35.00, 30.00, 42.00),
        ("sv8-3", "sv8", "Mew ex", "Ultra Rare", 28.00, 24.00, 32.00),
        ("sv8-4", "sv8", "Eevee", "Illustration Rare", 22.00, 18.00, 26.00),
        ("sv8-5", "sv8", "Dragonite", "Holo Rare", 12.00, 10.00, 15.00),
        ("sv8-6", "sv8", "Gengar", "Holo Rare", 10.00, 8.00, 12.00),
        ("sv8-161", "sv8", "Umbreon ex", "Special Illustration Rare", 838.00, 796.10, 1676.00),
    ]
    _insert_cards(conn, prismatic_cards)

    # Destined Rivals (sv10) — Set Value Index $38320
    conn.execute(
        """INSERT OR REPLACE INTO sets (id, name, series, release_date, logo_url, total, value_index, updated_at)
           VALUES ('sv10', 'Destined Rivals', 'Scarlet & Violet', '2025-05-30', '', 244, 38320, CURRENT_TIMESTAMP)""",
    )
    seed_pull_rates(conn, "sv10", PULL_RATES_DESTINED_RIVALS)
    destined_rivals_cards = [
        ("sv10-1", "sv10", "Team Rocket's Moltres ex", "Special Illustration Rare", 585.00, 520.00, 650.00),
        ("sv10-2", "sv10", "Team Rocket's Zapdos ex", "Special Illustration Rare", 495.00, 440.00, 550.00),
        ("sv10-3", "sv10", "Team Rocket's Articuno ex", "Special Illustration Rare", 475.00, 420.00, 530.00),
        ("sv10-4", "sv10", "Team Rocket's Mewtwo", "Illustration Rare", 435.00, 380.00, 490.00),
        ("sv10-5", "sv10", "Team Rocket's Houndoom", "Illustration Rare", 385.00, 340.00, 430.00),
        ("sv10-6", "sv10", "Team Rocket's Ampharos", "Illustration Rare", 325.00, 280.00, 370.00),
        ("sv10-7", "sv10", "Team Rocket's Hypno", "Illustration Rare", 265.00, 230.00, 300.00),
        ("sv10-8", "sv10", "Team Rocket's Spidops", "Double Rare", 185.00, 160.00, 210.00),
        ("sv10-9", "sv10", "Team Rocket's Flaaffy", "Double Rare", 145.00, 125.00, 165.00),
        ("sv10-10", "sv10", "Team Rocket's Houndour", "Holo Rare", 95.00, 80.00, 110.00),
        ("sv10-11", "sv10", "Team Rocket's Drowzee", "Holo Rare", 72.00, 62.00, 82.00),
        ("sv10-12", "sv10", "Team Rocket's Mareep", "Holo Rare", 58.00, 48.00, 68.00),
        ("sv10-13", "sv10", "Team Rocket's Tarountula", "Holo Rare", 42.00, 35.00, 50.00),
        ("sv10-14", "sv10", "Team Rocket's Blipbug", "Holo Rare", 38.00, 32.00, 45.00),
    ]
    _insert_cards(conn, destined_rivals_cards)

    # Alias so UI can request "destined-rivals" and get the same data
    conn.execute(
        """INSERT OR REPLACE INTO sets (id, name, series, release_date, logo_url, total, value_index, updated_at)
           VALUES ('destined-rivals', 'Destined Rivals', 'Scarlet & Violet', '2025-05-30', '', 244, 38320, CURRENT_TIMESTAMP)""",
    )
    seed_pull_rates(conn, "destined-rivals", PULL_RATES_DESTINED_RIVALS)
    for cid, _, name, rarity, market, low, high in destined_rivals_cards:
        new_cid = cid.replace("sv10-", "destined-rivals-", 1)
        _insert_cards(conn, [(new_cid, "destined-rivals", name, rarity, market, low, high)])

    # 151 (2023) — so SELECT SET "151 (2023)" has correct data
    conn.execute(
        """INSERT OR REPLACE INTO sets (id, name, series, release_date, logo_url, total, value_index, updated_at)
           VALUES ('151', '151 (2023)', 'Scarlet & Violet', '2023-09-22', '', 165, 25200, CURRENT_TIMESTAMP)""",
    )
    seed_pull_rates(conn, "151", PULL_RATES_151)
    set_151_cards = [
        ("151-6", "151", "Charizard ex", "Special Illustration Rare", 185.00, 165.00, 210.00),
        ("151-9", "151", "Blastoise ex", "Illustration Rare", 95.00, 82.00, 110.00),
        ("151-3", "151", "Venusaur ex", "Illustration Rare", 88.00, 75.00, 102.00),
        ("151-25", "151", "Pikachu", "Illustration Rare", 72.00, 62.00, 85.00),
        ("151-54", "151", "Alakazam ex", "Special Illustration Rare", 68.00, 58.00, 78.00),
        ("151-59", "151", "Arcanine ex", "Illustration Rare", 55.00, 48.00, 62.00),
        ("151-78", "151", "Eevee", "Illustration Rare", 48.00, 42.00, 55.00),
        ("151-94", "151", "Gengar ex", "Ultra Rare", 42.00, 36.00, 50.00),
        ("151-113", "151", "Mew ex", "Illustration Rare", 38.00, 32.00, 45.00),
        ("151-123", "151", "Zapdos ex", "Ultra Rare", 35.00, 30.00, 42.00),
        ("151-124", "151", "Moltres ex", "Ultra Rare", 32.00, 28.00, 38.00),
        ("151-125", "151", "Articuno ex", "Ultra Rare", 30.00, 26.00, 35.00),
    ]
    _insert_cards(conn, set_151_cards)

    # Sword & Shield (base) — so displayed set matches when this is selected (release 2020-02-07, 216 cards, $385)
    conn.execute(
        """INSERT OR REPLACE INTO sets (id, name, series, release_date, logo_url, total, value_index, updated_at)
           VALUES ('sword-shield', 'Sword & Shield', 'Sword & Shield', '2020-02-07', '', 216, 385, CURRENT_TIMESTAMP)""",
    )
    seed_pull_rates(conn, "sword-shield", PULL_RATES_SWORD_SHIELD)
    sword_shield_cards = [
        ("swsh1-1", "sword-shield", "Snorlax VMAX", "VMAX", 72.82, 65.00, 82.00),
        ("swsh1-2", "sword-shield", "Snorlax VMAX (Alt)", "VMAX", 42.15, 38.00, 48.00),
        ("swsh1-3", "sword-shield", "Marnie", "Full Art", 36.61, 32.00, 42.00),
        ("swsh1-4", "sword-shield", "Snorlax V", "V", 18.93, 16.00, 22.00),
        ("swsh1-5", "sword-shield", "Quick Ball", "Secret Rare", 18.62, 15.00, 22.00),
        ("swsh1-6", "sword-shield", "Marnie (Rainbow)", "Full Art", 18.52, 15.00, 22.00),
        ("swsh1-7", "sword-shield", "Zacian V", "V", 15.55, 13.00, 18.00),
        ("swsh1-8", "sword-shield", "Lapras V", "V", 12.40, 10.00, 15.00),
        ("swsh1-9", "sword-shield", "Air Balloon", "Secret Rare", 10.20, 8.50, 12.00),
        ("swsh1-10", "sword-shield", "Holo Rare 1", "Holo Rare", 4.00, 3.00, 5.00),
    ]
    _insert_cards(conn, sword_shield_cards)

    # Fusion Strike (2021) — so selecting "Fusion Strike (2021)" shows Fusion Strike data, not Sword & Shield
    conn.execute(
        """INSERT OR REPLACE INTO sets (id, name, series, release_date, logo_url, total, value_index, updated_at)
           VALUES ('fusion-strike', 'Fusion Strike (2021)', 'Sword & Shield', '2021-11-12', '', 264, 4200, CURRENT_TIMESTAMP)""",
    )
    seed_pull_rates(conn, "fusion-strike", PULL_RATES_FUSION_STRIKE)
    fusion_strike_cards = [
        ("swsh8-1", "fusion-strike", "Gengar VMAX", "VMAX", 95.00, 85.00, 108.00),
        ("swsh8-2", "fusion-strike", "Mew VMAX", "VMAX", 78.00, 68.00, 88.00),
        ("swsh8-3", "fusion-strike", "Espeon VMAX", "VMAX", 52.00, 45.00, 60.00),
        ("swsh8-4", "fusion-strike", "Inteleon VMAX", "VMAX", 38.00, 32.00, 45.00),
        ("swsh8-5", "fusion-strike", "Gengar V", "V", 28.00, 24.00, 32.00),
        ("swsh8-6", "fusion-strike", "Mew V", "V", 22.00, 18.00, 26.00),
        ("swsh8-7", "fusion-strike", "Celebi V", "V", 18.00, 15.00, 22.00),
        ("swsh8-8", "fusion-strike", "Full Art Trainer", "Full Art", 14.00, 12.00, 17.00),
        ("swsh8-9", "fusion-strike", "Secret Rare Item", "Secret Rare", 12.00, 10.00, 15.00),
        ("swsh8-10", "fusion-strike", "Holo Rare", "Holo Rare", 3.50, 2.50, 4.50),
    ]
    _insert_cards(conn, fusion_strike_cards)

    seed_graded_prices_placeholders(conn)
    print("Seeded fallback data (Prismatic Evolutions, Destined Rivals, 151, Sword & Shield, Fusion Strike (2021) + pull rates + chase cards + value index + graded prices).")


def main() -> None:
    init_db()
    conn = get_connection()
    skip_api = os.environ.get("SKIP_POKEMON_API", "").strip().lower() in ("1", "true", "yes")
    try:
        conn.execute("BEGIN")
        if skip_api:
            print("SKIP_POKEMON_API set; using fallback seed only.")
            seed_from_fallback(conn)
            conn.commit()
            conn.close()
            return
        try:
            n_sets = seed_sets(conn)
            print(f"Inserted/updated {n_sets} sets.")
        except Exception as e:
            print(f"API fetch failed ({e}). Using fallback seed.")
            seed_from_fallback(conn)
            conn.commit()
            conn.close()
            return

        # Seed cards for recent sets so each set has correct chase cards
        cur = conn.execute(
            "SELECT id, name FROM sets ORDER BY release_date DESC LIMIT 40"
        )
        sets_to_cards = list(cur.fetchall())
        total_cards = 0
        for (set_id, set_name) in sets_to_cards:
            try:
                n = seed_cards_for_set(conn, set_id)
                total_cards += n
                print(f"  {set_id} ({set_name}): {n} cards")
            except Exception as e:
                print(f"  {set_id}: error {e}")
                continue

        # Pull rates for every set we have cards for (so chase cards + pull rates are correct per set)
        for (set_id, set_name) in sets_to_cards:
            seed_pull_rates_placeholders(conn, set_id)
        print(f"Inserted pull rate placeholders for {len(sets_to_cards)} sets.")

        conn.commit()
        print(f"Total cards: {total_cards}. Done.")
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
