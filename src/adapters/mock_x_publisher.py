from ..db import get_conn
from .social_publisher import SocialPublisher

_SCHEMA = """
CREATE TABLE IF NOT EXISTS mock_x_posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  variant_id INTEGER NOT NULL,
  content TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

class MockXPublisher(SocialPublisher):
    def __init__(self):
        conn = get_conn()
        conn.executescript(_SCHEMA)
        conn.commit()
        conn.close()

    def publish(self, variant: dict) -> dict:
        conn = get_conn()
        cur = conn.execute(
            "INSERT INTO mock_x_posts (variant_id, content) VALUES (?, ?)",
            (variant["id"], variant["content"]),
        )
        conn.commit()
        row_id = cur.lastrowid
        conn.close()
        preview = variant["content"][:60]
        return {"external_id": f"mock-x-{row_id}", "preview_url": f'[MOCK X PREVIEW] "{preview}..."'}