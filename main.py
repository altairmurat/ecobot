"""
main.py – FastAPI entry point.

Run with:  uvicorn main:app --reload
The Telegram bot starts automatically when FastAPI starts.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from database import SessionLocal, engine, get_db
import models
from bot import client, start_bot


# ── DB init + bot lifecycle ──────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    models.Base.metadata.create_all(bind=engine)
    print("✅ Database tables ready")

    bot_task = asyncio.create_task(start_bot())

    yield  # app is running

    # Shutdown
    bot_task.cancel()
    await client.disconnect()
    print("👋 EcoBot stopped")


app = FastAPI(title="EcoBot API", lifespan=lifespan)


# ── Health check ─────────────────────────────────────────────────────────────

@app.get("/")
async def ping():
    return {"status": "ok", "service": "EcoBot"}


# ── Admin / stats endpoints ──────────────────────────────────────────────────

@app.get("/stats")
async def stats(db: Session = Depends(get_db)):
    """Basic usage stats."""
    total_users = db.query(models.User).count()
    total_scans = db.query(models.ProductScan).count()
    return {
        "total_users": total_users,
        "total_scans": total_scans,
    }


@app.get("/scans/{telegram_id}")
async def user_scans(telegram_id: int, db: Session = Depends(get_db)):
    """Return the last 20 scans for a given Telegram user."""
    scans = (
        db.query(models.ProductScan)
        .filter_by(telegram_id=telegram_id)
        .order_by(models.ProductScan.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": s.id,
            "product_name": s.product_name,
            "brand": s.brand,
            "eco_score": s.eco_score,
            "eco_score_num": s.eco_score_num,
            "microplastics_risk": s.microplastics_risk,
            "recommendation": s.gpt_summary,
            "scan_method": s.scan_method,
            "created_at": str(s.created_at),
        }
        for s in scans
    ]
