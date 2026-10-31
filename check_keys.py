import asyncio
import os

from dotenv import load_dotenv

load_dotenv()

import voice
from guide import web_search
from models import Gemma


async def main():
    for key in ["GEMINI_API_KEY", "ELEVENLABS_API_KEY", "TAVILY_API_KEY"]:
        print(f"{key}: {'found' if os.getenv(key) else 'MISSING'}")
    try:
        print("Gemma:", (await Gemma().generate("Reply with the word ready."))[:80])
    except Exception as error:
        print("Gemma FAILED:", error)
    try:
        print("Tavily results:", len(await web_search("how to make a cheese sandwich")))
    except Exception as error:
        print("Tavily FAILED:", error)
    try:
        print("ElevenLabs audio bytes:", len(await voice.tts("Sarathi is ready.")))
    except Exception as error:
        print("ElevenLabs FAILED:", error)


asyncio.run(main())