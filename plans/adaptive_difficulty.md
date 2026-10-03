# Adaptive Difficulty

## Inputs

Use the mean of pronunciation, fluency, vocabulary, and confidence for the last
10 completed turns.

## Recommendation

- Below 60: Easy and Slow.
- 60-79: Normal difficulty and Normal speed.
- 80-91: Hard difficulty and Normal speed.
- 92 or above: Expert difficulty and Normal speed.

The selected level controls prompt length and vocabulary:

- Easy: 6-10 words, common A2 vocabulary.
- Normal: 10-16 words, everyday B1 vocabulary.
- Hard: 15-22 words, richer B1-B2 vocabulary.
- Expert: 20-30 words, precise B2 vocabulary and viewpoint comparison.

All levels stay within middle-school daily life, learning, friendships,
hobbies, and age-appropriate discussion.

After three consecutive turn averages of at least 85, invite the learner to
level up. Never change the selected level without confirmation. Never
automatically lower a learner's saved level; frame a temporary easier question
as a supportive option.

## Frustration Recovery

After two turn averages below 50, simplify the next question and say: "Let's
take it easy - I love hearing your voice no matter what."

## Interface

`recommend(scores) -> DifficultyAdvice` keeps this policy independent of the UI
and future scoring engines.
