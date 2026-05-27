"""
GPT helpers: image vision analysis + text/barcode analysis.
"""
import json
import base64
from io import BytesIO
from openai import AsyncOpenAI
from env import OPENAI_API_KEY
from prompts import IMAGE_ANALYSIS_PROMPT, TEXT_ANALYSIS_PROMPT

client = AsyncOpenAI(api_key=OPENAI_API_KEY)


async def analyse_image(image_bytes: bytes) -> dict:
    """
    Send a product photo to GPT-4o vision.
    Returns parsed JSON dict or raises ValueError.
    """
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    response = await client.chat.completions.create(
        model="gpt-4o",
        max_tokens=1500,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": IMAGE_ANALYSIS_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    },
                ],
            }
        ],
    )

    raw = response.choices[0].message.content.strip()
    # Strip markdown fences if GPT wraps in ```json
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)


async def analyse_product_data(product_data: dict) -> dict:
    """
    Send structured product data (from Open Food Facts) to GPT-4o-mini.
    Returns parsed JSON dict.
    """
    prompt = TEXT_ANALYSIS_PROMPT.format(product_data=json.dumps(product_data, ensure_ascii=False, indent=2))

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.choices[0].message.content.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)
