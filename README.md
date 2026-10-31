# Korjaa

**A hands-free, voice-guided repair assistant that runs in your phone browser.**

You are lying on the floor behind a washing machine. Your hands are wet and busy.
You cannot scrub through a 22-minute video to find the 40 seconds that matter. So
you talk to Korjaa, and it talks back: one step at a time, waiting for you,
repeating itself without complaint, and checking a photo to confirm you have the
right part.

Built at the Hacktoberfest Hack Day Mikkeli, hosted by Hacklab Mikkeli ry.

## The problem

A washing machine that will not drain often has a blocked filter. The usual fix
takes a towel and twenty minutes. A vacuum that has lost suction often has a
clogged filter or hose.

People throw these machines away.

Electronic waste is among the fastest-growing waste streams in the world, and much
of it can be repaired. At the moment you are on the floor with your hands inside
the machine, there is no easy way to get the one instruction you need.

Written manuals assume you can read while working. Videos assume you have a free
hand. Neither can look at what you are holding and say whether it is the right
part.

## What Korjaa does

1. You describe the symptom out loud: *"my washing machine won't drain."*
2. It speaks the safety steps and waits for you to confirm.
3. It walks you through the job, one spoken step at a time.
4. You say **"next"**, **"repeat"** or **"stuck"**, and your hands stay on the work.
5. You ask *"is this it?"*, and it takes one photo and checks the part.

## Why open weights matter here

Korjaa uses Google's **Gemma 4**: `gemma-4-31b-it` through the Gemini API by
default, and `gemma4:e4b` through Ollama for the local path.

**Your home stays yours, if you choose.** A repair assistant sees the inside of
your home and hears your voice. The default Gemini API path sends your photos and
speech to external services, because it is faster and works on any phone. An
open-weight model means you are not locked into that: you can run the model on
your own hardware instead.

**The cost can fall towards zero.** The goal is to keep machines out of landfill,
and a repair tool stops helping when people must pay per repair. The hosted demo
uses paid APIs, but open weights leave a path to a local version with no per-call
model cost.

**The knowledge can be inspected.** These instructions tell people to put their
hands inside machines. The steps live in readable JSON files in this repository,
not inside a model's weights, so anyone can audit, correct or translate them.

## Architecture: the model handles language, the code handles facts

Korjaa is a state machine walking through a stored procedure. It is not a chatbot
that improvises repairs.

```
procedures/*.json  -->  state machine  -->  spoken step
                            ^    |
                            |    v
                    voice commands / camera
                            |
                            v
                   Gemma 4 (language + vision)
```

| Job | Handled by |
|---|---|
| The repair steps | JSON procedure files |
| Which step you are on | Application code |
| Safety checks and refusals | Application code |
| Matching your symptom to a procedure | Gemma 4 |
| Checking your photo against a part | Gemma 4 vision |
| Rephrasing a stored step when you are stuck | Gemma 4 |

**The model never invents a repair step.**

## Safety

Every job goes through one of three tiers, decided in code before the model is
involved.

| Tier | What happens | Examples |
|---|---|---|
| **Standard** | Spoken safety gate, confirmed before step 1 | Washing machine filter, flat-pack, vacuum |
| **Caution** | Expertise warning, then a deliberate "I understand the risk" | Phone screen or battery |
| **Refused** | Korjaa explains why and stops | Microwaves, gas, mains wiring, damaged lithium batteries |

A caution warning respects your choice but tells you the risk first. For phones,
Korjaa covers preparation and safety only, because opening steps differ per model.

**Say "stop", "smoke", "fire", "burning", "spark", "shock" or "gas" at any time** and
Korjaa stops immediately, with a red STOP button always on screen. Korjaa's photo
check can confirm a part, but it can never tell you something is safe or unplugged.

Procedures are community-written guidance, not manufacturer instructions. You are
responsible for your own safety. If in doubt, call a qualified technician.

## The procedure library is the contribution surface

A repair is a JSON file, and adding one is a pull request with no code required.
One repository cannot know every appliance in the world, but the people who do can
add to it. See [CONTRIBUTING.md](CONTRIBUTING.md).

| Procedure | Category | Risk |
|---|---|---|
| Washing machine won't drain | appliance-repair | Standard |
| Flat-pack shelf assembly | assembly | Standard |
| Vacuum lost suction | appliance-repair | Standard |
| Phone screen or battery preparation | electronics | Caution |

## Running it

```bash
git clone <this repo>
cd korjaa
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload
```

Add your keys to `.env`. Camera and microphone need HTTPS on a phone, so to test
from your own phone, run:

```bash
cloudflared tunnel --url http://localhost:8000
```

Then open the generated HTTPS URL on the phone.

### Environment

```
GEMINI_API_KEY=        # Gemma 4 through the Gemini API
ELEVENLABS_API_KEY=    # speech
KORJAA_BACKEND=gemini  # or ollama
```

### Optional local model

```bash
ollama pull gemma4:e4b
```

Set `KORJAA_BACKEND=ollama` to use it. The download is about 9.6 GB. ElevenLabs
speech still needs the internet, so this keeps model calls local but is not fully
offline.

## Honest limitations

- The default path sends your speech and photos to external services.
- Four procedures demonstrate a format. They are not a full repair manual.
- Photo checks can be wrong, so use your own judgement.
- Voice recognition gets worse in a loud room, so every command has a button.

## Built with

- **Gemma 4** (`gemma-4-31b-it`, `gemma4:e4b`): open-weight model from Google
  DeepMind, used for symptom matching, photo checks and rephrasing.
  [Model terms](https://ai.google.dev/gemma/docs)
- **ElevenLabs**: speech and transcription. Voice is the main interface because
  your hands are busy.
- **FastAPI**, vanilla JS, no build step.

## License

MIT. See [LICENSE](LICENSE).
