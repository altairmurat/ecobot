"""
cronjob.py – keep-alive pinger for Render free tier.

The free tier spins down after 15 min of inactivity.
Run this on any always-on machine (or a separate free cron service like cron-job.org)
to ping your app every 10 minutes.

Usage (locally):  python cronjob.py
Or schedule with cron:
  */10 * * * * /usr/bin/python3 /path/to/cronjob.py >> /tmp/ecobot_ping.log 2>&1
"""

import httpx
import time
import os

APP_URL = os.getenv("APP_URL", "https://your-ecobot.onrender.com")
INTERVAL_SECONDS = 10 * 60  # 10 minutes


def ping():
    try:
        r = httpx.get(f"{APP_URL}/", timeout=15)
        print(f"[{time.strftime('%H:%M:%S')}] Ping → {r.status_code}")
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] Ping failed: {e}")


if __name__ == "__main__":
    print(f"Keep-alive pinger started → {APP_URL}")
    while True:
        ping()
        time.sleep(INTERVAL_SECONDS)
