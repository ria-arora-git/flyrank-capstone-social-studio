# Design — Social Media Studio

## Problem
Turn one blog post into approved, scheduled posts across multiple platforms, without ever
publishing an unapproved variant or publishing the same approved variant twice.

## Data model
- **posts**: id, source_type (url|markdown), source_value, body, created_at
  — the single source of truth; nothing else feeds the generator.
- **variants**: id, post_id, platform, content, status (draft|approved|rejected|published),
  created_at, updated_at
- **slots**: id, variant_id, scheduled_at, created_at
  — a slot is a scheduled time for one variant.
- **publish_attempts**: id, idempotency_key (UNIQUE), variant_id, slot_id, platform,
  status (in_progress|success|failed), result, created_at, updated_at
  — one row per (variant, slot) ever. The UNIQUE constraint on idempotency_key is what
  makes publishing safe under retries and worker crashes.

## API surface
- `POST /posts` — ingest a post (url or markdown + body)
- `GET /posts/{id}` — fetch a stored post
- `POST /posts/{id}/generate` — generate + validate variants for given platforms
- `GET /posts/{id}/variants` — list variants for a post
- `PATCH /variants/{id}/approve` — approve a variant
- `PATCH /variants/{id}/reject` — reject a variant
- `PATCH /variants/{id}/edit` — edit variant content (re-validated)
- `POST /variants/{id}/schedule` — create a slot for an **approved** variant (409 otherwise)
- `GET /history` — every publish attempt and its outcome
- `GET /constraints` — the active constraint profiles (for debugging)

## SocialPublisher interface
```
class SocialPublisher(ABC):
    def publish(self, variant: dict) -> dict: {"external_id", "preview_url"}
```
Implementations: `TelegramPublisher` (real), `MockXPublisher`, `MockLinkedInPublisher`.
The scheduler and routes only ever call `adapter.publish(variant)` — they never know which
concrete class they're holding. Which platform maps to which adapter class is decided in
one place: `src/adapters/registry.py`, overridable via the `PLATFORM_ADAPTER_MAP` env var.

## Non-goal
This system does not do analytics, engagement tracking, or image generation. It also does
not integrate with real Instagram, X, or LinkedIn accounts — those are proven via mock
adapters plus one real free platform (Telegram), per the brief.