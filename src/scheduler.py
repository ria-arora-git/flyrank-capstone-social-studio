import json
import sqlite3
import threading
import time

from .db import get_conn
from .adapters.registry import get_adapter

STALE_SECONDS = 20  # treat in_progress older than this as needing a retry


def idempotency_key(variant_id: int, slot_id: int) -> str:
    return f"v{variant_id}-s{slot_id}"


def find_due_slots():
    """
    Finds due slots: approved variant, scheduled_at in the past, and
    no successful publish_attempt yet for that (variant, slot).
    """
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT slots.id AS slot_id, slots.scheduled_at, variants.*
        FROM slots
        JOIN variants ON variants.id = slots.variant_id
        WHERE variants.status = 'approved'
          AND slots.scheduled_at <= datetime('now')
          AND NOT EXISTS (
            SELECT 1 FROM publish_attempts pa
            WHERE pa.slot_id = slots.id AND pa.status = 'success'
          )
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def claim_slot(variant: dict, slot_id: int):
    """
    Tries to claim a slot for publishing. Returns the attempt row id if
    this worker won the claim, or None if another attempt already owns
    this slot (already succeeded, failed, or in progress).
    """
    key = idempotency_key(variant["id"], slot_id)
    conn = get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO publish_attempts (idempotency_key, variant_id, slot_id, platform, status)
               VALUES (?, ?, ?, ?, 'in_progress')""",
            (key, variant["id"], slot_id, variant["platform"]),
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None  # someone already claimed this slot — that IS the idempotency guarantee
    finally:
        conn.close()


def publish_slot(variant: dict, slot_id: int):
    attempt_id = claim_slot(variant, slot_id)
    if attempt_id is None:
        print(f"[scheduler] slot {slot_id} already claimed, skipping (idempotency held)")
        return

    conn = get_conn()
    try:
        adapter = get_adapter(variant["platform"])
        result = adapter.publish(variant)
        conn.execute(
            "UPDATE publish_attempts SET status='success', result=?, updated_at=datetime('now') WHERE id=?",
            (json.dumps(result), attempt_id),
        )
        conn.execute(
            "UPDATE variants SET status='published', updated_at=datetime('now') WHERE id=?",
            (variant["id"],),
        )
        conn.commit()
        print(f"[scheduler] published variant {variant['id']} to {variant['platform']}: "
              f"{result.get('preview_url') or result.get('external_id')}")
    except Exception as err:  # noqa: BLE001 - intentional: any adapter failure is recorded
        conn.execute(
            "UPDATE publish_attempts SET status='failed', result=?, updated_at=datetime('now') WHERE id=?",
            (json.dumps({"error": str(err)}), attempt_id),
        )
        conn.commit()
        print(f"[scheduler] FAILED variant {variant['id']}: {err}")
    finally:
        conn.close()


def recover_stale_attempts():
    """
    Recovers rows stuck in 'in_progress' from a crash. It re-attempts
    the SAME row via UPDATE (never a second INSERT), so this can never
    create a duplicate — it can only ever finish the one row that
    already exists for that (variant, slot).
    """
    conn = get_conn()
    stale = conn.execute(
        """
        SELECT pa.*, variants.content AS variant_content, variants.id AS variant_id
        FROM publish_attempts pa
        JOIN variants ON variants.id = pa.variant_id
        WHERE pa.status = 'in_progress'
          AND (strftime('%s','now') - strftime('%s', pa.updated_at)) > ?
        """,
        (STALE_SECONDS,),
    ).fetchall()
    conn.close()

    for row in stale:
        row = dict(row)
        print(f"[scheduler] recovering stale attempt {row['id']} (variant {row['variant_id']})")
        conn = get_conn()
        try:
            adapter = get_adapter(row["platform"])
            variant = {"id": row["variant_id"], "content": row["variant_content"]}
            result = adapter.publish(variant)
            conn.execute(
                "UPDATE publish_attempts SET status='success', result=?, updated_at=datetime('now') WHERE id=?",
                (json.dumps(result), row["id"]),
            )
            conn.execute(
                "UPDATE variants SET status='published', updated_at=datetime('now') WHERE id=?",
                (row["variant_id"],),
            )
            conn.commit()
        except Exception as err:  # noqa: BLE001
            conn.execute(
                "UPDATE publish_attempts SET status='failed', result=?, updated_at=datetime('now') WHERE id=?",
                (json.dumps({"error": str(err)}), row["id"]),
            )
            conn.commit()
        finally:
            conn.close()


def tick():
    recover_stale_attempts()
    for row in find_due_slots():
        variant = {"id": row["id"], "platform": row["platform"], "content": row["content"]}
        publish_slot(variant, row["slot_id"])


def start_worker(interval_seconds: float = 5.0):
    def loop():
        print(f"[scheduler] worker started, polling every {interval_seconds}s")
        while True:
            try:
                tick()
            except Exception as err:  # noqa: BLE001 - worker must never die silently
                print(f"[scheduler] tick error: {err}")
            time.sleep(interval_seconds)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    return thread