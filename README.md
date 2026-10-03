# SpeakBuddy

SpeakBuddy is an AI-powered English speaking practice app that helps students
build confidence with authentic American accent coaching and humane,
personalized exercises. Its mobile-first learning experience combines
conversation topics, read-aloud practice, encouraging feedback, pronunciation
and fluency scoring, progress tracking, rewards, and student/parent performance
dashboards.

Designed for secondary-school learners, SpeakBuddy uses a warm American-English
Buddy voice and gives one focused correction at a time. Practice difficulty and
daily content adapt across learner profiles while each child's history, scores,
XP, badges, and dashboard remain isolated.

## Stack

- Python 3.11, FastAPI, Uvicorn, Pydantic v2, SQLModel, SQLite
- Jinja2, HTMX, Alpine.js, Tailwind CDN, Chart.js
- BytePlus ModelArk, Seed-ASR, Seed-TTS, and TOS
- Local deterministic AI/audio fallback for development and provider outages

## Run

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Open <http://localhost:8000>. Microphone capture requires localhost or HTTPS.

The repository also supports the user's preferred `uv` workflow:

```bash
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
uv run uvicorn app.main:app --reload --port 8000
```

## Configuration

Set `MOCK_AI=true` for a fully local demo. With `MOCK_AI=false`, the app uses:

- `SESSION_SECRET`, a long random value used to sign account and parent-share cookies
- `MODELARK_API_KEY`, `MODELARK_BASE_URL`, `MAIN_AGENT_ENDPOINT`
- `SPEECH_API_KEY`, Seed-ASR/TTS URLs and resource IDs
- `BYTEPLUS_TTS_VOICE`, which must be a verified `en-US` voice ID
- BytePlus AK/SK, region, endpoint, and public-readable TOS bucket

The app fails at startup if the configured voice is not `en-US`. Provider
errors fall back locally, but never switch to a British or non-English voice.
TOS should enforce a seven-day lifecycle policy in the BytePlus console.

## Flow

1. `/practice` redirects to the three-line voice warm-up.
2. Each turn records audio, stores it, counts loud time, transcribes it, asks
   Buddy for strict JSON coaching, and synthesizes the response.
3. The learner echoes the ideal rephrase and collects new words.
4. Five turns finish the quest and award completion XP and badges.
5. `/progress/parent` provides a print-friendly summary and share QR code.

Anonymous visitors share one guest profile. `/account` can create and switch
password-protected learner profiles; practice history, XP, topics, trophies, and
progress stay scoped to the active profile. Difficulty defaults to Normal and
supports Easy, Normal, Hard, and Expert. `/progress` and the signed parent view
provide day, week, and month summaries with an encouraging speaking evaluation.

## Tests and Quality

```bash
pytest
ruff check .
black --check app tests
```

The skill tests cover a happy path and fallback behavior for ASR, TTS, Coach,
Topics, Difficulty, Gamification, Loud Meter, Pronunciation, and TOS.

## Manual Acceptance

- [ ] iPhone Safari completes Warm-up and a five-turn Quest.
- [ ] Android Chrome shows a clear microphone permission flow.
- [ ] Chrome at 375px and 1280px has no clipping or overlap.
- [ ] English and Chinese UI strings render without omissions.
- [ ] Missing TOS access falls back to `data/audio`.
- [ ] TTS is the same American female voice at all three speeds.
- [ ] 300 total XP promotes the learner to Chatty Robin.
- [ ] 300 daily loud seconds shows Loud Legend and awards the badge.
- [ ] An echo score of at least 80 awards the Echo Bonus.

## Structure

`app/skills/*/SKILL.md` documents each stable capability boundary. Editable LLM
prompts and product decisions live in `plans/`; runtime code loads prompts from
there so coaching can be tuned without embedding policy inside service code.
