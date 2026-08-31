# Social Media Studio

Turns one blog post into per-platform social variants, gated behind human review, published
exactly once through a durable, crash-safe scheduler.

## Architecture

```
[blog post: URL or markdown]
        |
        v
  ingest + store  --->  variant generator  --->  constraint validation
                                                        |
                                                        v
                            review workflow: draft -> approved | rejected
                                                        |
                                                        v
                              scheduler (durable, resumable, idempotent)
                                                        |
                                                        v
                                    SocialPublisher interface
                                +-- TelegramPublisher (real)
                                +-- MockXPublisher
                                +-- MockLinkedInPublisher
                                                        |
                                                        v
                                publish history: one slot = one post, always
```

## Run it

```bash
git clone https://github.com/<you>/flyrank-capstone-social-studio.git
cd flyrank-capstone-social-studio
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 seed.py      
python3 -m uvicorn src.server:app --port 3000
```

Server runs on `http://localhost:3000`. The scheduler worker starts automatically as a
background thread in the same process and polls every `WORKER_INTERVAL_SECONDS` (default 5s).
The seeded post will publish itself about 2 minutes after you start the server.

## Try it manually

```bash
curl -s -X POST localhost:3000/posts -H "Content-Type: application/json" -d '{
  "sourceType":"markdown","sourceValue":"https://example.com/post",
  "body":"Your blog post text here."
}'
curl -s -X POST localhost:3000/posts/1/generate -d '{"platforms":["x","linkedin"]}' -H "Content-Type: application/json"
curl -s -X PATCH localhost:3000/variants/1/approve
curl -s -X POST localhost:3000/variants/1/schedule -d '{"scheduledAt":"2026-01-01 00:00:00"}' -H "Content-Type: application/json"
curl -s localhost:3000/history
```

## Tests

```bash
python3 test_smoke.py            # ingest, blocking, approval gate, idempotent publish, adapter swap
python3 test_crash_recovery.py   # worker-restart-mid-publish does not duplicate
```

## Known limitations

- Variant generation is template-based by default; swapping in an AI model only requires
  changing `src/generator.py`.
- The scheduler runs as a background thread inside the same process using Python's `threading`
  module. For real production scale you'd run it as a separate process (or swap in APScheduler
  with a persistent job store, which the brief also suggests), but the durability guarantee — a
  UNIQUE constraint on the idempotency key — is identical either way.
- URL ingestion does a best-effort text extraction with BeautifulSoup; very unusual page layouts
  (heavy JavaScript rendering, paywalls) may need the body pasted manually instead.
