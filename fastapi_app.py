"""
fastapi_app.py — REST API layer for the YC Daily Hacker News scraper.

WHY THIS EXISTS
----------------
The original project only exposed its logic through a Streamlit UI
(app.py) and a polling script (scheduler.py). Neither can be called
by another program, a mobile app, a cron job on a different server,
or tested with a simple HTTP request.

This file wraps the SAME core functions you already wrote in
scraper.py, mailer.py and supabase_db.py behind REST endpoints, using
FastAPI. Nothing about the scraping or emailing logic changes — this
is purely an API layer on top of code that already works, which is
exactly how REST APIs get added to real projects.

RUN IT
------
    pip install fastapi uvicorn
    uvicorn fastapi_app:app --reload

Then open http://127.0.0.1:8000/docs for the auto-generated,
interactive Swagger UI (FastAPI builds this for free from the type
hints and Pydantic models below — nothing extra to write).
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# ── Reuse the exact functions already used by app.py / scheduler.py ───────────
from scraper import scrape_hn
from mailer import (
    add_subscriber,
    remove_subscriber,
    load_subscribers,
    load_archive,
    save_today,
    send_welcome_email,
    send_daily_newsletters,
    send_to_subscriber,
)

app = FastAPI(
    title="YC Daily API",
    description="REST API for the Hacker News scraper + newsletter system.",
    version="1.0.0",
)


# ── Pydantic models = request/response validation, done automatically ────────
# FastAPI reads these type hints and rejects bad requests with a 422 error
# BEFORE your function code ever runs — you don't write any manual validation.

class SubscribeRequest(BaseModel):
    email: EmailStr                      # must look like a real email or FastAPI rejects it
    send_time: str = Field(
        default="08:00",
        pattern=r"^([01]\d|2[0-3]):[0-5]\d$",   # must be HH:MM, 24-hour format
        description="Daily send time in HH:MM (24hr) format",
    )


class Article(BaseModel):
    rank: int
    upvotes: int
    title: str
    link: str


class ScrapeResponse(BaseModel):
    count: int
    articles: list[Article]


# ── Health check ───────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    """Simple liveness endpoint — used by uptime monitors / load balancers."""
    return {"status": "ok"}


# ── Scraping endpoint ──────────────────────────────────────────────────────────

@app.get("/scrape", response_model=ScrapeResponse)
def scrape(limit: int = Query(10, ge=1, le=30, description="How many articles to return")):
    """
    Live-scrapes Hacker News right now and returns the top `limit` articles
    ranked by upvotes. Same underlying call the Streamlit 'Live Rankings'
    page and the newsletter both use — scrape_hn() in scraper.py.
    """
    try:
        ranked = scrape_hn()
    except Exception as e:
        # Any network/parsing failure becomes a clean 502, not a stack trace
        raise HTTPException(status_code=502, detail=f"Scrape failed: {e}")

    top = ranked[:limit]
    articles = [
        Article(rank=i, upvotes=upvotes, title=title, link=link)
        for i, (upvotes, title, link) in enumerate(top, start=1)
    ]
    return ScrapeResponse(count=len(articles), articles=articles)


# ── Archive endpoints ───────────────────────────────────────────────────────────

@app.get("/archive")
def get_archive(day: Optional[str] = Query(None, description="YYYY-MM-DD, omit for full archive")):
    """Read hn_daily_archive.json — same file the Streamlit Archive page reads."""
    archive = load_archive()
    if day:
        if day not in archive:
            raise HTTPException(status_code=404, detail=f"No archive saved for {day}")
        return {day: archive[day]}
    return archive


@app.post("/archive/save-today")
def save_today_endpoint():
    """Scrape now and persist today's Top 10 into the archive file."""
    ranked = scrape_hn()
    today = save_today(ranked)
    return {"saved": today, "count": min(len(ranked), 10)}


# ── Subscriber endpoints ───────────────────────────────────────────────────────

@app.get("/subscribers/count")
def subscriber_count():
    """Return the REAL active subscriber count (no display offset)."""
    subs = load_subscribers()
    active = sum(1 for s in subs.values() if s["active"])
    return {"active_subscribers": active}


@app.post("/subscribers", status_code=201)
def create_subscriber(payload: SubscribeRequest):
    """
    Add a subscriber. Mirrors what the Streamlit Subscribe page does:
    add_subscriber() -> optional welcome email -> Supabase sync (inside mailer.py).
    """
    is_new = add_subscriber(payload.email, payload.send_time)
    if is_new:
        try:
            send_welcome_email(payload.email, payload.send_time)
        except Exception as e:
            # Subscriber was still saved even if the email send fails
            return {"email": payload.email, "new": True, "welcome_email_sent": False, "error": str(e)}
    return {"email": payload.email, "new": is_new, "welcome_email_sent": is_new}


@app.delete("/subscribers/{email}")
def delete_subscriber(email: str):
    """Soft-delete (active=False) — same as the Unsubscribe page."""
    removed = remove_subscriber(email)
    if not removed:
        raise HTTPException(status_code=404, detail=f"{email} not found or already inactive")
    return {"email": email, "removed": True}


# ── Newsletter trigger (manual / for testing from Postman, cron, etc.) ────────

@app.post("/newsletter/send/{email}")
def send_newsletter_to(email: str):
    """
    Manually trigger a send to one subscriber — useful for testing without
    waiting for scheduler.py's per-minute loop, or for calling from an
    external cron service instead of running scheduler.py yourself.
    """
    ranked, today = send_daily_newsletters()
    try:
        send_to_subscriber(email, ranked, today)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Send failed: {e}")
    return {"sent_to": email, "date": today, "articles_sent": min(len(ranked), 10)}
