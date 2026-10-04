# SpeakBuddy

**Demo Site:** [https://sg2fo9jdgkvomc1ncqdqv.apigateway-ap-southeast-1.apigw-byteplus.com/](https://sg2fo9jdgkvomc1ncqdqv.apigateway-ap-southeast-1.apigw-byteplus.com/)

SpeakBuddy is an AI-powered English speaking practice app for secondary-school
learners. It helps children speak more often, build confidence, and improve
fluency through short daily conversations, read-aloud exercises, encouraging
feedback, and a consistent American-English Buddy voice.

The experience is mobile-first and designed to feel supportive rather than
exam-like. Buddy celebrates what the learner did well, gives one focused
improvement at a time, suggests a stronger version of the answer, and introduces
useful new words without interrupting the conversation with too many
corrections.

## How SpeakBuddy Helps

### For Learners

- **Low-pressure speaking practice:** children can speak about familiar school,
  friendship, travel, hobbies, family, and everyday-life topics.
- **Confidence before correction:** every response starts with positive,
  specific encouragement.
- **Focused coaching:** Buddy highlights one small improvement instead of
  correcting every mistake at once.
- **Read-aloud training:** daily sentences help learners practise rhythm,
  clarity, pronunciation, and sentence length.
- **Adaptive difficulty:** Easy, Normal, Hard, and Expert levels adjust
  vocabulary, question depth, and sentence complexity.
- **Fresh daily content:** AI-generated topics and read-aloud material are
  refreshed regularly and separated by learner profile.
- **Visible progress:** XP, streaks, speaking time, scores, trophies, and badges
  make consistent practice easier to maintain.

### For Parents and Guardians

- Review daily, weekly, and monthly speaking activity.
- Track fluency, response length, word accuracy, pronunciation, and relevance.
- Read encouraging progress summaries instead of isolated test scores.
- Compare improvement over time through charts and practice history.
- Open a signed, shareable parent view with a QR code.
- Keep each child's account, practice history, topics, scores, XP, and badges
  isolated from other learner profiles.

## Main Pages and Features

| Page | Purpose |
| --- | --- |
| **Home** (`/`) | Shows today's practice, XP, streak, and speaking time. Starting the quest selects a random unfinished topic for the day. |
| **Read Aloud** (`/warmup`) | Provides daily sentences for pronunciation, fluency, and confidence practice. Results are grouped so children can practise naturally before receiving feedback. |
| **Topics** (`/topics`) | Lists AI-generated conversation topics and supports creating a custom topic by voice. |
| **Topic Practice** (`/practice`) | Opens directly on the selected topic, streams the first question automatically, and listens for an interruptible spoken reply. Each completed topic receives a five-dimension evaluation. |
| **Progress** (`/progress`) | Displays day, week, and month summaries, score trends, speaking activity, and an encouraging overall evaluation. |
| **Parent View** (`/progress/parent`) | Provides a signed, print-friendly learning summary and share QR code for parents or guardians. |
| **History** (`/history`) | Shows previous speaking turns, questions, transcripts, and coaching results for the active learner. |
| **Trophies** (`/trophy`) | Displays earned and locked badges that reward practice consistency and speaking milestones. |
| **Account and Settings** (`/account`, `/settings`) | Manages learner accounts, language, difficulty, speaking speed, nickname, and Buddy voice preferences. |

## BytePlus Services

SpeakBuddy uses the following BytePlus services in its production AI and cloud
workflow:

| BytePlus Service | How SpeakBuddy Uses It |
| --- | --- |
| **ModelArk with DeepSeek V4.1 Flash** | Generates daily conversation topics and read-aloud content, creates custom topics from voice commands, and powers Buddy's structured coaching response. |
| **Seed Speech ASR** | Streams topic-practice audio into English text with uploaded-recording fallback and confidence data for coaching and scoring. |
| **Seed Speech TTS** | Streams Buddy's replies and prompts at learner-selected speaking speeds with six selectable English voices. |
| **TOS Object Storage** | Stores uploaded recordings and generated TTS audio. Production objects can use a seven-day lifecycle policy for automatic cleanup. |
| **veFaaS** | Runs the FastAPI application as a cloud function with a minimum of one and a maximum of two instances. |
| **BytePlus API Gateway** | Exposes the veFaaS application through the public HTTPS Demo Site URL and routes browser traffic to the production function. |

API keys, access keys, secrets, and model endpoint IDs are supplied only through
server-side environment variables. They are never embedded in frontend code or
committed to the repository.

## Speaking Flow

1. Starting today's quest selects a random unfinished topic. Learners can also
   select or create a topic themselves.
2. The selected topic opens immediately and streams Buddy's first question.
3. The browser begins streaming the learner's reply and stops Buddy when the
   learner interrupts.
4. Seed Speech ASR transcribes the live audio, with uploaded recordings as a
   browser fallback.
5. DeepSeek on ModelArk returns structured coaching with praise, one focused
   adjustment, a stronger rephrasing, suggested words, and scoring data.
6. Seed Speech TTS reads Buddy's response aloud.
7. After the topic is complete, the app saves the evaluation and updates
   progress, XP, streaks, and badges.

Read-aloud mode follows a separate flow and evaluates practice in groups of ten
sentences.

## Technology Stack

- Python 3.11 locally and Python 3.9-compatible production packages
- FastAPI, Uvicorn, Pydantic v2, SQLModel, and SQLite
- Jinja2, HTMX, Alpine.js, Tailwind CDN, Chart.js, and Lucide icons
- BytePlus ModelArk, Seed Speech ASR/TTS, TOS, veFaaS, and API Gateway
- Local deterministic AI and audio fallbacks for development or provider
  outages

## Run Locally

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000). Microphone capture requires
localhost or HTTPS.

The repository also supports `uv`:

```bash
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
uv run uvicorn app.main:app --reload --port 8000
```

## Configuration

Set `MOCK_AI=true` for a fully local demo. With `MOCK_AI=false`, configure:

- `SESSION_SECRET`, a long random value used to sign account and parent-share
  cookies
- `MODELARK_API_KEY`, `MODELARK_BASE_URL`, and `MAIN_AGENT_ENDPOINT`
- `SPEECH_API_KEY`, Seed Speech ASR/TTS URLs, and resource IDs
- `BYTEPLUS_TTS_VOICE`, which must be one of the verified English Buddy voice
  IDs
- BytePlus AK/SK, region, endpoint, and a public-readable TOS bucket
- `APP_BASE_URL` with the externally accessible HTTPS application URL

The app rejects a production configuration that uses the default session
secret. It also rejects unverified Buddy voices. Provider errors can fall back
locally, but the app does not switch to a non-English voice. Configure a
seven-day lifecycle policy for the TOS bucket in the BytePlus console.

## Accounts and Data

Anonymous visitors use a shared guest profile. `/account` can create and switch
password-protected learner accounts. Practice history, generated content,
scores, XP, trophies, and progress are scoped to the active profile.

The current deployment uses instance-local SQLite. This is suitable for the
single-reserved-instance operating mode, but strict state consistency during
multi-instance scaling or rolling releases requires an external shared
database.

## Tests and Quality

```bash
pytest
ruff check app
black --check app tests
```

The test suite covers application routes, account and profile isolation, daily
content releases, grouped scoring, ASR, TTS, AI coaching, topics, difficulty,
gamification, loud-time tracking, pronunciation, and TOS fallback behavior.

## Project Structure

- `app/routers/` contains page and API routes.
- `app/services/` contains content, evaluation, authentication, and progress
  workflows.
- `app/skills/` contains stable AI, speech, storage, scoring, and gamification
  capability boundaries.
- `app/templates/` and `app/static/` contain the server-rendered mobile-first
  interface.
- `plans/` contains editable prompts and product decisions used by the runtime.
