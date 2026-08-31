import re

PROFILES = {
    "x": {"max_length": 280, "max_hashtags": 2, "tone": "punchy"},
    "linkedin": {"max_length": 3000, "max_hashtags": 5, "tone": "professional"},
    "mock_x": {"max_length": 280, "max_hashtags": 2, "tone": "punchy"},
    "mock_linkedin": {"max_length": 3000, "max_hashtags": 5, "tone": "professional"},
    "telegram": {"max_length": 1000, "max_hashtags": 4, "tone": "conversational"},
}

HASHTAG_RE = re.compile(r"#[A-Za-z0-9_]+")

def count_hashtags(text: str) -> int:
    return len(HASHTAG_RE.findall(text))

def validate_variant(platform: str, text: str) -> dict:
    """
    Validates one variant's text against its platform profile.
    Returns {"ok": True} or {"ok": False, "reason": "..."} — the reason
    always names the exact rule that was broken (Probe 2 checks this).
    """
    profile = PROFILES.get(platform)
    if not profile:
        return {"ok": False, "reason": f'unknown platform "{platform}"'}
    if len(text) > profile["max_length"]:
        return {
            "ok": False,
            "reason": f'length {len(text)} exceeds max {profile["max_length"]} for {platform}',
        }
    tags = count_hashtags(text)
    if tags > profile["max_hashtags"]:
        return {
            "ok": False,
            "reason": f'hashtag count {tags} exceeds max {profile["max_hashtags"]} for {platform}',
        }
    return {"ok": True}