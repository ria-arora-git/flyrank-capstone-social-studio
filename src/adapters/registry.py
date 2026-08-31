import os
from .telegram_publisher import TelegramPublisher
from .mock_x_publisher import MockXPublisher
from .mock_linkedin_publisher import MockLinkedInPublisher

_registry = {
    "telegram": TelegramPublisher(),
    "mock_x": MockXPublisher(),
    "mock_linkedin": MockLinkedInPublisher(),
}

def _parse_map(env_value: str) -> dict:
    mapping = {"x": "mock_x", "linkedin": "mock_linkedin", "telegram": "telegram"}
    if not env_value:
        return mapping
    for pair in env_value.split(","):
        if ":" not in pair:
            continue
        platform, adapter_key = [p.strip() for p in pair.split(":", 1)]
        if platform and adapter_key:
            mapping[platform] = adapter_key
    return mapping

def get_adapter(platform: str):
    platform_to_adapter_key = _parse_map(os.environ.get("PLATFORM_ADAPTER_MAP", ""))
    adapter_key = platform_to_adapter_key.get(platform, platform)
    adapter = _registry.get(adapter_key)
    if not adapter:
        raise ValueError(f'no adapter registered for "{adapter_key}"')
    return adapter