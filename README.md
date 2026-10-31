# Sārathi (सारथि)

**A hands-free, voice-guided repair assistant that runs in your browser.**

*Sārathi* is Sanskrit for a charioteer: the trusted guide who steers beside you.

You are lying on the floor behind a washing machine. Your hands are wet and busy.
You cannot scrub through a 22-minute video to find the 40 seconds that matter. So
you talk to Sārathi, and it talks back: one step at a time, answering your questions,
looking through your camera and stopping the moment you say stop.

Built at the Hacktoberfest Hack Day Mikkeli, hosted by Hacklab Mikkeli ry.

## The problem

A washing machine that will not drain often has a blocked filter. The usual fix
takes a towel and twenty minutes. People throw these machines away anyway, because
at the moment you are on the floor with your hands inside the machine, there is no
easy way to get the one instruction you need.

Written manuals assume you can read while working. Videos assume you have a free
hand. Neither can look at what you are holding and tell you whether it matches.

## What Sārathi does

1. You say what's wrong: *"my washing machine won't drain."* You can add up to 6
   photos, and Sārathi lists the parts it can see.
2. It lists only the items you need. It shows no shop links until you ask.
3. It speaks the safety points and waits for you to say you're ready.
4. It guides you one spoken step at a time. Say **next**, **back**, **repeat** or
   **stuck**, or just ask: *"where do I find the filter cap?"*
5. After each fix attempt it asks whether that worked. Say yes, and you skip the
   remaining steps.
6. If you're missing something, say *"I don't have wood glue"*. A shopping sheet opens
   over your current step, and your step doesn't change. Sārathi never places an order.

### Talking to it

| You say | Sārathi |
|---|---|
| *"Sarathi"* | Answers "Yes?" |
| *"Next"*, *"okay, done"*, *"what now?"*, *"keep going"* | Moves to the next step |
| *"Say that again"*, *"sorry?"*, *"one more time"* | Repeats the step |
| *"Go back"*, *"go to step 4"* | Moves to that step |
| *"Which way does it turn?"*, then *"and how far?"* | Talks it through and remembers what you just said, from the guide or a fresh web search |
| *"Where are we?"* | Tells you the step and repeats it |
| *"Set a timer for ten minutes"* | Runs a timer on screen, then tells you when it's done |
| *"Check this"* or *"Take a look"* | Takes a photo in three seconds and compares it with the step |
| *"Hold on"* | Stops talking and waits |

On desktop browsers you can talk over Sārathi with short commands. On phones the mic
and speaker clash, so tap the voice pill or any button to cut it off.

Every voice command also has a button, and either one cuts Sārathi off while it's talking.
Each step keeps its own conversation on screen.

While Sārathi is working, a panel shows what it's doing and for how long, and input is
locked. Press **Cancel** or say "cancel" to drop the work and ask something else. STOP and
hazard words always get through.

For 15 seconds after each exchange, Sārathi treats whatever you say as part of the
conversation. After that, long sentences that aren't questions need its name, so nearby
conversations don't move your step. Hazard words always get through. Only your own words
can pass the safety gate, never the model's interpretation of them.

## How it stays grounded

Sārathi first looks for a saved guide in `procedures/`. Otherwise it searches the web, and
Gemma 4 turns those sources and your photos into steps. If two searches find nothing
useful, it offers cautious general advice rather than giving up. Every guide is labelled
on screen as a saved guide, built from web sources, or general advice, and you can open
the sources. Answers it isn't sure of say so out loud.

You can also change your mind mid-task. Say *"let's fix my refrigerator instead"*, and
Sārathi builds the new guide. If it can't, or you press Cancel, you stay on your old step.

| Job | Handled by |
|---|---|
| Which step you are on | Application code |
| Safety tiers, refusals and the emergency stop | Application code |
| Shop URLs | Application code, taken from search results only |
| Prices | Shown only if the exact text appears on the source page |
| Writing steps from sources and photos | Gemma 4 |
| Answering questions from the current guide | Gemma 4 |
| Checking a photo against a step | Gemma 4 vision |

Gemma can never invent a shop link: it picks results by source number, and the code
builds the link.

## Safety

Every job goes through one of three tiers, decided in code before the model is
involved.

| Tier | What happens | Examples |
|---|---|---|
| **Standard** | Spoken safety gate, confirmed before step 1 | Washing machine filter, flat-pack |
| **Caution** | Warning, then a deliberate "I understand the risk" | Phone screen or battery |
| **Refused** | Sārathi explains why and stops | Microwave faults, gas, mains wiring, damaged lithium batteries, brakes |
| **Refused: harm** | Refused by code patterns, then by the model for what patterns miss | Hurting people, hiding evidence, weapons, illegal drugs. Self-harm gets support details |

**During a task, say "stop", "smoke", "fire", "burning", "sparks", "shock" or "gas leak"**
and Sārathi stops immediately. A bare "stop" works at any time, and the red STOP button
is on every screen. Sārathi can never tell you that something is safe or unplugged. Replies
that claim this are filtered out.

AI steps can be wrong, so use your own judgement. If in doubt, call a qualified
technician.

## Saved guides

A guide is a JSON file in `procedures/`, so adding one needs no code. It holds a `match`
regular expression plus `title`, `safety`, `items`, `steps` and `sources`. Saved guides
load instantly, with no search or model call.

| Guide | Tier |
|---|---|
| Washing machine won't drain | Standard |
| Assemble a flat-pack bookcase | Standard |

## Running it

Requires Python 3.11 or newer.

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
cp .env.example .env
```

Add your keys to `.env`, never to `.env.example`, then run:

```bash
.venv/Scripts/python -m uvicorn main:app --port 8765
```

Open <http://localhost:8765>. Camera and microphone need HTTPS on a phone, so to test
on your own phone, run:

```bash
cloudflared tunnel --url http://localhost:8765
```

Run the tests with `.venv/Scripts/python -m pytest`.

### Environment

```
GEMINI_API_KEY=         # Gemma 4 through the Gemini API (required)
ELEVENLABS_API_KEY=     # text to speech (required)
TAVILY_API_KEY=         # web search (required)
GEMMA_MODEL=gemma-4-26b-a4b-it
ELEVENLABS_VOICE_ID=    # optional
ELEVENLABS_TTS_MODEL=eleven_flash_v2_5
SARATHI_REGION=Finland   # where to look for shops
```

## Why open weights matter

Sārathi uses Google's **Gemma 4**, an open-weight model. Today it runs through the
Gemini API. Open weights are what make a private, low-cost local version possible, so a
repair tool that sees inside your home doesn't have to depend on one provider.

## Honest limitations

- Local model hosting is planned, not built. Your speech and photos go to external
  services: the browser's speech service, the Gemini API, ElevenLabs and Tavily.
- Sārathi tries any task and describes any picture, but it can be wrong or unsure. General
  advice isn't specific to your model, so check it against your manual.
- It won't name real people from their faces, and dangerous jobs stay refused on purpose.
- HEIC photos open only in browsers that can decode them. Other browsers need JPG or PNG.
- Web-built plans can take 20 to 60 seconds.
- Saved guides are general, so your machine may differ. Check them against your manual.
- Commands are English only.
- Voice input uses the browser's Web Speech API, which works best in Chrome and gets
  worse in a loud room. Every command also has a button or the typed input.
- Photo checks can be wrong, so use your own judgement.

## Built with

- **Gemma 4** (`gemma-4-26b-a4b-it`): steps, answers and photo checks.
  [Model terms](https://ai.google.dev/gemma/docs)
- **ElevenLabs**: text to speech, with the browser's voice as a fallback.
- **Tavily**: web search.
- **FastAPI**, vanilla JS, no build step.

## License

MIT. See [LICENSE](LICENSE).
