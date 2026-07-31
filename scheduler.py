"""
scheduler.py — Run this once and leave it running.
It checks every minute who needs a newsletter right now and sends it.

Usage:
    python scheduler.py
"""

import time
from datetime import datetime
from mailer import get_due_subscribers, send_daily_newsletters, send_to_subscriber

print("⏰ YC Daily Scheduler started. Press Ctrl+C to stop.")
print("   Checking every minute for due subscribers...\n")

# Cache ranked articles per minute so we don't scrape HN once per subscriber
_last_scraped_minute = None
_cached_ranked       = None
_cached_today        = None

while True:
    now        = datetime.now()
    time_str   = now.strftime("%H:%M")   # e.g. '08:00'
    minute_key = now.strftime("%Y-%m-%d %H:%M")  # unique per minute per day

    due = get_due_subscribers(time_str)  # Who wants their email right now?

    if due:
        # Scrape once per minute even if multiple subscribers are due
        if minute_key != _last_scraped_minute:
            print(f"[{time_str}] {len(due)} subscriber(s) due — scraping HN...")
            _cached_ranked, _cached_today = send_daily_newsletters()
            _last_scraped_minute = minute_key

        # Send to each due subscriber
        for subscriber in due:
            try:
                send_to_subscriber(subscriber["email"], _cached_ranked, _cached_today)
            except Exception as e:
                print(f"❌ Failed to send to {subscriber['email']}: {e}")

    else:
        print(f"[{time_str}] No emails due.", end="\r")  # Overwrite same line

    time.sleep(60)  # Wait 60 seconds before checking again
