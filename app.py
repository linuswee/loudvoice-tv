# app.py  — LoudVoice TV Dashboard (fixed icons + map + padding)
import json
from pathlib import Path
from typing import Optional
import streamlit as st
from textwrap import dedent
from streamlit.components.v1 import html as component_html

# ----------------- helpers -----------------
def md(md_str: str) -> None:
    st.markdown(dedent(md_str).strip(), unsafe_allow_html=True)

def render_world_map(dots_svg: str, bg_svg: Optional[str], height: int = 420) -> None:
    """Render the map using components.html so SVG never appears as raw text."""
    if not bg_svg:
        # Soft “pill” fallback when assets/worldmap.svg is absent
        bg_svg = """
        <svg viewBox="0 0 100 50" preserveAspectRatio="xMidYMid meet">
          <rect x="4" y="12" width="92" height="26" rx="14"
                fill="#0e1116" stroke="rgba(255,255,255,0.12)" stroke-width="0.6"/>
          <ellipse cx="30" cy="28" rx="22" ry="8" fill="#171c28"/>
          <ellipse cx="63" cy="26" rx="26" ry="9" fill="#171c28"/>
          <ellipse cx="84" cy="30" rx="12" ry="7" fill="#171c28"/>
        </svg>
        """
    component_html(f"""
<div style="position:relative;height:{height}px">
  <style>
    .map-wrap svg {{ width:100%; height:100%; display:block; }}
    .dot {{ fill:#ffd54a; filter:drop-shadow(0 0 6px rgba(255,213,74,.55)); }}
  </style>
  <div class="map-wrap" style="position:relative;">
    {bg_svg}
    <svg viewBox="0 0 100 50" preserveAspectRatio="xMidYMid meet"
         style="position:absolute;left:0;top:0">
      {dots_svg}
    </svg>
  </div>
</div>
""", height=height)

# ----------------- page config -----------------
st.set_page_config(page_title="LoudVoice Dashboard", page_icon="🎛️", layout="wide")
zoom = st.query_params.get("zoom", ["100"])[0]
st.markdown(f"<style>body {{ zoom: {zoom}% }}</style>", unsafe_allow_html=True)

YELLOW = "#ffd54a"; TEXT = "#f5f7ff"; MUTED = "#8b93b5"

# Global CSS (padding + icon clamp)
st.markdown(f"""
<style>
header[data-testid="stHeader"]{{display:none;}}
#MainMenu{{visibility:hidden;}}
footer{{visibility:hidden;}}

html, body, [class^="css"] {{ background:#000 !important; color:{TEXT}!important; }}
.block-container {{ max-width: 1800px; padding-top: 16px; }}

h1,h2,h3,h4,h5,h6,.section-title,.kpi-label {{ color: {YELLOW}!important; }}

/* Cards & spacing */
.card {{
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 26px 28px;                 /* more breathing room */
  box-shadow: 0 10px 30px rgba(0,0,0,0.35);
}}
.section-title {{ font-size: 22px; font-weight: 800; margin: 0 0 16px 0; }}
.row, .row-sm {{
  display:flex; align-items:center; justify-content:space-between;
  gap: 12px; padding: 14px 8px;
  border-bottom: 1px solid rgba(255,255,255,.07);
}}
.row:last-child, .row-sm:last-child {{ border-bottom: none; }}
.small {{ color:{MUTED}; font-size:12px; }}

/* KPI icon clamp (prevents giant SVGs) */
.kpi {{ display:flex; gap:12px; align-items:center; }}
.kpi .icon {{
  width:44px; height:44px; min-width:44px; min-height:44px;
  border-radius:10px; overflow:hidden;
  display:flex; align-items:center; justify-content:center;
  background:#20242f; border:1px solid rgba(255,255,255,.06);
}}
.kpi .icon svg, .kpi .icon img {{ width:28px !important; height:28px !important; }}
.kpi .big {{ font-size:48px; font-weight:800; margin:0; }}
.kpi .kpi-label {{ font-size:14px; letter-spacing:.3px; font-weight:700; }}

/* Progress bars */
.hbar {{ position:relative; height:12px; width:100%; background:#23283b; border-radius:6px; overflow:hidden; }}
.hbar > span {{ position:absolute; left:0; top:0; bottom:0; display:block; border-radius:6px; }}
.bar-red {{ background:#ff5a5f; }}
.bar-yellow {{ background:#ffd166; }}
.bar-green {{ background:#2ECC71; }}

.views-bar {{ height:14px; border-radius:7px; background:#23283b; overflow:hidden; }}
.views-bar > span {{ display:block; height:100%; }}

.map-wrap {{ position:relative; height:420px; }}
.map-wrap svg {{ width:100%; height:100%; display:block; }}

.logo-wrap img, .logo-wrap svg {{ height:42px; }}
</style>
""", unsafe_allow_html=True)

# ----------------- assets -----------------
ASSETS = Path(__file__).parent / "assets"
def svg_str(name: str) -> str:
    p = ASSETS / name
    return p.read_text(encoding="utf-8") if p.exists() else ""

# Social icons (falls back to emoji if SVGs are missing)
YT = svg_str("youtube.svg") or "▶️"
IG = svg_str("instagram.svg") or "📸"
TT = svg_str("tiktok.svg") or "🎵"
WORLD = svg_str("worldmap.svg")        # optional; fallback background is used if missing
LOGO_SVG = svg_str("logo.svg") or svg_str("logo_placeholder.svg")

# ----------------- mock data -----------------
DATA = {
    "kpis": {"youtube": 15721, "instagram": 6050, "tiktok": 11032},
    "map_dots": [
        {"x": 13, "y": 28, "r": 3.2},
        {"x": 32, "y": 30, "r": 1.2},
        {"x": 53, "y": 27, "r": 2.6},
        {"x": 67, "y": 29, "r": 2.8},
        {"x": 78, "y": 35, "r": 2.0},
        {"x": 86, "y": 48, "r": 2.4},
    ],
    "timeslots": [
        {"when":"Thu 2:00–4:00 PM","what":"Bahasa short — EP12"},
        {"when":"Sat 9:30–11:00 AM","what":"Choir session"},
        {"when":"Tue 3:00–5:00 PM","what":"Testimony w/ Mary"},
    ],
    "daily": [
        {"title":"Outline next video","status":"Not Ready"},
        {"title":"Shoot testimony interview","status":"In Progress"},
        {"title":"Schedule weekend posts","status":"Done"},
    ],
    "weekly": ["Publish Bahasa caption pack","Update media kit","Plan outreach schedule"],
    "views": {"music": 20345, "reels": 28910},
}

# ----------------- header -----------------
left, right = st.columns([0.7, 0.3])
with left:
    if LOGO_SVG: md(f"<div class='logo-wrap'>{LOGO_SVG}</div>")
    md("## **LOUDVOICE**")
with right:
    st.caption("Tip: add **assets/worldmap.svg** for continents • use **?zoom=115** for TV")

st.write("")

# ----------------- KPI row (with icons) -----------------
k1, k2, k3 = st.columns(3)
for col, label, val, icon in [
    (k1, "YouTube Subscribers", DATA["kpis"]["youtube"], YT),
    (k2, "Instagram Followers", DATA["kpis"]["instagram"], IG),
    (k3, "TikTok Followers", DATA["kpis"]["tiktok"], TT),
]:
    with col:
        md("<div class='card kpi'>")
        md(f"<div class='icon'>{icon}</div>")
        md(f"<div><div class='kpi-label'>{label}</div><p class='big'>{val:,}</p></div>")
        md("</div>")

st.write("")

# ----------------- Map + Timeslots -----------------
mcol, scol = st.columns([0.62, 0.38])
with mcol:
    md("<div class='card'><div class='section-title'>Global Viewer Map</div>")
    circles = "".join([f"<circle class='dot' cx='{d['x']}' cy='{d['y']}' r='{d['r']}'></circle>" for d in DATA["map_dots"]])
    render_world_map(circles, WORLD if WORLD.strip() else None, 420)
    if not WORLD.strip():
        st.info("Using fallback map. Place an outline at **assets/worldmap.svg** to show continents.")
    md("</div>")

with scol:
    md("<div class='card'><div class='section-title'>Next Filming Timeslots</div>")
    for s in DATA["timeslots"]:
        md(f"<div class='row'><div><b>{s['when']}</b><div class='small'>{s['what']}</div></div><span class='small pill'>Upcoming</span></div>")
    md("</div>")

st.write("")

# ----------------- Tasks -----------------
dcol, wcol = st.columns([0.55, 0.45])
def status_class(s: str) -> str:
    s = s.lower()
    return "bar-green" if "done" in s else "bar-yellow" if "progress" in s else "bar-red"
def status_pct(s: str) -> int:
    s = s.lower()
    return 100 if "done" in s else 60 if "progress" in s else 18

with dcol:
    md("<div class='card'><div class='section-title'>Daily Tasks</div>")
    for t in DATA["daily"]:
        md(f"<div class='row'><div>{t['title']}<div class='small'>{t['status']}</div></div>"
           f"<div style='flex:1;max-width:360px' class='hbar'><span class='{status_class(t['status'])}' style='width:{status_pct(t['status'])}%'></span></div></div>")
    md("</div>")

with wcol:
    md("<div class='card'><div class='section-title'>Weekly Tasks</div>")
    for item in DATA["weekly"]:
        md(f"<div class='row'><div>{item}</div><span class='pill small'>This week</span></div>")
    md("</div>")

st.write("")

# ----------------- Views + Ministry -----------------
vcol, mcol2 = st.columns([0.55, 0.45])
with vcol:
    md("<div class='card'><div class='section-title'>Last 7 Days Views</div>")
    total = max(DATA["views"]["music"], DATA["views"]["reels"], 1)
    def vbar(label: str, value: int, color: str) -> str:
        pct = int(value/total*100)
        return (
            f"<div class='row'>"
            f"<div style='min-width:180px'>{label}</div>"
            f"<div class='views-bar' style='flex:1'><span style='width:{pct}%; background:{color}'></span></div>"
            f"<div style='min-width:110px; text-align:right'>{value:,}</div>"
            f"</div>"
        )
    md(vbar("Music Videos", DATA["views"]["music"], "#ff8a34"))
    md(vbar("Reels / Shorts", DATA["views"]["reels"], "#4aa3ff"))
    md("</div>")

with mcol2:
    md("<div class='card'><div class='section-title'>Ministry Tracker</div>")
    a, b, c = st.columns(3)
    a.metric("Prayer Contacts", 15)
    b.metric("Bible Studies", 8)
    c.metric("Baptisms", 1)
    md("<div class='small'>Updated weekly</div>")
    md("</div>")
