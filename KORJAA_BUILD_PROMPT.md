# Build prompt for Claude Code: Korjaa

Paste everything below into Claude Code as your opening message.

---

Build a web app called **Korjaa** (Finnish for "repair") in this folder. It is a
hands-free, voice-guided repair and assembly assistant for a phone browser. It is
for a hackathon with a hard deadline today at **20:00 Helsinki time**, so scope
discipline matters more than completeness. Feature freeze at 19:00. Everything
after that is testing, the backup video and submission.

`README.md` already exists in this folder. Use it as given, and update it only if
what you build differs from what it says. It must never claim something that
does not work.

## The situation it is built for

A person is lying on the floor behind a washing machine, or sitting in a pile of
flat-pack parts. Their hands are dirty and busy. They cannot scrub through a
YouTube video or tap a screen. They talk to the app; it talks back, one step at a
time, and it can look at what they are holding through the camera.

## Core architecture: read this before writing code

This is **not a chatbot**. It is a **state machine that walks through a stored
procedure**, with a language model handling only the conversation around it.

Procedures are structured JSON files on disk. The model NEVER invents repair
steps. This is a safety requirement: an improvised instruction about a
mains-powered appliance can hurt someone.

| Job | Who does it |
|---|---|
| Deciding the repair steps | The JSON procedure file |
| Tracking which step we are on | Application code |
| Hazard stop, refusal and caution checks | Application code, never the model |
| Matching a spoken symptom to a procedure | Gemma 4 |
| Looking at a photo and confirming the part | Gemma 4 vision |
| Rephrasing a step when the user is stuck | Gemma 4, using only that step's `say` and `detail` |
| Interpreting "next" / "repeat" / "stuck" | Application code first, Gemma as fallback |

The rule for the README and the pitch: **the model handles language, the code
handles facts.**

## Tech stack

- **Backend:** Python + FastAPI. Serves the frontend and procedure files, and
  proxies all model and voice calls.
- **Frontend:** ONE `index.html` with vanilla JS. No build step, no framework.
- **LLM, primary path:** Gemma 4 through the Gemini API, model `gemma-4-31b-it`.
  Vision calls use the same model with an image. This path is required for the
  Gemma 4 prize category and is the default.
- **LLM, local path:** `gemma4:e4b` through Ollama at `http://localhost:11434`
  (about 9.6 GB). Both backends sit behind ONE interface in `models.py`. Selected
  with `KORJAA_BACKEND=gemini|ollama`. Do not fail over automatically: never move
  a user's data between providers without them choosing it.
- **Voice out:** ElevenLabs text-to-speech, streamed. Pick a low-latency model
  and check its ID in the current ElevenLabs docs. Cache generated audio on disk
  by a hash of text and voice, and add a script that pre-generates every `say`,
  `detail` and safety line, so the demo survives bad Wi-Fi and saves credits.
- **Voice in:** Web Speech API (`webkitSpeechRecognition`) for short commands.
  ElevenLabs Scribe for the longer free-text symptom description.

**All API keys stay server-side.** The browser never sees a key. Keep `.env` in
`.gitignore` and check that before the first commit. Never print keys in logs.

Verify model IDs against the live API at startup. If one is unavailable, print
a clear error naming the model and the fix.

## Browser gotchas: handle these from the start

1. **Camera and microphone need HTTPS on a phone.** Use
   `cloudflared tunnel --url http://localhost:8000` and put the exact command in
   the README. Test on a real phone by stage 6, not at 19:00.
2. **iOS Safari blocks audio until a user gesture.** Create and unlock the
   `AudioContext` in the first tap handler, before any speech plays.
3. **The screen sleeps mid-repair.** Request `navigator.wakeLock` when a procedure
   starts, release it at the end, and re-request it on `visibilitychange`.
4. **The app can hear itself.** Pause speech recognition while Korjaa is speaking,
   then resume it, or its own voice will trigger commands.
5. **Web Speech API is not available everywhere.** Detect support. If it is
   missing, record short clips and send them to Scribe. Buttons always work.

## Hands-free is the product

During a procedure the microphone listens continuously, so the user never has to
touch the screen. The start screen uses one large tap to begin (needed for the
audio and microphone permissions). A listening indicator is always visible. The
microphone stops when a procedure ends.

The camera captures **single photos on request**, never continuous video. Saying
"is this it" shows the live preview and speaks a three-second countdown, then
takes one photo. Do not store photos or audio on disk. Tell the user once, at the
start, that photos and voice are processed by the selected AI services.

## Procedure file format

Store in `procedures/*.json`. This schema is the contract and the thing outside
contributors will add to. Validate every file at startup and refuse to start if
one is invalid.

```json
{
  "id": "washing-machine-wont-drain",
  "category": "appliance-repair",
  "title": "Washing machine won't drain",
  "risk": "standard",
  "symptoms": ["won't drain", "full of water", "water still inside", "standing water", "won't empty"],
  "difficulty": "easy",
  "time_minutes": 20,
  "tools": ["shallow tray", "towel", "flat screwdriver"],
  "safety": [
    "Unplug the machine at the wall before you start.",
    "If it just ran a hot wash, wait until the water has cooled.",
    "Have a towel and a shallow tray ready. Water will come out."
  ],
  "steps": [
    {
      "say": "Open the small hatch at the bottom front of the machine.",
      "detail": "It's a square panel near the floor, usually in the left or right corner. It may pop open with a fingernail or need a flat screwdriver in the slot.",
      "expect": "a small door, then a round cap with a handle behind it",
      "vision_check": "Is this a drain pump filter cap: a round plastic cap, often blue or grey, with a raised grip, set into a recess at the bottom front of a washing machine?"
    }
  ],
  "sources": ["Where these steps came from"]
}
```

- `risk`: `standard` or `caution`.
- `say`: spoken verbatim. Short. One instruction. Written for the ear.
- `detail`: spoken on "stuck" or "I don't understand".
- `expect`: what they should be seeing, used to reassure.
- `vision_check`: passed to Gemma 4 vision on "is this it?". Optional per step.
- `caution`: required when `risk` is `caution`, with `hazards` (list), `skill`
  (one sentence), and `stop_if` (list).
- `sources`: required. Never present a procedure as verified by a professional.

## Procedures to ship

1. `washing-machine-wont-drain`: the hero. Drain pump filter. Include clearing the
   filter, refitting it firmly and a leak check before plugging back in.
2. `flatpack-shelf-assembly`: demo insurance, needs no appliance. Include a step
   whose `vision_check` identifies **which fastener is which** from a photo of
   several, and end with anchoring the shelf to the wall if it is meant to be.
3. `vacuum-lost-suction`: a second appliance, proving nothing is hard-coded.
4. `phone-screen-battery-prep`: `risk: caution`. Cut this first if time runs out.
   It covers preparation and safety only: back up data, discharge below 25%,
   check for a swollen battery, clear a non-flammable work surface, use no metal
   tools near the battery, and find the guide for the exact phone model. It says
   plainly that opening steps differ per model, so Korjaa does not guide them. It
   ends with taking the old battery to a battery collection point.

## Safety system: three risk tiers

All checks here run in code, BEFORE procedure matching, and cannot be overridden
by the model. Implement them in `safety.py`.

| Tier | Example | What happens |
|---|---|---|
| **Standard** | Washing machine filter, flat-pack, vacuum | Safety gate, then steps |
| **Caution** | Phone screen or battery | Expertise warning, deliberate confirmation, safety gate, then steps |
| **Refused** | Microwave, gas, mains wiring | Refuse with the reason and stop |

**Safety gate (all procedures).** Before step 1, speak every item in `safety[]` and
wait for spoken confirmation or a button press. It cannot be skipped.

**Caution warning.** Before the safety gate, speak the hazards, the skill needed
and the `stop_if` conditions. Example: "This job means working next to a lithium
battery. A punctured battery can catch fire. It needs patience and steady hands.
Stop at once if the battery looks swollen. If you are comfortable with that, say
'I understand the risk'. Otherwise, a repair shop is the safer choice." Show the
same warning on screen in amber.

- Only the exact phrase, or a separate button, continues. "Next", "okay" and "yes"
  do not.
- The default is to not continue. Silence or anything else ends the procedure and
  suggests a repair shop.
- A caution task with no stored procedure gets the warning, then: "I don't have
  verified steps for this." The model never fills the gap.

**Refusal list.** `REFUSALS` in `safety.py`, each with a plain-language reason:
- Microwave ovens: "The capacitor inside can hold a lethal charge even when
  unplugged. This one needs a qualified technician."
- Gas appliances or connections.
- Mains wiring, fuse boxes and control boards.
- Swollen, leaking, hot or damaged lithium batteries: "Don't charge it, puncture
  it or keep working on it. Move it away from anything flammable if it is safe to
  do so, and take it to a battery collection point or repair shop."

If the spoken symptom matches a refusal, refuse and stop. Offer no workaround.

**Emergency stop.** At any point, including mid-step, "stop", "smoke", "fire",
"burning", "spark", "shock" or "gas" immediately stops the procedure and speaks a
fixed line: move away, unplug only if it is safe, and call 112 if anyone is in
danger or there is fire. Keep a permanent red STOP button on screen. Matched in
code, spoken from a pre-generated clip, and it must work offline.

**Vision limits.** A vision answer is `yes`, `no` or `unsure`, returned as JSON.
Treat `unsure`, or anything unparseable, as a request for a clearer photo. Vision
can only confirm a part. It can never say something is safe, unplugged or
de-energised, and it can never advance a step on its own.

**Nothing outside the procedures.** If asked something outside a stored procedure,
say so plainly. Do not generate an answer.

Add `tests/test_safety.py` covering each refusal, the caution phrase, and the
emergency stop, including that "okay" cannot pass the caution warning.

## Interaction model

Matched in code before falling back to the model:
- "next" / "done" / "okay": advance
- "repeat" / "again" / "what": replay the current `say`
- "stuck" / "I don't understand" / "help": speak `detail`, and if still stuck,
  let Gemma rephrase using that step's text only
- "back": previous step
- "is this it" / "what is this": camera check against the current step
- "stop": emergency stop

Every voice command has an on-screen button. A noisy demo room must not break the
demo.

## UI

Phone-first, large touch targets, high contrast, dark background. Show the current
step in large text, the step counter ("3 of 7"), a listening indicator, a camera
button, Next / Repeat / Stuck / Back buttons, and the red STOP button. Nothing
else. Amber styling is for caution warnings only.

## Build order: follow this exactly

Each stage must run before the next starts. Commit after each stage.

1. Repo skeleton, `LICENSE` (MIT), `.gitignore`, `.env.example`, FastAPI serving
   `index.html`, startup key checks.
2. Procedure loader, schema validation, and procedures 1 to 3 written in full.
3. Text-only state machine: typed symptom, matched procedure, typed "next". Build
   `safety.py` and its tests here, because they sit in front of matching. **Then
   stop and tell me, so I can test it before you add voice.**
4. `models.py` with the Gemini backend. Symptom matching through Gemma 4.
5. ElevenLabs TTS with caching. Audio unlock on first tap.
6. Web Speech API commands, echo protection, hands-free listening, and the
   Cloudflare tunnel. **Test on a real phone here.**
7. Camera, Gemma 4 vision, spoken `vision_check` answer.
8. Procedure 4 and the caution warning flow in the UI.
9. Ollama backend, wake lock, pre-generated audio, final phone test.

**If time runs short, cut in this order:** Ollama backend, then procedure 4, then
procedure 3, then vision check. If the Ollama backend is cut, remove it from the
README too. **Never cut** the state machine, safety gate, caution warning, refusal
list or emergency stop. If procedure 4 is cut, the caution warning still runs for
phone tasks and ends in "I don't have verified steps for this."

## Deliverables

- App runnable with `uvicorn main:app`
- `README.md` kept accurate, naming `gemma-4-31b-it`, linking the model's license
  or terms, and listing key dependencies
- `.env.example` listing `GEMINI_API_KEY`, `ELEVENLABS_API_KEY`, `KORJAA_BACKEND`
- `LICENSE` (MIT) and `requirements.txt`
- `CONTRIBUTING.md`: how to add a procedure JSON file, including sources, risk tier
  and review expectations. Procedures that touch safety need a reviewer.

## Rules while building

- No TODOs or stub functions in committed code. If it is not built, it is not
  referenced.
- Print clear startup errors for missing keys and models.
- Keep `index.html` under about 600 lines.
- Do not create the GitHub repo or push until I say so. I must check that no secret
  is in the history first.
- Label the procedures as community-written guidance, not manufacturer instructions.

Start with stage 1. Tell me when the text-only state machine in stage 3 runs.
