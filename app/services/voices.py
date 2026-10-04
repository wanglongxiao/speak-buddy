from typing import NamedTuple


class BuddyVoice(NamedTuple):
    id: str
    name: str
    gender: str
    accent: str
    style: str


BUDDY_VOICES = (
    BuddyVoice(
        "en_female_skye_emo_v2_mars_bigtts",
        "Serena",
        "female",
        "American English",
        "Vivid",
    ),
    BuddyVoice(
        "en_female_candice_emo_v2_mars_bigtts",
        "Candice",
        "female",
        "American English",
        "Warm",
    ),
    BuddyVoice(
        "en_female_nadia_tips_emo_v2_mars_bigtts",
        "Nadia",
        "female",
        "British English",
        "Sweet",
    ),
    BuddyVoice(
        "en_male_glen_emo_v2_mars_bigtts",
        "Glen",
        "male",
        "American English",
        "Clear",
    ),
    BuddyVoice(
        "en_male_sylus_emo_v2_mars_bigtts",
        "Sylus",
        "male",
        "American English",
        "Deep",
    ),
    BuddyVoice(
        "en_male_corey_emo_v2_mars_bigtts",
        "Corey",
        "male",
        "British English",
        "Clear",
    ),
)

DEFAULT_BUDDY_VOICE = BUDDY_VOICES[0].id
BUDDY_VOICE_IDS = frozenset(voice.id for voice in BUDDY_VOICES)


def valid_buddy_voice(value: str) -> bool:
    return value in BUDDY_VOICE_IDS
