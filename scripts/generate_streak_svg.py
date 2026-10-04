#!/usr/bin/env python3
"""Generate an animated GitHub contribution heatmap SVG with constant refreshing animation.
Squares light up with a diagonal pop & flash sweep, hold, and smoothly loop constantly.
Works standalone; designed to run in a GitHub Action regularly to stay live.
Usage: python generate_streak_svg.py [username] [output.svg]
"""
import sys, json, os, datetime, urllib.request

USER = sys.argv[1] if len(sys.argv) > 1 else "arpitsharma2028"
OUT  = sys.argv[2] if len(sys.argv) > 2 else "contrib-heatmap.svg"

def get_data(user):
    url = f"https://github-contributions-api.jogruber.de/v4/{user}?y=last"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "profile-readme/1.0"})
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        # fallback to a local snapshot if the API is unreachable
        here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "contributions.json")
        if os.path.exists(here):
            print("API failed (%s); using local contributions.json" % e)
            return json.load(open(here, "r", encoding="utf-8"))
        raise

raw_data = get_data(USER)

if "contributions" in raw_data:
    contribs = raw_data["contributions"]
    total = raw_data.get("total", {}).get("lastYear", sum(c.get("count", 0) for c in contribs))
elif "days" in raw_data:
    contribs = []
    for d in raw_data["days"]:
        cnt = d.get("count", 0)
        lvl = 0 if cnt == 0 else (1 if cnt <= 3 else (2 if cnt <= 6 else (3 if cnt <= 9 else 4)))
        contribs.append({"date": d["date"], "count": cnt, "level": lvl})
    total = raw_data.get("total_contributions", sum(c["count"] for c in contribs))
else:
    raise ValueError("Unrecognized contribution data format")

# ---- layout ----
CELL, GAP, RAD, LEFT, TOP = 13, 3, 2.5, 34, 24
COLORS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
FLASH = "#b4ffaa"
GRAY = "#7d8590"
MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

n = len(contribs)
NW = (n + 6) // 7
W = LEFT + NW * (CELL + GAP) + 6
H = TOP + 7 * (CELL + GAP) + 22

# timing (seconds) for constant looping animation
CYCLE = 9.5
REVEAL = 2.8
maxorder = (NW - 1) + 6 * 0.55

rects, labels = [], []
sd = datetime.date.fromisoformat(contribs[0]["date"])
last_m = None
for wk in range(NW):
    d = sd + datetime.timedelta(days=wk * 7)
    if d.month != last_m:
        last_m = d.month
        labels.append(f'<text class="lbl" x="{LEFT + wk * (CELL + GAP)}" y="{TOP - 8}">{MONTHS[d.month - 1]}</text>')

for name, r in [("Mon", 1), ("Wed", 3), ("Fri", 5)]:
    labels.append(f'<text class="lbl" x="2" y="{TOP + r * (CELL + GAP) + CELL - 2}">{name}</text>')

for i, c in enumerate(contribs):
    wk, row, lvl = i // 7, i % 7, c["level"]
    x = LEFT + wk * (CELL + GAP)
    y = TOP + row * (CELL + GAP)
    delay = round((wk + row * 0.55) / maxorder * REVEAL, 3)
    cls = "c g" if lvl >= 1 else "c e"
    rects.append(
        f'<rect class="{cls}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="{RAD}" '
        f'fill="{COLORS[lvl]}" style="animation-delay:{delay}s"/>'
    )

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">
<style>
  text.lbl {{ fill: {GRAY}; font-size: 13px; font-weight: 600; }}
  text.total {{ fill: #e6edf3; font-size: 15px; font-weight: 700; }}
  .c {{
    transform-box: fill-box;
    transform-origin: center;
    opacity: 0;
    animation: pop {CYCLE}s ease-out infinite both;
  }}
  .g {{
    animation: pop {CYCLE}s ease-out infinite both, flash {CYCLE}s ease-out infinite both;
  }}
  @keyframes pop {{
    0%   {{ opacity: 0; transform: scale(.2); }}
    2%   {{ opacity: 1; transform: scale(1.15); }}
    5%   {{ opacity: 1; transform: scale(1); }}
    57%  {{ opacity: 1; transform: scale(1); }}
    64%  {{ opacity: 0; transform: scale(.6); }}
    100% {{ opacity: 0; transform: scale(.6); }}
  }}
  @keyframes flash {{
    0%   {{ filter: brightness(2.6); }}
    3%   {{ filter: brightness(2.6); }}
    7%   {{ filter: brightness(1); }}
    100% {{ filter: brightness(1); }}
  }}
  @media (prefers-color-scheme: light) {{
    text.lbl {{ fill: #57606a; }}
    text.total {{ fill: #1f2328; }}
    .c.e {{ fill: #ebedf0 !important; }}
  }}
  @media (prefers-reduced-motion: reduce) {{
    .c {{ opacity: 1 !important; transform: none !important; animation: none !important; }}
  }}
</style>
<rect width="{W}" height="{H}" fill="none"/>
{''.join(labels)}
{''.join(rects)}
<text class="total" x="{LEFT}" y="{H - 6}">{total:,} contributions in the last year</text>
</svg>'''

os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(svg)

print(f"Wrote {OUT}: {n} days, {total:,} contributions, {len(svg) // 1024} KB")
