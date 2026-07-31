import os, smtplib, json, base64, sys
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
from scraper import scrape_hn
from supabase_db import db_add_subscriber, db_remove_subscriber  # ← Supabase sync

load_dotenv()

def _get_env_val(key, default=""):
    val = os.getenv(key)
    if not val:
        try:
            import streamlit as st
            val = st.secrets.get(key, default)
        except Exception:
            val = default
    return (val or "").strip()

SENDER_EMAIL  = _get_env_val("SENDER_EMAIL")
APP_PASSWORD  = _get_env_val("APP_PASSWORD")
ARCHIVE_FILE  = "hn_daily_archive.json"
SUB_FILE      = "subscribers.json"

# Base URL of your deployed Streamlit app — update after deploying
STREAMLIT_URL = _get_env_val("STREAMLIT_URL", "http://localhost:8501")


# ── Subscriber helpers ────────────────────────────────────────────────────────

def load_subscribers():
    """Load subscribers dict from JSON file."""
    if os.path.exists(SUB_FILE):
        with open(SUB_FILE, "r") as f:
            return json.load(f)
    return {}


def save_subscribers(subs):
    """Write subscribers dict back to JSON file."""
    with open(SUB_FILE, "w") as f:
        json.dump(subs, f, indent=2)


def add_subscriber(email, send_time):
    """
    Add a new subscriber with their preferred daily send time.
    send_time format: 'HH:MM' e.g. '08:00'
    Returns False if already subscribed and active.
    Also syncs the new subscriber to Supabase YC_Webscraped table.
    """
    subs = load_subscribers()
    key  = email.lower().strip()

    already_active = key in subs and subs[key]["active"]

    if not already_active:
        subs[key] = {
            "email":         key,
            "send_time":     send_time,
            "active":        True,
            "subscribed_on": str(date.today())
        }
        save_subscribers(subs)

    # ── Always sync to Supabase (upsert handles both new + existing) ──────────
    try:
        db_add_subscriber(key, send_time)
    except Exception as e:
        print(f"[Supabase] Warning: could not sync subscriber {key}: {e}")
    # ─────────────────────────────────────────────────────────────────────────

    return not already_active  # True = new, False = already existed


def remove_subscriber(email):
    """
    Mark subscriber as inactive (soft delete).
    Also syncs the removal to Supabase.
    """
    subs = load_subscribers()
    key  = email.lower().strip()
    if key in subs:
        subs[key]["active"] = False
        save_subscribers(subs)

        # ── Sync to Supabase ──────────────────────────────────────────────────
        try:
            db_remove_subscriber(key)
        except Exception as e:
            print(f"[Supabase] Warning: could not sync removal for {key}: {e}")
        # ─────────────────────────────────────────────────────────────────────

        return True
    return False


def get_due_subscribers(current_time_str):
    """
    Return list of active subscribers whose send_time matches current_time_str.
    current_time_str format: 'HH:MM'
    """
    subs = load_subscribers()
    return [
        s for s in subs.values()
        if s["active"] and s["send_time"] == current_time_str
    ]


# ── Archive helpers ───────────────────────────────────────────────────────────

def load_archive():
    if os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_today(ranked):
    archive = load_archive()
    today   = str(date.today())
    archive[today] = [
        {"upvotes": upvotes, "title": title, "link": link}
        for upvotes, title, link in ranked[:10]
    ]
    with open(ARCHIVE_FILE, "w") as f:
        json.dump(archive, f, indent=2)
    return today


# ── Email builders ────────────────────────────────────────────────────────────

def _unsubscribe_url(email):
    """Build a deep-link URL that opens the Unsubscribe page in Streamlit."""
    encoded = base64.urlsafe_b64encode(email.encode()).decode()
    return f"{STREAMLIT_URL}/?unsub={encoded}"


def build_newsletter_html(ranked, today, receiver_email):
    """Styled dark HTML email with unsubscribe link at the bottom."""
    rows = ""
    for rank, (upvotes, title, link) in enumerate(ranked[:10], start=1):
        full_link = link if link.startswith("http") else f"https://news.ycombinator.com/{link}"
        rows += f"""
        <tr>
          <td style="padding:14px 10px;border-bottom:1px solid #222;
                     font-family:monospace;color:#ff6600;font-size:1.2rem;
                     font-weight:bold;width:44px;">#{rank}</td>
          <td style="padding:14px 10px;border-bottom:1px solid #222;">
            <a href="{full_link}" style="color:#f0ead8;text-decoration:none;
               font-family:monospace;font-size:0.9rem;font-weight:600;">{title}</a>
            <div style="font-family:monospace;font-size:0.7rem;color:#555;
                        margin-top:4px;word-break:break-all;">{full_link}</div>
          </td>
          <td style="padding:14px 10px;border-bottom:1px solid #222;
                     text-align:right;white-space:nowrap;vertical-align:top;">
            <span style="background:#ff6600;color:#000;font-family:monospace;
                         font-weight:700;font-size:0.82rem;padding:3px 8px;
                         border-radius:2px;">▲ {upvotes}</span>
          </td>
        </tr>"""

    unsub_url = _unsubscribe_url(receiver_email)

    return f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#0d0d0d;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0d0d0d;padding:30px 0;">
  <tr><td align="center">
    <table width="620" cellpadding="0" cellspacing="0"
           style="background:#111;border:1px solid #ff6600;border-radius:4px;">

      <!-- Header -->
      <tr><td style="background:#ff6600;padding:22px 28px;">
        <div style="font-family:monospace;font-size:1.9rem;font-weight:900;
                    color:#000;letter-spacing:3px;">🔥 YC DAILY TOP 10</div>
        <div style="font-family:monospace;font-size:0.78rem;color:#000;
                    opacity:0.65;margin-top:5px;">{today} · news.ycombinator.com</div>
      </td></tr>

      <!-- Articles -->
      <tr><td style="padding:10px 18px 20px 18px;">
        <table width="100%" cellpadding="0" cellspacing="0">{rows}</table>
      </td></tr>

      <!-- Unsubscribe footer -->
      <tr><td style="padding:18px 28px;border-top:1px solid #1e1e1e;text-align:center;">
        <p style="font-family:monospace;font-size:0.7rem;color:#444;margin:0 0 10px 0;">
          You're receiving this because you subscribed to YC Daily.
        </p>
        <a href="{unsub_url}"
           style="display:inline-block;background:transparent;border:1px solid #333;
                  color:#666;font-family:monospace;font-size:0.72rem;padding:6px 16px;
                  border-radius:2px;text-decoration:none;">
          Unsubscribe
        </a>
      </td></tr>

    </table>
  </td></tr>
</table>
</body></html>"""


def build_welcome_html(email, send_time):
    """Welcome email sent immediately after subscribing."""
    unsub_url = _unsubscribe_url(email)
    return f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#0d0d0d;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0d0d0d;padding:30px 0;">
  <tr><td align="center">
    <table width="560" cellpadding="0" cellspacing="0"
           style="background:#111;border:1px solid #ff6600;border-radius:4px;">

      <tr><td style="background:#ff6600;padding:22px 28px;">
        <div style="font-family:monospace;font-size:1.8rem;font-weight:900;
                    color:#000;letter-spacing:3px;">👋 YOU'RE IN!</div>
        <div style="font-family:monospace;font-size:0.78rem;color:#000;
                    opacity:0.65;margin-top:5px;">YC Daily Newsletter</div>
      </td></tr>

      <tr><td style="padding:28px;">
        <p style="font-family:monospace;font-size:0.9rem;color:#e8e0d0;margin:0 0 16px 0;">
          Welcome! You've successfully subscribed to the <strong style="color:#ff6600;">YC Daily Top 10</strong>.
        </p>
        <p style="font-family:monospace;font-size:0.85rem;color:#aaa;margin:0 0 24px 0;">
          Every day at <strong style="color:#ff6600;">{send_time}</strong> you'll receive the
          top Hacker News articles ranked by upvotes, delivered straight to your inbox.
        </p>
        <div style="background:#0d0d0d;border-left:3px solid #ff6600;
                    padding:14px 18px;border-radius:2px;">
          <div style="font-family:monospace;font-size:0.72rem;color:#555;margin-bottom:4px;">
            SUBSCRIBED EMAIL
          </div>
          <div style="font-family:monospace;font-size:0.88rem;color:#ff6600;">
            {email}
          </div>
          <div style="font-family:monospace;font-size:0.72rem;color:#555;
                      margin-top:10px;margin-bottom:4px;">DAILY SEND TIME</div>
          <div style="font-family:monospace;font-size:0.88rem;color:#ff6600;">
            {send_time} every day
          </div>
        </div>
      </td></tr>

      <tr><td style="padding:0 28px 22px 28px;text-align:center;">
        <a href="{unsub_url}"
           style="font-family:monospace;font-size:0.7rem;color:#444;text-decoration:none;">
          Unsubscribe anytime
        </a>
      </td></tr>

    </table>
  </td></tr>
</table>
</body></html>"""


# ── Send helpers ──────────────────────────────────────────────────────────────

def _send(to_email, subject, html_body):
    """Core SMTP send — used by both welcome and newsletter senders."""
    load_dotenv(override=True)
    sender = _get_env_val("SENDER_EMAIL")
    password = _get_env_val("APP_PASSWORD")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, to_email, msg.as_string())


def send_welcome_email(email, send_time):
    """Send welcome email immediately after someone subscribes."""
    html = build_welcome_html(email, send_time)
    _send(email, "🔥 Welcome to YC Daily Top 10!", html)
    print(f"[Welcome] Welcome email sent to {email}")


def send_daily_newsletters():
    """
    Scrape HN, save archive, then send to ALL active subscribers.
    Called by scheduler.py at the right time for each subscriber.
    """
    print("[Scrape] Scraping Hacker News...")
    ranked = scrape_hn()
    today  = save_today(ranked)
    print(f"[Archive] Saved archive for {today}")
    return ranked, today


def send_to_subscriber(email, ranked, today):
    """Send the daily newsletter to a single subscriber."""
    html = build_newsletter_html(ranked, today, email)
    _send(email, f"🔥 YC Top 10 — {today}", html)
    print(f"[Email] Sent to {email}")
