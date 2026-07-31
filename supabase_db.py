"""
supabase_db.py — Supabase integration for YC Daily subscriber management.
Stores and syncs subscriber emails to the YC_Webscraped table in Supabase.
"""

import os, sys
import requests
from datetime import date
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

def _get_env_val(key, default=""):
    val = os.getenv(key)
    if not val:
        try:
            import streamlit as st
            val = st.secrets.get(key, default)
        except Exception:
            val = default
    return (val or "").strip()

SUPABASE_URL = _get_env_val("SUPABASE_URL", "https://yritfdwfszqinxrdhnut.supabase.co")
SUPABASE_KEY = _get_env_val("SUPABASE_KEY", "")

TABLE = "YC_Webscraped"

HEADERS = {
    "apikey":        SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type":  "application/json",
    "Prefer":        "return=representation",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _url(query=""):
    return f"{SUPABASE_URL}/rest/v1/{TABLE}{query}"


# ── Public API ────────────────────────────────────────────────────────────────

def db_add_subscriber(email: str, send_time: str) -> bool:
    """
    Insert a new subscriber row into YC_Webscraped.
    Uses upsert so re-subscribing just reactivates the row.
    Returns True on success, False on failure.
    """
    payload = {
        "email":         email.lower().strip(),
        "send_time":     send_time,
        "active":        True,
        "subscribed_on": str(date.today()),
    }
    resp = requests.post(
        _url(),
        json=payload,
        headers={**HEADERS, "Prefer": "resolution=merge-duplicates,return=representation"},
    )
    if resp.status_code in (200, 201):
        print(f"[Supabase] Subscriber added: {email}")
        return True
    print(f"[Supabase] Insert failed ({resp.status_code}): {resp.text}")
    return False


def db_remove_subscriber(email: str) -> bool:
    """
    Soft-delete: set active = False for the given email.
    Returns True on success.
    """
    email = email.lower().strip()
    resp = requests.patch(
        _url(f"?email=eq.{email}"),
        json={"active": False},
        headers=HEADERS,
    )
    if resp.status_code in (200, 204):
        print(f"[Supabase] Unsubscribed: {email}")
        return True
    print(f"[Supabase] Update failed ({resp.status_code}): {resp.text}")
    return False


def db_get_all_subscribers() -> list:
    """Return all rows from YC_Webscraped as a list of dicts."""
    resp = requests.get(_url("?select=*"), headers=HEADERS)
    if resp.status_code == 200:
        return resp.json()
    print(f"[Supabase] Fetch failed ({resp.status_code}): {resp.text}")
    return []


def db_subscriber_exists(email: str) -> bool:
    """Check if an email is already actively subscribed."""
    email = email.lower().strip()
    resp = requests.get(
        _url(f"?email=eq.{email}&active=eq.true&select=email"),
        headers=HEADERS,
    )
    if resp.status_code == 200:
        return len(resp.json()) > 0
    return False
