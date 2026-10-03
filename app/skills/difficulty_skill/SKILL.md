# Difficulty Skill

## Responsibility

Turn recent score averages into a supportive difficulty and speed recommendation.

## Input / Output

Input: list of recent 0-100 turn averages. Output: `DifficultyAdvice` with
difficulty, speed, rolling average, level-up invitation, and recovery flag.

## Dependencies

No provider dependency.

## Example

`recommend([72, 81, 88])`

## Failure Fallback

An empty score list recommends Medium and Normal. Difficulty changes remain
recommendations; the caller must request learner confirmation.
