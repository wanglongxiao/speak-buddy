# TOS Skill

## Responsibility

Store learner audio in BytePlus TOS and resolve local fallback recordings.

## Input / Output

Input: bytes, original filename, and MIME type. Output:
`StoredAudio(key, url, local_path, provider)`.

## Dependencies

BytePlus `tos` SDK and AK/SK/bucket settings; writable `data/audio`.

## Example

`store_audio(content, "turn.webm", "audio/webm")`

## Failure Fallback

Missing credentials, SDK errors, or TOS downtime writes the same bytes locally
and returns a `/audio/...` URL. Secrets never leave the backend.
