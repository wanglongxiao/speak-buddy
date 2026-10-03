# Loud Skill

## Responsibility

Validate browser RMS and duration, optionally measure PCM WAV locally, and count
active speaking seconds.

## Input / Output

Input: normalized RMS, duration milliseconds, and optional WAV path. Output:
`LoudResult(rms, duration_ms, counted_seconds, is_quiet)`.

## Dependencies

Python standard-library `wave`; browser Web Audio supplies RMS for WebM audio.

## Example

`assess(0.08, 4200)`

## Failure Fallback

Unknown or unmeasurable volume counts zero loud seconds but is not labeled quiet
and never penalizes the learner.
