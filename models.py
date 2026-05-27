from sqlalchemy import Column, Integer, String, Float, Text, DateTime, BigInteger
from sqlalchemy.sql import func
from database import Base


class User(Base):
    """Telegram users who have interacted with the bot."""
    __tablename__ = "users"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username    = Column(String(128), nullable=True)
    first_name  = Column(String(128), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())


class ProductScan(Base):
    """Every product a user has scanned / analyzed."""
    __tablename__ = "product_scans"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id     = Column(BigInteger, nullable=False, index=True)
    barcode         = Column(String(64),  nullable=True)   # EAN/UPC if detected
    product_name    = Column(String(256), nullable=True)
    brand           = Column(String(128), nullable=True)

    # ── Eco scores ────────────────────────────────────────────────
    eco_score       = Column(String(8),   nullable=True)   # A / B / C / D / E
    eco_score_num   = Column(Float,       nullable=True)   # 0-100
    nutri_score     = Column(String(8),   nullable=True)   # A / B / C / D / E
    nova_group      = Column(Integer,     nullable=True)   # 1-4

    # ── Health flags ──────────────────────────────────────────────
    microplastics_risk  = Column(String(32), nullable=True)   # low / medium / high
    harmful_chemicals   = Column(Text,       nullable=True)   # comma-sep list
    allergens           = Column(Text,       nullable=True)

    # ── Environment flags ─────────────────────────────────────────
    palm_oil            = Column(String(8),  nullable=True)   # yes / no / maybe
    packaging_type      = Column(String(64), nullable=True)
    recyclable          = Column(String(8),  nullable=True)   # yes / no / partial

    # ── Raw GPT analysis ─────────────────────────────────────────
    gpt_summary         = Column(Text, nullable=True)

    # ── Meta ──────────────────────────────────────────────────────
    scan_method         = Column(String(16), nullable=True)  # barcode / photo / text
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
