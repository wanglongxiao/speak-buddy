# Pronunciation Skill

## Responsibility

Score echo practice with word-sequence similarity and ASR confidence while
avoiding unsupported phoneme claims.

## Input / Output

Input: reference text, ASR hypothesis, confidence 0-1. Output:
`PronunciationResult` with score, components, feedback, and Echo Bonus flag.

## Dependencies

Python `difflib`; upstream ASR result.

## Example

`grade("I loved the view", "I love the view", 0.9)`

## Failure Fallback

Empty hypotheses receive only the confidence component and encouraging replay
feedback. No XP is removed.
