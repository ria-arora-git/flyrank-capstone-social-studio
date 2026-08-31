import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("DB_PATH", os.path.join(os.path.dirname(__file__), "data.sqlite"))

from src.db import get_conn, init_db

SAMPLE_BODY = (
    "Idempotency is the property that lets you retry an action safely: doing it once or a hundred times has the same effect. In publishing systems this matters because networks fail, workers crash, and retries are unavoidable. The trick is to give every attempt a unique key up front and let the database enforce uniqueness, rather than trying to coordinate this in application code."
)

def main():
    init_db()
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO posts (source_type, source_value, body) VALUES (?, ?, ?)",
        ("markdown", "https://example.com/idempotency-101", SAMPLE_BODY),
    )
    conn.commit()
    post_id = cur.lastrowid

    cur = conn.execute(
        "INSERT INTO variants (post_id, platform, content) VALUES (?, 'x', ?)",
        (post_id, SAMPLE_BODY[:230] + " #blog"),
    )
    conn.commit()
    variant_id = cur.lastrowid

    conn.execute(
        "UPDATE variants SET status='approved', updated_at=datetime('now') WHERE id=?",
        (variant_id,),
    )
    conn.execute(
        "INSERT INTO slots (variant_id, scheduled_at) VALUES (?, datetime('now', '+2 minutes'))",
        (variant_id,),
    )
    conn.commit()
    conn.close()

    print(f"Seeded post {post_id}, approved variant {variant_id}, scheduled 2 minutes from now.")
    print("Start the server (uvicorn src.server:app) and it will publish automatically.")


if __name__ == "__main__":
    main()