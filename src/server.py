import os

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from .db import get_conn, init_db
from .generator import generate_variant
from .constraints import validate_variant, PROFILES
from .ingest import fetch_url_text

app = FastAPI(title="Social Media Studio")

@app.on_event("startup")
def on_startup():
    init_db()

# Request bodies 
class EditIn(BaseModel):
    content: str

class PostIn(BaseModel):
    sourceType: str
    sourceValue: str
    body: Optional[str] = None 

class GenerateIn(BaseModel):
    platforms: Optional[List[str]] = None

# Post ingestion 
@app.post("/posts", status_code=201)
def create_post(payload: PostIn):
    if payload.sourceType not in ("url", "markdown"):
        raise HTTPException(400, 'sourceType must be "url" or "markdown"')

    if payload.sourceType == "markdown":
        if not payload.body:
            raise HTTPException(400, "body is required when sourceType is 'markdown'")
        body = payload.body
    else:  
        if payload.body:
            body = payload.body
        else:
            try:
                body = fetch_url_text(payload.sourceValue)
            except Exception as err:
                raise HTTPException(400, f"could not fetch that URL: {err}")

    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO posts (source_type, source_value, body) VALUES (?, ?, ?)",
        (payload.sourceType, payload.sourceValue, body),
    )
    conn.commit()
    post = conn.execute("SELECT * FROM posts WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return dict(post)

@app.get("/posts/{post_id}")
def get_post(post_id: int):
    conn = get_conn()
    post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    conn.close()
    if not post:
        raise HTTPException(404, "post not found")
    return dict(post)

# Variant generation 
@app.post("/posts/{post_id}/generate", status_code=201)
def generate(post_id: int, payload: GenerateIn):
    conn = get_conn()
    post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        conn.close()
        raise HTTPException(404, "post not found")
    post = dict(post)

    platforms = payload.platforms or ["x", "linkedin"]
    created, blocked = [], []

    for platform in platforms:
        try:
            content = generate_variant(platform, post)
        except ValueError as err:
            blocked.append({"platform": platform, "reason": str(err)})
            continue

        check = validate_variant(platform, content)
        if not check["ok"]:
            blocked.append({"platform": platform, "reason": check["reason"], "content": content})
            continue

        cur = conn.execute(
            "INSERT INTO variants (post_id, platform, content) VALUES (?, ?, ?)",
            (post_id, platform, content),
        )
        conn.commit()
        variant = conn.execute("SELECT * FROM variants WHERE id = ?", (cur.lastrowid,)).fetchone()
        created.append(dict(variant))

    conn.close()
    return {"created": created, "blocked": blocked}

@app.get("/posts/{post_id}/variants")
def list_variants(post_id: int):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM variants WHERE post_id = ?", (post_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# Review workflow 
@app.patch("/variants/{variant_id}/approve")
def approve_variant(variant_id: int):
    conn = get_conn()
    variant = conn.execute("SELECT * FROM variants WHERE id = ?", (variant_id,)).fetchone()
    if not variant:
        conn.close()
        raise HTTPException(404, "variant not found")
    if variant["status"] == "published":
        conn.close()
        raise HTTPException(400, "cannot approve a variant that is already published")
    conn.execute(
        "UPDATE variants SET status='approved', updated_at=datetime('now') WHERE id=?", (variant_id,)
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM variants WHERE id = ?", (variant_id,)).fetchone()
    conn.close()
    return dict(updated)


@app.patch("/variants/{variant_id}/reject")
def reject_variant(variant_id: int):
    conn = get_conn()
    variant = conn.execute("SELECT * FROM variants WHERE id = ?", (variant_id,)).fetchone()
    if not variant:
        conn.close()
        raise HTTPException(404, "variant not found")
    conn.execute(
        "UPDATE variants SET status='rejected', updated_at=datetime('now') WHERE id=?", (variant_id,)
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM variants WHERE id = ?", (variant_id,)).fetchone()
    conn.close()
    return dict(updated)


@app.patch("/variants/{variant_id}/edit")
def edit_variant(variant_id: int, payload: EditIn):
    conn = get_conn()
    variant = conn.execute("SELECT * FROM variants WHERE id = ?", (variant_id,)).fetchone()
    if not variant:
        conn.close()
        raise HTTPException(404, "variant not found")
    check = validate_variant(variant["platform"], payload.content)
    if not check["ok"]:
        conn.close()
        raise HTTPException(400, check["reason"])
    conn.execute(
        "UPDATE variants SET content=?, updated_at=datetime('now') WHERE id=?",
        (payload.content, variant_id),
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM variants WHERE id = ?", (variant_id,)).fetchone()
    conn.close()
    return dict(updated)

@app.get("/constraints")
def constraints():
    return PROFILES

@app.get("/health")
def health():
    return {"ok": True}