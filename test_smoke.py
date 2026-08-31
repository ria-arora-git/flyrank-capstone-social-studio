import os
import sys
import threading

os.environ["PLATFORM_ADAPTER_MAP"] = "x:mock_x,linkedin:mock_linkedin,telegram:mock_x"
os.environ["DB_PATH"] = os.path.join(os.path.dirname(__file__), "data.sqlite")
sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient
from src.server import app
from src.db import get_conn
from src.scheduler import publish_slot
from src.constraints import validate_variant
from src.adapters.registry import get_adapter

def main():
    with TestClient(app) as client:
        print(" 1. ingest a post ")
        r = client.post("/posts", json={
            "sourceType": "markdown",
            "sourceValue": "https://example.com/my-post",
            "body": "This is a long blog post about backend architecture and idempotent systems.",
        })
        print(r.status_code, r.json())
        post_id = r.json()["id"]

        print("\n 2. generate variants for x + linkedin ")
        r = client.post(f"/posts/{post_id}/generate", json={"platforms": ["x", "linkedin"]})
        print(r.status_code, r.json())
        variants = r.json()["created"]

        print("\n 2b. rule-breaking variant is blocked (too many hashtags) ")
        print(validate_variant("x", "short text #a #b #c #d #e #f"))

        print("\n 3. schedule BEFORE approval must be 4xx ")
        x_variant = next(v for v in variants if v["platform"] == "x")
        r = client.post(f"/variants/{x_variant['id']}/schedule", json={"scheduledAt": "2020-01-01 00:00:00"})
        print(r.status_code, r.json())

        print("\n 3b. approve then schedule succeeds ")
        r = client.patch(f"/variants/{x_variant['id']}/approve")
        print("approve:", r.status_code, r.json()["status"])
        r = client.post(f"/variants/{x_variant['id']}/schedule", json={"scheduledAt": "2020-01-01 00:00:00"})
        print("schedule:", r.status_code, r.json())
        slot_id = r.json()["slot"]["id"]

        print("\n 4/5. idempotent publish: call publish_slot 3x concurrently (real threads) ")
        conn = get_conn()
        variant_row = dict(conn.execute("SELECT * FROM variants WHERE id = ?", (x_variant["id"],)).fetchone())
        conn.close()

        threads = [threading.Thread(target=publish_slot, args=(variant_row, slot_id)) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        conn = get_conn()
        attempts = conn.execute("SELECT * FROM publish_attempts WHERE slot_id = ?", (slot_id,)).fetchall()
        conn.close()
        print("publish_attempts rows for this slot (must be exactly 1):", len(attempts))
        for a in attempts:
            print(dict(a))

        print("\n 6. adapter swap via env, zero code change ")
        print("adapter used for 'telegram':", type(get_adapter("telegram")).__name__)

        print("\n history ")
        r = client.get("/history")
        print(r.status_code, r.json())

    print("\nALL SMOKE CHECKS DONE")

if __name__ == "__main__":
    main()