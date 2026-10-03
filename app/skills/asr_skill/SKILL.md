# ASR Skill

## Responsibility

Transcribe English audio with Seed-ASR and report confidence and duration.

## Input / Output

Input: `{audio_url: str, duration_ms: int, fallback_text?: str}`.
Output: `ASRResult(transcript, confidence, duration_ms, provider)`.

## Dependencies

`httpx`, `SPEECH_API_KEY`, Seed-ASR 2.0 audio-file endpoint, and a provider-
reachable audio URL.

## Example

`await transcribe("https://bucket/file.webm", 4200)`

## Failure Fallback

Network, timeout, malformed provider response, or missing credentials returns a
clearly marked deterministic fallback result. It never fabricates a high
confidence score.
