import hashlib
import os
from pathlib import Path

import httpx

CACHE = Path(__file__).parent / "cache"


async def tts(text: str) -> bytes:
    voice = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    model = os.getenv("ELEVENLABS_TTS_MODEL", "eleven_flash_v2_5")
    key = hashlib.sha256(f"{voice}|{model}|{text}".encode()).hexdigest()
    path = CACHE / f"{key}.mp3"
    if path.exists():
        return path.read_bytes()
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
            headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
            json={"text": text, "model_id": model},
        )
    response.raise_for_status()
    CACHE.mkdir(exist_ok=True)
    path.write_bytes(response.content)
    return response.content