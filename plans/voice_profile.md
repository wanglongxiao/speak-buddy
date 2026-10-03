# Buddy Voice Profile

## Hard Requirements

- Language and accent: American English (`en-US`) only.
- Character: warm, clear, friendly, and lightly energetic.
- Default voice ID: `en_female_skye_emo_v2_mars_bigtts` (Skye/Serena,
  American English), overridden only by another verified American-English
  female voice ID.
- Startup fails with an explicit configuration error when the voice does not
  begin with `en_us` or `en-US`.

## Speed

Slow 0.85x, Normal 1.0x, Fast 1.15x. Changing speed must preserve the same
speaker. Frustration recovery uses 0.9x and softer wording, not a different
accent.

## Output

MP3, mono, 24 kHz where supported. Generated files are cached by a hash of text,
voice, and speed. UI previews are available for each speed.

## Verification

Before release, synthesize the same sentence at all three speeds and listen for
speaker consistency, American vowels, clipping, and intelligibility on phone
speakers.
