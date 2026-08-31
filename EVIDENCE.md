# Phase 2 Evidence

## Manual Gate Check

### 1. Markdown ingestion

Command:

curl -s -X POST localhost:3000/posts -H "Content-Type: application/json" -d '{
  "sourceType":"markdown",
  "sourceValue":"https://example.com/my-post",
  "body":"This is a long blog post about backend architecture and idempotent systems."
}'

Response:

{"id":1,"source_type":"markdown","source_value":"https://example.com/my-post","body":"This is a long blog post about backend architecture and idempotent systems.","created_at":"2026-08-31 11:10:33"}

### 2. Generate variants

Command:

curl -s -X POST localhost:3000/posts/1/generate -H "Content-Type: application/json" -d '{"platforms":["x","linkedin"]}'

Response:

{"created":[{"id":1,"post_id":1,"platform":"x","content":"This is a long blog post about backend architecture and idempotent systems. #blog","status":"draft","created_at":"2026-08-31 11:10:52","updated_at":"2026-08-31 11:10:52"},{"id":2,"post_id":1,"platform":"linkedin","content":"This is a long blog post about backend architecture and idempotent systems.\n\nRead the full post: https://example.com/my-post\n\n#Insights #Growth","status":"draft","created_at":"2026-08-31 11:10:52","updated_at":"2026-08-31 11:10:52"}],"blocked":[]}

Result: 2 variants created, 0 blocked.

### 3. URL ingestion

Command:

curl -s -X POST localhost:3000/posts -H "Content-Type: application/json" -d '{
  "sourceType":"url",
  "sourceValue":"https://lnkd.in/p/dQeSfJff"
}'

Response:

{"id":2,"source_type":"url","source_value":"https://lnkd.in/p/dQeSfJff","body":"Standardize Audio for Improved Whisper Transcription Accuracy | Ria Arora posted on the topic | LinkedIn ...","created_at":"2026-08-31 11:15:17"}

Result: URL ingestion succeeded and fetched content was populated in the body field.