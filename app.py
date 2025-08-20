import json
import streamlit as st

# ──────────────────────────────
# Page & Theme
# ──────────────────────────────
st.set_page_config(page_title="LoudVoice Dashboard", page_icon="🎛️", layout="wide")

# Optional zoom control: use ?zoom=115 in the URL for a TV farther away
zoom = st.query_params.get("zoom", ["100"])[0]
st.markdown(f"<style>body {{ zoom: {zoom}% }}</style>", unsafe_allow_html=True)

# Brand colors
YELLOW = "#ffd54a"  # LoudVoice-style yellow
TEXT   = "#f5f7ff"
MUTED  = "#8b93b5"
ACCENT = "#58b1ff"  # secondary accent for lines, etc.

# Global CSS (TV/kiosk look)
st.markdown(f"""
<style>
/* Hide Streamlit chrome for TV use */
header[data-testid="stHeader"]{{display:none;}}
#MainMenu{{visibility:hidden;}}
footer{{visibility:hidden;}}

html, body, [class^="css"] {{
  background:#000 !important; color:{TEXT}!important;
}}
.block-container {{ max-width: 1800px; padding-top: 16px; }}
h1,h2,h3,h4,h5,h6,.section-title,.kpi-label {{ color: {YELLOW}!important; }}

.card {{
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 18px 20px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.35);
}}

.kpi {{ display:flex; gap:12px; align-items:center; }}
.kpi .icon {{
  width:36px; height:36px; border-radius:10px;
  display:flex; align-items:center; justify-content:center; font-size:18px;
  background: #20242f; border:1px solid rgba(255,255,255,.06);
}}
.kpi .big {{ font-size: 56px; font-weight: 800; margin: 0; }}
.kpi .kpi-label {{ font-size: 14px; letter-spacing:.3px; color:{YELLOW}; font-weight:700; }}

.section-title {{ font-size: 22px; font-weight: 800; margin: 0 0 12px 0; }}

.row, .row-sm {{
  display:flex; align-items:center; justify-content:space-between;
  gap: 12px; padding: 10px 0;
  border-bottom: 1px solid rgba(255,255,255,.07);
}}
.row:last-child, .row-sm:last-child{{ border-bottom:none; }}

.pill {{
  font-size:12px; padding:4px 8px; border-radius:999px;
  background:#23283b; color:#dfe5ff; border:1px solid rgba(255,255,255,.08);
}}
.small {{ color:{MUTED}; font-size:12px; }}

/* Bars */
.hbar {{ position:relative; height:12px; width:100%; background:#23283b; border-radius:6px; overflow:hidden; }}
.hbar > span {{ position:absolute; left:0; top:0; bottom:0; display:block; border-radius:6px; }}
.bar-red   {{ background:#ff5a5f; }}
.bar-yellow{{ background:#ffd166; }}
.bar-green {{ background:#2ECC71; }}

.views-bar {{ height:14px; border-radius:7px; background:#23283b; overflow:hidden; }}
.views-bar > span {{ display:block; height:100%; }}

.map-wrap {{ position:relative; height: 420px; }}
.map {{ width:100%; height:100%; }}
.dot {{ fill: {YELLOW}; opacity:.95; }}

</style>
""", unsafe_allow_html=True)

# ──────────────────────────────
# Data layer
# ──────────────────────────────
DEFAULT_DATA = {
    "kpis": {"youtube": 12345, "instagram": 4321, "tiktok": 6789},
    "map_dots": [
        {"x": 13, "y": 28, "r": 3.2},
        {"x": 32, "y": 30, "r": 1.2},
        {"x": 53, "y": 27, "r": 2.6},
        {"x": 67, "y": 29, "r": 2.8},
        {"x": 78, "y": 35, "r": 2.0},
        {"x": 86, "y": 48, "r": 2.4},
    ],
    "ministry": {"prayer": 15, "biblestudies": 8, "baptisms": 1, "weekly":[3,5,4,6,7,8,6,10,12,11,14,15]},
    "timeslots": [
        {"when":"Tue 1:00–3:00 PM","what":"LDE Ep.5 (Bahasa)"},
        {"when":"Wed 10:30–12:00","what":"Testimony shoot (John)"},
        {"when":"Fri 9:00–11:00 AM","what":"Music session — choir"},
    ],
    "daily_tasks": [
        {"title":"Outline next video","status":"Not Ready"},
        {"title":"Shoot testimony interview","status":"In Progress"},
        {"title":"Edit promo cut","status":"In Progress"},
        {"title":"Schedule weekend posts","status":"Done"},
    ],
    "weekly_tasks": [
        "Plan outreach event schedule",
        "Publish Bahasa caption pack",
        "Update media kit",
    ],
    "last_week_views": { "music": 18234, "reels": 24790 },
    "notes":"Tip: Add/override all data via Streamlit Secrets → key = DASHBOARD_JSON."
}

# Allow full JSON override from Secrets (paste JSON into DASHBOARD_JSON)
override = st.secrets.get("DASHBOARD_JSON")
if override:
    try:
        parsed = json.loads(override) if isinstance(override, str) else override
        DEFAULT_DATA.update(parsed)
    except Exception:
        st.warning("DASHBOARD_JSON is not valid JSON. Using defaults.")

data = DEFAULT_DATA

# Helpers for colored progress bars on daily tasks
def status_to_pct_and_class(status: str):
    s = (status or "").lower()
    if "progress" in s:
        return 55, "bar-yellow"
    if "done" in s or "complete" in s:
        return 100, "bar-green"
    return 15, "bar-red"

def progress_bar_html(pct: int, css_class: str):
    pct = max(0, min(100, int(pct)))
    return f'<div class="hbar"><span class="{css_class}" style="width:{pct}%"></span></div>'

# ──────────────────────────────
# Header
# ──────────────────────────────
left, right = st.columns([0.7, 0.3])
with left:
    st.markdown("## **LOUDVOICE**")
    st.caption("TV‑friendly dashboard • Streamlit Cloud • Black + Yellow theme")
with right:
    st.caption("Auto‑refresh your browser if needed • Use `?zoom=115` for larger UI")

st.write("")

# ──────────────────────────────
# KPI Row
# ──────────────────────────────
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown('<div class="card kpi">', unsafe_allow_html=True)
    st.markdown('<div class="icon">▶️</div>', unsafe_allow_html=True)
    st.markdown('<div><div class="kpi-label">YouTube Subscribers</div>'
                f'<p class="big">{data["kpis"]["youtube"]:,}</p></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="card kpi">', unsafe_allow_html=True)
    st.markdown('<div class="icon">📸</div>', unsafe_allow_html=True)
    st.markdown('<div><div class="kpi-label">Instagram Followers</div>'
                f'<p class="big">{data["kpis"]["instagram"]:,}</p></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c3:
    st.markdown('<div class="card kpi">', unsafe_allow_html=True)
    st.markdown('<div class="icon">🎵</div>', unsafe_allow_html=True)
    st.markdown('<div><div class="kpi-label">TikTok Followers</div>'
                f'<p class="big">{data["kpis"]["tiktok"]:,}</p></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# ──────────────────────────────
# Map (left) + Next Filming Timeslots (right)
# ──────────────────────────────
map_col, side_col = st.columns([0.62, 0.38])

with map_col:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Global Viewer Map</div>', unsafe_allow_html=True)

    dots_svg = "\n".join([f'<circle class="dot" cx="{pt["x"]}" cy="{pt["y"]}" r="{pt["r"]}"></circle>' for pt in data["map_dots"]])
    st.markdown(f"""
    <div class="map-wrap">
      <svg class="map" viewBox="0 0 100 50" preserveAspectRatio="xMidYMid meet" aria-label="world map">
        <rect x="2" y="14" width="96" height="22" rx="6" fill="#101319" stroke="rgba(255,255,255,0.04)"/>
        <!-- abstract continents -->
        <ellipse cx="28" cy="26" rx="18" ry="7" fill="#1a2030"></ellipse>
        <ellipse cx="60" cy="25" rx="22" ry="8" fill="#1a2030"></ellipse>
        <ellipse cx="82" cy="28" rx="10" ry="6" fill="#1a2030"></ellipse>
        {dots_svg}
      </svg>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with side_col:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Next Filming Timeslots</div>', unsafe_allow_html=True)
    for slot in data["timeslots"]:
        st.markdown(
            f'<div class="row-sm"><div><b>{slot["when"]}</b><div class="small">{slot["what"]}</div></div>'
            f'<span class="pill">Upcoming</span></div>',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# ──────────────────────────────
# Tasks Row (Daily with bars + Weekly list)
# ──────────────────────────────
daily_col, weekly_col = st.columns([0.55, 0.45])

with daily_col:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Daily Tasks</div>', unsafe_allow_html=True)
    for t in data["daily_tasks"]:
        pct, css = status_to_pct_and_class(t.get("status"))
        bar = progress_bar_html(pct, css)
        st.markdown(
            f'<div class="row-sm"><div>{t["title"]}<div class="small">{t["status"]}</div></div><div style="flex:1;max-width:360px">{bar}</div></div>',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)

with weekly_col:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Weekly Tasks</div>', unsafe_allow_html=True)
    for item in data["weekly_tasks"]:
        st.markdown(f'<div class="row-sm"><div>{item}</div><span class="pill">This week</span></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# ──────────────────────────────
# Last 7 Days Views + Ministry Tracker
# ──────────────────────────────
views_col, ministry_col = st.columns([0.55, 0.45])

with views_col:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Last 7 Days Views</div>', unsafe_allow_html=True)
    music = int(data["last_week_views"]["music"])
    reels = int(data["last_week_views"]["reels"])
    total = max(music, reels, 1)

    def views_bar(label, value, color):
        pct = int(100 * value / max(total, 1))
        return (f'<div class="row">'
                f'<div style="min-width:180px">{label}</div>'
                f'<div style="flex:1" class="views-bar"><span style="width:{pct}%; background:{color}"></span></div>'
                f'<div style="min-width:110px; text-align:right">{value:,}</div>'
                f'</div>')

    st.markdown(views_bar("Music Videos", music, "#ff8a34"), unsafe_allow_html=True)  # orange
    st.markdown(views_bar("Reels / Shorts", reels, "#4aa3ff"), unsafe_allow_html=True) # blue
    st.markdown('</div>', unsafe_allow_html=True)

with ministry_col:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Ministry Tracker</div>', unsafe_allow_html=True)
    a,b,c = st.columns(3)
    a.metric("Prayer Contacts", data["ministry"]["prayer"])
    b.metric("Bible Studies", data["ministry"]["biblestudies"])
    c.metric("Baptisms", data["ministry"]["baptisms"])
    st.markdown('<div class="small">Updated weekly</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.caption("Tip: Edit data without code via **Settings → Secrets → DASHBOARD_JSON**. Use `?zoom=115` if the TV is far.")
