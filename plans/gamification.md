# Gamification

## XP

| Event | XP |
| --- | ---: |
| Coach turn | 10-30 |
| Echo score >= 80 | 5 |
| Warm-up complete | 5 |
| Daily Shouter | 20 |
| Quest complete | 20 |
| Streak day | 5, capped at 50/day |

## Titles

Little Sprout 0; Chatty Robin 300; Brave Lioness 1000; Story Weaver 2500;
Golden Voice 6000; Legendary Speaker 12000.

## Badges

First Flight, 7-Day Streak, Loud & Proud, Word Collector, Topic Creator,
Challenger, Early Bird, Weekend Warrior, Perfect Score, Comeback Kid, Echo
Master, Loud Legend, and Daily Shouter.

## Feedback Rules

- Reward effort immediately; do not subtract XP.
- Use motion for a new event, not as permanent decoration.
- Badge unlock: centered badge, short sound, and `navigator.vibrate(150)`.
- Three confident turns create an on-fire streak.
- Early exit preserves all earned XP and uses a pressure-free message.

## Trigger Contract

`gamify_skill.evaluate(event, context)` returns awarded XP, newly earned badge
codes, current title, and optional celebration. Badge awards are idempotent.
