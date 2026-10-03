# Coach Skill

## Responsibility

Turn one learner transcript into concise, validated, encouraging coaching with
one correction, an echo line, scores, XP, and vocabulary.

## Input / Output

Input: question, transcript, ASR confidence, and recent turn history.
Output: strict Pydantic `CoachResult`.

## Dependencies

ModelArk OpenAI-compatible API, `MAIN_AGENT_ENDPOINT`, and
`plans/coach_prompt.md`.

## Example

`await coach(question, transcript, 0.84, history)`

## Failure Fallback

Invalid JSON, schema failure, missing credentials, and provider errors return a
deterministic coach result. Fallback confidence is conservative and still
quotes the learner's own words.
