# Loud-First Design

## Measurement

The browser calculates RMS while recording and sends RMS plus duration with the
audio. The server rejects impossible values, counts seconds only above the
configurable quiet threshold, and stores daily totals in `LoudMeter`.

## Required Touchpoints

- Quest gate: three escalating warm-up lines, Buddy demo audio, hold-to-record,
  live RMS bar, and +5 XP when complete.
- Every turn: short/quiet speech sets `encourage_loud`; Buddy offers an echo of
  the ideal rephrase and awards +5 XP at score 80.
- Word cards: selecting a word plays it and opens an immediate repeat action.
- Shout-Out Corner: optional practice counts toward loud time and grants Daily
  Shouter at 10 lines.
- Header: today's counted seconds remain visible.
- At 300 seconds: show Loud Legend celebration and award the badge once.
- Topic, difficulty, and quest start accept short voice commands with visible
  button fallbacks.

## Emotional Guardrail

Two consecutive quiet turns suspend volume pressure and use the gentle voice
variant: "It's okay to be quiet today. Even a whisper is brave. 💛"

## Privacy and Failure

Raw browser amplitude is never used for identity or health inference. Missing
RMS is measured server-side when WAV data is available; otherwise it is marked
unknown and no penalty is applied. Upload failure queues the Blob in IndexedDB
through the browser's local retry store.
