# Pronunciation Grading

## MVP Formula

1. Normalize the reference and ASR hypothesis to lowercase word tokens.
2. Compute word sequence similarity with `difflib.SequenceMatcher`.
3. Calculate `round(100 * (0.6 * word_match + 0.4 * asr_confidence))`.

## Feedback

- 80-100: green star celebration and +5 Echo Bonus.
- 60-79: "Almost! One more try?"
- Below 60: encouragement only, then replay the model pronunciation.

No points are removed. A low ASR confidence must not be presented as proof of a
pronunciation problem.

## Stable Interface

`grade(reference, hypothesis, confidence) -> PronunciationResult` stays stable
when a phoneme-level provider is added later.
