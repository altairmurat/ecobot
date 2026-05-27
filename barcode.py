"""
Barcode detection (pyzbar + opencv) and Open Food Facts API lookup.
"""
import httpx
import numpy as np
from io import BytesIO
from env import OFF_BASE_URL

# pyzbar / cv2 are optional; gracefully fail if not installed
try:
    import cv2
    from pyzbar.pyzbar import decode as pyzbar_decode
    BARCODE_LIBS_AVAILABLE = True
except ImportError:
    BARCODE_LIBS_AVAILABLE = False


def detect_barcode(image_bytes: bytes) -> str | None:
    """
    Try to extract a barcode string from raw image bytes.
    Returns the barcode string or None.
    """
    if not BARCODE_LIBS_AVAILABLE:
        return None

    # Decode image bytes → numpy array
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return None

    # Try grayscale first (better detection)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    codes = pyzbar_decode(gray)

    if not codes:
        # Fallback: try original colour image
        codes = pyzbar_decode(img)

    if codes:
        # Return first found barcode
        return codes[0].data.decode("utf-8")
    return None


async def lookup_openfoodfacts(barcode: str) -> dict | None:
    """
    Query the Open Food Facts API for a given barcode.
    Returns the product dict or None if not found.
    """
    url = f"{OFF_BASE_URL}/api/v0/product/{barcode}.json"
    async with httpx.AsyncClient(timeout=10.0) as http:
        try:
            r = await http.get(url)
            data = r.json()
        except Exception:
            return None

    if data.get("status") != 1:
        return None  # Product not found

    p = data.get("product", {})

    # Extract the most useful fields for eco analysis
    return {
        "barcode": barcode,
        "product_name": p.get("product_name") or p.get("product_name_en", ""),
        "brand": p.get("brands", ""),
        "categories": p.get("categories", ""),
        "countries": p.get("countries", ""),
        "ingredients_text": p.get("ingredients_text", ""),
        "ingredients_tags": p.get("ingredients_tags", []),
        "allergens": p.get("allergens", ""),
        "traces": p.get("traces", ""),
        "additives_tags": p.get("additives_tags", []),
        "nutriscore_grade": p.get("nutriscore_grade", "").upper() or None,
        "nova_group": p.get("nova_group") or None,
        "ecoscore_grade": p.get("ecoscore_grade", "").upper() or None,
        "ecoscore_score": p.get("ecoscore_score") or None,
        "packaging": p.get("packaging", ""),
        "packaging_tags": p.get("packaging_tags", []),
        "labels": p.get("labels", ""),
        "labels_tags": p.get("labels_tags", []),
        "manufacturing_places": p.get("manufacturing_places", ""),
        "origins": p.get("origins", ""),
        "palm_oil_ingredients": p.get("ingredients_from_palm_oil_tags", []),
        "image_url": p.get("image_url", ""),
    }
