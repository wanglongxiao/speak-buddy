# Topic Creation Prompt

The child wants to practice: {{raw_text}}.
Selected difficulty: {{difficulty}}.

Generate a topic card in strict JSON:

```json
{
  "title": "string",
  "difficulty": "easy|normal|hard|expert",
  "starter_question": "string",
  "follow_up_hints": ["five strings"],
  "ideal_answer_sample": "string",
  "suggested_new_words": ["three to five strings"]
}
```

Keep the topic within middle-school daily life, study, hobbies, friendships, or
age-appropriate discussion. The starter question must be warm and specific.
Use these difficulty rules:
- easy: 6-10 words per prompt, common A2 vocabulary
- normal: 10-16 words per prompt, everyday B1 vocabulary
- hard: 15-22 words per prompt, richer B1-B2 vocabulary
- expert: 20-30 words per prompt, precise B2 vocabulary and comparison

Content must be safe and suitable for a 12-year-old.
