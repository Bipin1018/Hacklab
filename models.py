import json
import os
import re

import httpx


class Gemma:
    async def generate(self, prompt: str, images: str | list[str] | None = None) -> str:
        parts = [{"text": prompt}]
        for image in [images] if isinstance(images, str) else images or []:
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": image}})
        model = os.getenv("GEMMA_MODEL", "gemma-4-31b-it")
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
                json={"contents": [{"role": "user", "parts": parts}]},
            )
        response.raise_for_status()
        content = response.json()["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in content if not p.get("thought"))


def parse_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


async def ask_json(model, prompt: str, images: str | list[str] | None = None) -> dict:
    try:
        return parse_json(await model.generate(prompt, images))
    except (httpx.HTTPError, KeyError, IndexError) as error:
        print(f"Gemma request failed: {type(error).__name__}")
        return {}