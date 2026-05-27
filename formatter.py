"""
Format the GPT analysis dict into a nicely readable Telegram message.
Telegram supports HTML parse mode.
"""


RATING_EMOJI = {
    # health
    "safe":    "🟢",
    "caution": "🟡",
    "harmful": "🔴",
    # ecology
    "green":   "🌿",
    "yellow":  "🟡",
    "red":     "🔴",
}

RECOMMEND_EMOJI = {
    "buy":             "✅ Buy it!",
    "ok-with-caution": "⚠️ OK with caution",
    "avoid":           "🚫 Avoid",
}

SCORE_BAR_LENGTH = 10


def _score_bar(score: int) -> str:
    """Visual progress bar  ████░░░░░░ 65/100"""
    filled = round(score / 100 * SCORE_BAR_LENGTH)
    empty  = SCORE_BAR_LENGTH - filled
    bar    = "█" * filled + "░" * empty
    return f"{bar}  {score}/100"


def format_report(analysis: dict, product_name: str | None = None) -> str:
    """
    Build the full Telegram HTML report from a GPT analysis dict.
    Works for both image-analysis and text-analysis responses.
    """
    name    = analysis.get("product_name") or product_name or "Unknown product"
    brand   = analysis.get("brand", "")
    verdict = analysis.get("one_line_verdict", "")
    score   = analysis.get("overall_eco_score_0_100", 0)
    rec     = analysis.get("recommendation", "ok-with-caution")

    health  = analysis.get("health", {})
    ecology = analysis.get("ecology", {})
    certs   = analysis.get("certifications", {})
    gw      = analysis.get("greenwashing_flags", [])

    h_rating = health.get("overall_rating", "caution")
    e_rating = ecology.get("overall_rating", "yellow")

    lines = []

    # ── Header ──────────────────────────────────────────────────────────────
    lines.append(f"<b>🔍 {name}</b>" + (f"  •  <i>{brand}</i>" if brand else ""))
    lines.append("")
    lines.append(f"<b>{RECOMMEND_EMOJI.get(rec, rec)}</b>")
    lines.append(f"<i>{verdict}</i>")
    lines.append("")

    # ── Eco score bar ────────────────────────────────────────────────────────
    lines.append(f"<b>🌍 Eco Score</b>")
    lines.append(_score_bar(score))
    lines.append("")

    # ── Health ───────────────────────────────────────────────────────────────
    h_emoji = RATING_EMOJI.get(h_rating, "🟡")
    lines.append(f"<b>{h_emoji} Health Safety</b>")

    if ns := health.get("nutri_score"):
        lines.append(f"  • Nutri-Score: <b>{ns}</b>")
    if ng := health.get("nova_group"):
        nova_labels = {1: "Unprocessed", 2: "Processed ingredients", 3: "Processed", 4: "Ultra-processed"}
        lines.append(f"  • NOVA Group: <b>{ng}</b> ({nova_labels.get(ng, '')})")

    mp_risk = health.get("microplastics_risk", "low")
    mp_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(mp_risk, "🟡")
    lines.append(f"  • Microplastics risk: {mp_emoji} <b>{mp_risk.upper()}</b>")

    if mp_ings := health.get("microplastic_ingredients"):
        lines.append(f"    ↳ {', '.join(mp_ings)}")

    if hc := health.get("harmful_chemicals"):
        lines.append(f"  • ⚠️ Harmful chemicals: {', '.join(hc)}")

    if carc := health.get("carcinogens"):
        lines.append(f"  • ☠️ Carcinogens: {', '.join(carc)}")

    if ed := health.get("endocrine_disruptors"):
        lines.append(f"  • 🔬 Endocrine disruptors: {', '.join(ed)}")

    if allergens := health.get("allergens"):
        al = allergens if isinstance(allergens, list) else [allergens]
        if al:
            lines.append(f"  • 🥜 Allergens: {', '.join(al)}")

    lines.append(f"  • {health.get('health_notes', '')}")
    lines.append("")

    # ── Ecology ──────────────────────────────────────────────────────────────
    e_emoji = RATING_EMOJI.get(e_rating, "🟡")
    lines.append(f"<b>{e_emoji} Ecological Impact</b>")

    if es := ecology.get("eco_score"):
        lines.append(f"  • Eco-Score: <b>{es}</b>")

    palm = ecology.get("palm_oil_risk", "unknown")
    palm_emoji = {"yes": "🔴", "no": "🟢", "maybe": "🟡"}.get(palm, "❓")
    lines.append(f"  • Palm oil: {palm_emoji} {palm.upper()}")

    at = ecology.get("animal_testing", "unknown")
    at_emoji = "🐇" if at == "yes" else ("✅" if at in ("no", "cruelty-free-certified") else "❓")
    lines.append(f"  • Animal testing: {at_emoji} {at}")

    packaging = ecology.get("packaging_type", "unknown")
    recyclable = ecology.get("recyclable", "unknown")
    rec_emoji = {"yes": "♻️", "no": "🗑️", "partial": "⚠️"}.get(recyclable, "❓")
    lines.append(f"  • Packaging: {packaging}  {rec_emoji} {recyclable}")

    cf = ecology.get("carbon_footprint_estimate", "unknown")
    lines.append(f"  • Carbon footprint: {cf}")
    lines.append(f"  • {ecology.get('ecology_notes', '')}")
    lines.append("")

    # ── Certifications ───────────────────────────────────────────────────────
    cert_flags = []
    if certs.get("organic"):      cert_flags.append("🌱 Organic")
    if certs.get("fair_trade"):   cert_flags.append("🤝 Fair Trade")
    if certs.get("vegan"):        cert_flags.append("🐾 Vegan")
    if certs.get("cruelty_free"): cert_flags.append("🐰 Cruelty-Free")
    cert_flags += certs.get("other", [])

    if cert_flags:
        lines.append(f"<b>🏅 Certifications</b>")
        lines.append("  " + "  •  ".join(cert_flags))
        lines.append("")

    # ── Greenwashing flags ───────────────────────────────────────────────────
    if gw:
        lines.append(f"<b>🚨 Greenwashing Alerts</b>")
        for flag in gw:
            lines.append(f"  ⚠️ {flag}")
        lines.append("")

    lines.append("<i>Powered by EcoBot 🌿 • Data: OpenFoodFacts + GPT-4o</i>")

    return "\n".join(lines)
