"""
EcoBot – Telegram bot built with Telethon.

Supported flows:
  1. User sends a product PHOTO
       → try to read barcode from photo
       → if barcode found: Open Food Facts lookup + GPT text analysis
       → else: GPT-4o vision analysis of the image
  2. User sends a BARCODE NUMBER as text
       → Open Food Facts lookup + GPT text analysis
  3. /start, /help
"""

import asyncio
import json
from io import BytesIO

from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto

from env import API_ID, API_HASH, BOT_TOKEN
from barcode import detect_barcode, lookup_openfoodfacts
from gpt_client import analyse_image, analyse_product_data
from formatter import format_report
from database import SessionLocal
import models

# ── Telethon client ──────────────────────────────────────────────────────────
client = TelegramClient("ecobot_session", API_ID, API_HASH)

# ── Simple in-memory state: track what we expect from each user ──────────────
# state: None | "awaiting_text"
user_state: dict[int, str] = {}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _upsert_user(db, telegram_id: int, username: str | None, first_name: str | None):
    user = db.query(models.User).filter_by(telegram_id=telegram_id).first()
    if not user:
        user = models.User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
        )
        db.add(user)
        db.commit()


def _save_scan(db, telegram_id: int, analysis: dict, barcode: str | None, method: str):
    health  = analysis.get("health", {})
    ecology = analysis.get("ecology", {})
    certs   = analysis.get("certifications", {})

    scan = models.ProductScan(
        telegram_id=telegram_id,
        barcode=barcode or analysis.get("barcode_visible"),
        product_name=analysis.get("product_name"),
        brand=analysis.get("brand"),
        eco_score=ecology.get("eco_score"),
        eco_score_num=analysis.get("overall_eco_score_0_100"),
        nutri_score=health.get("nutri_score"),
        nova_group=health.get("nova_group"),
        microplastics_risk=health.get("microplastics_risk"),
        harmful_chemicals=", ".join(health.get("harmful_chemicals") or []),
        allergens=", ".join(health.get("allergens") or []),
        palm_oil=ecology.get("palm_oil_risk"),
        packaging_type=ecology.get("packaging_type"),
        recyclable=ecology.get("recyclable"),
        gpt_summary=analysis.get("one_line_verdict"),
        scan_method=method,
    )
    db.add(scan)
    db.commit()


async def _process_and_reply(event, image_bytes: bytes | None, barcode: str | None):
    """Core logic: decide which analysis path to take, then reply."""
    sender     = await event.get_sender()
    telegram_id = sender.id

    db = SessionLocal()
    try:
        _upsert_user(db, telegram_id, getattr(sender, "username", None), getattr(sender, "first_name", None))

        # ── Path A: we have a barcode ────────────────────────────────────────
        if barcode:
            off_data = await lookup_openfoodfacts(barcode)
            if off_data:
                await event.respond("🔍 Found in Open Food Facts! Analysing with GPT…")
                analysis = await analyse_product_data(off_data)
                # Enrich with names from OFF
                analysis.setdefault("product_name", off_data.get("product_name"))
                analysis.setdefault("brand", off_data.get("brand"))
                method = "barcode"
            else:
                # Barcode not in OFF → fall back to vision if we have the image
                if image_bytes:
                    await event.respond("📦 Barcode found but not in database. Analysing photo with GPT Vision…")
                    analysis = await analyse_image(image_bytes)
                    method = "photo"
                else:
                    await event.respond(
                        "❌ Barcode not found in Open Food Facts and no image provided.\n"
                        "Try sending a clear product photo instead."
                    )
                    return

        # ── Path B: photo, no barcode → vision ───────────────────────────────
        elif image_bytes:
            await event.respond("🤖 Analysing your product photo with GPT Vision…")
            analysis = await analyse_image(image_bytes)
            method = "photo"

        else:
            await event.respond("❓ Please send a product photo or a barcode number.")
            return

        # ── Format & send ────────────────────────────────────────────────────
        report = format_report(analysis)
        await event.respond(report, parse_mode="html")

        _save_scan(db, telegram_id, analysis, barcode, method)

    except json.JSONDecodeError:
        await event.respond("⚠️ GPT returned unexpected data. Please try again.")
    except Exception as exc:
        await event.respond(f"⚠️ Error: {exc}")
        raise
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Handlers
# ─────────────────────────────────────────────────────────────────────────────

@client.on(events.NewMessage(pattern="/start"))
async def cmd_start(event):
    await event.respond(
        "🌿 <b>Welcome to EcoBot!</b>\n\n"
        "I analyse products for their <b>eco-friendliness</b>, "
        "<b>health safety</b>, and <b>environmental impact</b>.\n\n"
        "<b>How to use:</b>\n"
        "📸 Send a photo of any product → I'll analyse it\n"
        "🔢 Send a barcode number (EAN/UPC) → I'll look it up\n\n"
        "/help for more info",
        parse_mode="html",
    )


@client.on(events.NewMessage(pattern="/help"))
async def cmd_help(event):
    await event.respond(
        "🌿 <b>EcoBot Help</b>\n\n"
        "<b>What I check:</b>\n"
        "• Microplastics risk\n"
        "• Harmful chemicals (parabens, BPA, SLS…)\n"
        "• Carcinogens & endocrine disruptors\n"
        "• Nutri-Score & NOVA group (food)\n"
        "• Eco-Score & carbon footprint\n"
        "• Palm oil, animal testing, recyclability\n"
        "• Greenwashing flags\n\n"
        "<b>Tips for best results:</b>\n"
        "• Photo: make sure the ingredient list is visible\n"
        "• Barcode: just type the number (e.g. <code>5000112548167</code>)\n\n"
        "Questions? @your_support_handle",
        parse_mode="html",
    )


@client.on(events.NewMessage(func=lambda e: e.photo))
async def handle_photo(event):
    """User sent a photo → download, try barcode, then analyse."""
    await event.respond("📷 Photo received! Checking for barcode…")

    buf = BytesIO()
    await client.download_media(event.message, file=buf)
    image_bytes = buf.getvalue()

    barcode = detect_barcode(image_bytes)
    if barcode:
        await event.respond(f"✅ Barcode detected: <code>{barcode}</code>", parse_mode="html")

    await _process_and_reply(event, image_bytes=image_bytes, barcode=barcode)


@client.on(events.NewMessage(func=lambda e: not e.photo and e.text and not e.text.startswith("/")))
async def handle_text(event):
    """
    User typed text.
    If it looks like a barcode (8-14 digits), treat as barcode lookup.
    Otherwise, ask for a photo.
    """
    text = event.text.strip()

    # EAN-8, EAN-13, UPC-A, UPC-E, ITF-14 are 8-14 digit numbers
    if text.isdigit() and 8 <= len(text) <= 14:
        await event.respond(f"🔍 Looking up barcode <code>{text}</code> in Open Food Facts…", parse_mode="html")
        await _process_and_reply(event, image_bytes=None, barcode=text)
    else:
        await event.respond(
            "❓ I didn't understand that.\n\n"
            "Please:\n"
            "📸 Send a <b>product photo</b>, or\n"
            "🔢 Type a <b>barcode number</b> (8-14 digits)",
            parse_mode="html",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Entry point (standalone – also importable by main.py)
# ─────────────────────────────────────────────────────────────────────────────

async def start_bot():
    await client.start(bot_token=BOT_TOKEN)
    print("✅ EcoBot is running…")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(start_bot())
