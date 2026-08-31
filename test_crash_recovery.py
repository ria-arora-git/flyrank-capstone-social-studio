import os
import sys

os.environ["PLATFORM_ADAPTER_MAP"] = "x:mock_x"
os.environ["DB_PATH"] = os.path.join(os.path.dirname(__file__), "data.sqlite")
sys.path.insert(0, os.path.dirname(__file__))

from src.db import get_conn, init_db
from src import scheduler

def main():
    init_db()
    conn = get_conn()
    conn.execute("INSERT INTO posts (source_type, source_value, body) VALUES ('markdown','u','body text here')")
    conn.execute(
        "INSERT INTO variants (post_id, platform, content, status) VALUES (1,'x','crash test content','approved')"
    )
    conn.execute("INSERT INTO slots (variant_id, scheduled_at) VALUES (1, '2020-01-01 00:00:00')")
    conn.execute(
        "INSERT INTO publish_attempts (idempotency_key, variant_id, slot_id, platform, status, updated_at) "
        "VALUES ('v1-s1',1,1,'x','in_progress', datetime('now','-1 hour'))"
    )
    conn.commit()

    before = [dict(r) for r in conn.execute("SELECT * FROM publish_attempts").fetchall()]
    print("before recovery:", before)
    conn.close()

    scheduler.tick()

    conn = get_conn()
    after = [dict(r) for r in conn.execute("SELECT * FROM publish_attempts").fetchall()]
    print("after recovery :", after)
    mock_posts = conn.execute("SELECT * FROM mock_x_posts").fetchall()
    print("mock_x_posts count :", len(mock_posts))
    conn.close()

if __name__ == "__main__":
    main()