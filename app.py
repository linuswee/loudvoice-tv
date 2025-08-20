# app.py — LoudVoice Dashboard (mock data, black/yellow theme)
import json
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import streamlit as st
from textwrap import dedent
from streamlit.components.v1 import html as component_html

# ----------------- helpers -----------------
def md(s: str):
    st.markdown(dedent(s).strip(), unsafe_allow_html=True)

def render_world_map(dots: List[Dict[str, float]], bg_svg: Optional[str], height: int = 360):
    """Render a subtle world background (if provided) and overlay dots for viewer locations."""
    if not bg_svg:
        # fallback "pill" background so the area never looks empty
        bg_svg = """
        <svg viewBox="0 0 100 48" preserveAspectRatio="xMidYMid meet">
          <rect x="3" y="10" width="94" height="28" rx="16"
                fill="#0c0f14" stroke="rgba(255,255,255,0.10)" stroke-width="0.5"/>
          <ellipse cx="30" cy="26" rx="22" ry="8" fill="#141a25"/>
          <ellipse cx="62" cy="24" rx="26" ry="9" fill="#141a25"/>
          <ellipse cx="84" cy="28" rx="12" ry="7" fill="#141a25"/>
        </svg>
        """
    circles = "".join([f"<circle class='dot' cx='{d['x']}' cy='{d['y']}' r='{d['r']}'></circle>" for d in dots])
    component_html(f"""
<div style="position:relative;height:{height}px">
  <style>
    .map-wrap svg {{ width:100%; height:100%; display:block; }}
    .dot {{ fill:#ffd54a; opacity:.95; filter:drop-shadow(0 0 6px rgba(255,213,74,.55)); }}
  </style>
  <div class="map-wrap" style="position:relative;">
    {bg_svg}
    <svg viewBox="0 0 100 48" preserveAspectRatio="xMidYMid meet"
         style="position:absolute;left:0;top:0">
      {circles}
    </svg>
  </div>
</div>
""", height=height)

# ----------------- page config -----------------
st.set_page_config(page_title="LoudVoice Dashboard", page_icon="🎛️", layout="wide")
zoom = st.query_params.get("zoom", ["100"])[0]
st.markdown(f"<style>body {{ zoom: {zoom}% }}</style>", unsafe_allow_html=True)

# colors
YELLOW = "#ffd54a"; TEXT = "#f5f7ff"; MUTED = "#9aa3bd"

# ----------------- global CSS -----------------
st.markdown(f"""
<style>
header[data-testid="stHeader"]{{display:none;}}
#MainMenu{{visibility:hidden;}}
footer{{visibility:hidden;}}

html, body {{ background:#000 !important; color:{TEXT}!important; }}
.block-container {{ max-width: 1820px; padding-top: 8px; }}

h1,h2,h3,h4,h5,h6,.section-title,.kpi-label {{ color:{YELLOW}!important; }}

.card{{
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 16px;
  padding: 22px 24px;
  box-shadow: 0 10px 32px rgba(0,0,0,.35);
}}
.section-title{{ font-size:20px; font-weight:800; margin: 0 0 12px 0; }}
.row{{ display:flex; justify-content:space-between; align-items:center;
      gap:12px; padding:10px 6px; border-bottom:1px solid rgba(255,255,255,.07);}}
.row:last-child{{ border-bottom:none; }}
.small{{ color:{MUTED}; font-size:12px; }}

/* metric/kpi */
.kpi{{ display:flex; flex-direction:column; gap:6px; }}
.kpi .value{{ font-size:44px; font-weight:800; line-height:1; }}

/* bars */
.hbar{{ position:relative; height:12px; width:100%; background:#202636; border-radius:6px; overflow:hidden; }}
.hbar>span{{ position:absolute; left:0; top:0; bottom:0; display:block; border-radius:6px; }}
.bar-red{{ background:#ff5a5f; }}
.bar-yellow{{ background:#ffd166; }}
.bar-green{{ background:#2ECC71; }}

.views-bar{{ height:14px; border-radius:7px; background:#202636; overflow:hidden; }}
.views-bar>span{{ display:block; height:100%; }}

/* map */
.map-wrap{{ position:relative; height:360px; }}
.map-wrap svg{{ width:100%; height:100%; display:block; }}
</style>
""", unsafe_allow_html=True)

# ----------------- assets -----------------
ASSETS = Path(__file__).parent / "assets"
WORLD_SVG = (ASSETS / "worldmap.svg").read_text(encoding="utf-8") if (ASSETS / "worldmap.svg").exists() else ""

# ----------------- mock data -----------------
data = {
    # row 1 metrics
    "youtube": {"subscribers": 15890, "total_views": 145_000_000},
    "instagram": {"followers": 6050, "total_views": 2_340_000},
    "tiktok": {"followers": 11032, "total_views": 9_450_000},

    # row 2
    "viewer_dots": [
        {"x": 12, "y": 30, "r": 3.2}, {"x": 24, "y": 28, "r": 1.8},
        {"x": 52, "y": 26, "r": 2.6}, {"x": 67, "y": 30, "r": 2.8},
        {"x": 78, "y": 36, "r": 2.0}, {"x": 86, "y": 46, "r": 2.2},
    ],
    "yt_last7": [23500, 27100, 24800, 30100, 28900, 33000, 35120],

    "ministry": {"prayer": 15, "biblestudies": 8, "baptisms": 1},

    # row 3
    "tasks": [
        {"title":"Outline next video","status":"Not Done"},
        {"title":"Shoot testimony interview","status":"In Progress"},
        {"title":"Edit podcast episode","status":"Done"},
        {"title":"Schedule weekend posts","status":"In Progress"},
    ],
    "timeslots": [
        {"day":"Tue", "time":"1:00–3:00 PM", "activity":"Worship Set"},
        {"day":"Wed", "time":"10:30–12:00", "activity":"Testimony Recording"},
        {"day":"Fri", "time":"9:00–10:30 AM", "activity":"Youth Reels"},
    ],
}

# ----------------- header -----------------
left, right = st.columns([0.7, 0.3])
with left:
    md("## <span style='letter-spacing:.12em;'>LOUDVOICE</span>")
with right:
    md(f"<div style='text-align:right;color:{YELLOW};font-weight:600'>{datetime.now().strftime('%B %d, %Y %I:%M %p')}</div>")

st.write("")

# ----------------- ROW 1: KPIs (3 columns) -----------------
c1, c2, c3 = st.columns(3)
with c1:
    md("<div class='card'>")
    md("<div class='section-title'>YouTube</div>")
    md(f"<div class='kpi'><div class='kpi-label'>Subscribers</div><div class='value'>{data['youtube']['subscribers']:,}</div></div>")
    md(f"<div class='kpi'><div class='kpi-label'>Total Views</div><div class='value'>{data['youtube']['total_views']:,}</div></div>")
    md("</div>")
with c2:
    md("<div class='card'>")
    md("<div class='section-title'>Instagram</div>")
    md(f"<div class='kpi'><div class='kpi-label'>Followers</div><div class='value'>{data['instagram']['followers']:,}</div></div>")
    md(f"<div class='kpi'><div class='kpi-label'>Total Views</div><div class='value'>{data['instagram']['total_views']:,}</div></div>")
    md("</div>")
with c3:
    md("<div class='card'>")
    md("<div class='section-title'>TikTok</div>")
    md(f"<div class='kpi'><div class='kpi-label'>Followers</div><div class='value'>{data['tiktok']['followers']:,}</div></div>")
    md(f"<div class='kpi'><div class='kpi-label'>Total Views</div><div class='value'>{data['tiktok']['total_views']:,}</div></div>")
    md("</div>")

st.write("")

# ----------------- ROW 2: Map / Last 7 Days / Ministry -----------------
r2c1, r2c2, r2c3 = st.columns([0.5, 0.25, 0.25])

with r2c1:
    md("<div class='card'><div class='section-title'>World Map – YouTube Viewers</div>")
    render_world_map(data["viewer_dots"], WORLD_SVG, 360)
    if not WORLD_SVG:
        st.caption("Add **assets/worldmap.svg** to show continent outlines.")
    md("</div>")

with r2c2:
    md("<div class='card'><div class='section-title'>YouTube Views (Last 7 Days)</div>")
    days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    total = max(1, max(data["yt_last7"]))
    for d, v in zip(days, data["yt_last7"]):
        pct = int(v/total*100)
        md(f"<div class='row'><div style='min-width:54px'>{d}</div>"
           f"<div class='views-bar' style='flex:1'><span style='width:{pct}%;background:#4aa3ff'></span></div>"
           f"<div style='min-width:90px;text-align:right'>{v:,}</div></div>")
    md("</div>")

with r2c3:
    m = data["ministry"]
    md("<div class='card'><div class='section-title'>Ministry Tracker</div>")
    a,b,c = st.columns(3)
    a.metric("Prayer", m["prayer"])
    b.metric("Studies", m["biblestudies"])
    c.metric("Baptisms", m["baptisms"])
    md("</div>")

st.write("")

# ----------------- ROW 3: Tasks / Timeslots -----------------
r3c1, r3c2 = st.columns([0.6, 0.4])

def status_pct(s: str) -> int:
    s = s.lower()
    return 100 if "done" in s else 60 if "progress" in s else 18

def status_class(s: str) -> str:
    s = s.lower()
    return "bar-green" if "done" in s else "bar-yellow" if "progress" in s else "bar-red"

with r3c1:
    md("<div class='card'><div class='section-title'>ClickUp Tasks (Upcoming)</div>")
    for t in data["tasks"]:
        md(f"<div class='row'><div>{t['title']}<div class='small'>{t['status']}</div></div>"
           f"<div style='flex:1;max-width:420px' class='hbar'><span class='{status_class(t['status'])}' style='width:{status_pct(t['status'])}%'></span></div></div>")
    md("</div>")

with r3c2:
    md("<div class='card'><div class='section-title'>Next Filming Timeslots</div>")
    for s in data["timeslots"]:
        md(f"<div class='row'><div><b>{s['day']}</b> <span class='small'>&nbsp;{s['time']}</span></div>"
           f"<div class='small'>{s['activity']}</div></div>")
    md("</div>")

st.caption("Mock data • TV friendly • Edit values in app.py or wire to API/Secrets later. Use **?zoom=115** for distance.")
