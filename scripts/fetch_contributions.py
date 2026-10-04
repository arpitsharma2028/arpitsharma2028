#!/usr/bin/env python3
"""
Scrape real daily contribution counts from GitHub's public, unauthenticated
contributions endpoint (the same fragment the profile page itself uses) and
write data/contributions.json with raw days and totals.

No token, no auth, no GraphQL -- just the public HTML GitHub already serves.
Run regularly by .github/workflows/update-profile-art.yml.
"""
import datetime
import json
import os
import re
import sys
import urllib.request
from bs4 import BeautifulSoup

USERNAME = os.environ.get("GH_PROFILE_USER", "arpitsharma2028")
URL = f"https://github.com/users/{USERNAME}/contributions"
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "contributions.json")


def fetch_days():
    req = urllib.request.Request(URL, headers={"User-Agent": "profile-readme-bot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8")
    except Exception as e:
        print(f"Error fetching contributions HTML: {e}", file=sys.stderr)
        return []

    soup = BeautifulSoup(html, "html.parser")
    cells = soup.select("td.ContributionCalendar-day")
    if not cells:
        print("no calendar cells found -- github markup may have changed", file=sys.stderr)
        return []

    days = []
    for td in cells:
        date = td.get("data-date")
        if not date:
            continue
        td_id = td.get("id")
        tooltip_el = soup.find("tool-tip", attrs={"for": td_id}) if td_id else None
        text = tooltip_el.get_text(strip=True) if tooltip_el else ""
        if re.search(r"no contributions", text, re.I):
            count = 0
        else:
            m = re.match(r"(\d+)", text)
            count = int(m.group(1)) if m else 0
        days.append({"date": date, "count": count})

    days.sort(key=lambda d: d["date"])
    return days


def build_data(days):
    total = sum(d["count"] for d in days)
    active_days = sum(1 for d in days if d["count"] > 0)
    return {
        "username": USERNAME,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_contributions": total,
        "active_days": active_days,
        "days": days,
    }


if __name__ == "__main__":
    days = fetch_days()
    if days:
        data = build_data(days)
        os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"wrote {OUT_PATH}: {data['total_contributions']} contributions")
    else:
        print("Scrape yielded no days, skipping file overwrite")
