import re

def first_sentences(body: str, max_chars: int) -> str:
    clean = re.sub(r"\s+", " ", body).strip()
    if len(clean) > max_chars:
        return clean[: max_chars - 1].strip() + "…"
    return clean

def generate_variant(platform: str, post: dict) -> str:
    body = post["body"]
    if platform in ("x", "mock_x"):
        return f"{first_sentences(body, 230)} #blog"
    if platform in ("linkedin", "mock_linkedin"):
        return (
            f"{first_sentences(body, 900)}\n\n"
            f"Read the full post: {post['source_value']}\n\n#Insights #Growth"
        )
    if platform == "telegram":
        return f"📰 New post!\n\n{first_sentences(body, 700)}\n\n{post['source_value']}"
    raise ValueError(f'no generator template for platform "{platform}"')