# TTS Skill

## Responsibility

Create and cache Buddy speech with one verified American-English female voice.

## Input / Output

Input: `{text: str, speed: slow|normal|fast, voice?: en-US voice id}`.
Output: local playable URL or an empty string when browser speech fallback is
required.

## Dependencies

`httpx`, Seed-TTS 2.0, `SPEECH_API_KEY`, and writable `data/audio`.

## Example

`await synthesize("Tell me about your day!", "normal")`

## Failure Fallback

Missing service access or a provider error returns an empty URL so the UI uses
the Web Speech API with `en-US`. A non-US voice fails immediately and never
falls back to another accent.
