# Topic Skill

## Responsibility

Create a child-safe B2-or-lower topic card from spoken intent and map supported
voice phrases to navigation or difficulty intents.

## Input / Output

Input: raw transcript string. Output: `TopicCard`; command matching returns
`(intent, slots)`.

## Dependencies

ModelArk through the same main endpoint as the coach.

## Example

`await create_topic("I want to talk about making music")`

## Failure Fallback

Missing AI access or invalid JSON creates a complete topic card directly from
the learner's phrase. Unknown commands return `unknown` and leave buttons
available.
