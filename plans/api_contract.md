# API Contract

All failures use:

```json
{"ok": false, "hint_en": "Please try again.", "hint_zh": "请再试一次。"}
```

## Audio and AI

- `POST /api/upload-audio` multipart `audio`, `rms`, `duration_ms` returns
  `{audio_key,url,rms,duration_ms}`.
- `POST /api/asr` `{audio_key,lang:"en"}` returns
  `{transcript,confidence,duration_ms}`.
- `POST /api/tts` `{text,voice,speed}` returns `{url}`.
- `POST /api/coach` `{topic_id,question,transcript,history,user_profile,
  asr_confidence}` returns `CoachResult`.
- `POST /api/pronunciation` `{audio_key,reference_text}` returns
  `{score,word_match,confidence}`.
- `POST /api/loud/record` `{audio_key,context,rms,duration_ms}` returns
  `{rms,duration_ms,counted_seconds}`.

## Topics and Commands

- `POST /api/topics/create-from-voice` `{raw_text}` returns `TopicCard`.
- `POST /api/voice-command` `{audio_key,transcript?}` returns `{intent,slots}`.

## Read Models

- `GET /api/progress` returns rolling average, 30-day series, radar data, loud
  time, and three weekly highlights.
- `GET /api/trophies` returns earned and locked badge arrays.

## CoachResult

Strict fields: `praise`, optional `tiny_tweak`, `highlight_words`,
`ideal_rephrase`, optional phonetic hint, `follow_up_question`, four 0-100
scores, `xp_earned` 10-30, `encourage_loud`, `emotion_boost`, and one to three
`suggested_new_words`.
