# Gamify Skill

## Responsibility

Calculate XP, title transitions, and event-driven badge candidates without
subtracting rewards.

## Input / Output

Input: event name and numeric/boolean context. Output: `Reward(xp, title,
badges, celebration)`.

## Dependencies

The persistence caller enforces badge idempotency with `BadgeAward`.

## Example

`evaluate("echo", {"score": 88, "total_xp": 295})`

## Failure Fallback

Unknown events award zero XP and preserve the current title. Missing context
uses conservative zero values.
