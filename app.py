import json
from pathlib import Path
import streamlit as st
from textwrap import dedent
from streamlit.components.v1 import html as component_html

# ---------- helpers ----------
def md(md_str: str):
    st.markdown(dedent(md_str).strip(), unsafe_allow_html=True)

def render_world_map(dots_svg: str, bg_svg: str = None, height: int = 420):
    component_html(f"""
<div style="position:relative;height:{height}px">
  <style>
    .map-wrap svg {{ width:100%; height:100%; display:block; }}
    .dot {{ fill:#ffd54a; filter:drop-shadow(0 0 6px rgba(255,213,74,.55)); }}
  </style>
  <div class="map-wrap" style="position:relative;">
    {bg_svg or ''}
    <svg viewBox="0 0 100 50" preserveAspectRatio="xMidYMid meet"
         style="position:absolute;left:0;top:0">
      {dots_svg}
    </svg>
  </div>
</div>
""", height=height)

# ---------- page config ----------
st.set_page_config(page_title="LoudVoice Dashboard", page_icon="🎛️", layout="wide")

zoom = st.query_params.get("zoom", ["100"])[0]
st.markdown(f"<style>body {{ zoom: {zoom}% }}</style>", unsafe_allow_html=True)

YELLOW = "#ffd54a"
TEXT   = "#f5f7ff"
MUTED  = "#8b93b5"

st.markdown(f"""
<style>
header[data-testid="stHeader"]{{display:none;}}
#MainMenu{{visibility:hidden;}}
footer{{visibility:hidden;}}

html, body, [class^="css"] {{ background:#000 !important; color:{TEXT}!important; }}
.block-container {{ max-width: 1800px; padding-top: 16px; }}

h1,h2,h3,h4,h5,h6,.section-title,.kpi-label {{ color: {YELLOW}!important; }}

.card{{
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.35);
}}
.section-title{{ font-size:22px; font-weight:800; margin: 0 0 16px 0; }}
.row{{
  display:flex; align-items:center; justify-content:space-between;
  gap: 12px; padding: 12px 6px;
  border-bottom: 1px solid rgba(255,255,255,.07);
}}
.row:last-child{{ border-bottom:none; }}
.small {{ color:{MUTED}; font-size:12px; }}

.hbar{{ position:relative; height:12px; width:100%; background:#23283b; border-radius:6px; overflow:hidden; }}
.hbar > span{{ position:absolute; left:0; top:0; bottom:0; display:block; border-radius:6px; }}
.bar-red{{ background:#ff5a5f; }}
.bar-yellow{{ background:#ffd166; }}
.bar-green{{ background:#2ECC71; }}

.views-bar{{ height:14px; border-radius:7px; background:#23283b; overflow:hidden; }}
.views-bar > span{{ display:block; height:100%; }}
</style>
""", unsafe_allow_html=True)

# ---------- data ----------
DEFAULT_DATA = {
    "kpis": {"youtube": 15721, "instagram": 6050, "tiktok": 11032},
    "map_dots": [
        {"x": 13, "y": 28, "r": 3.2},
        {"x": 32, "y": 30, "r": 1.2},
        {"x": 53, "y": 27, "r": 2.6},
        {"x": 67, "y": 29, "r": 2.8},
        {"x": 78, "y": 35, "r": 2.0},
        {"x": 86, "y": 48, "r": 2.4},
    ],
    "ministry": {"prayer": 15, "biblestudies": 8, "baptisms": 1},
    "timeslots": [
        {"when":"Thu 2:00–4:00 PM","what":"Bahasa short — EP12","status":"Upcoming"},
        {"when":"Sat 9:30–11:00 AM","what":"Choir session","status":"Upcoming"},
        {"when":"Tue 3:00–5:00 PM","what":"Testimony w/ Mary","status":"Upcoming"},
    ],
    "tasks_daily": [
        {"task":"Edit EP12 subtitles","progress":"in progress"},
        {"task":"Schedule Reel upload","progress":"not ready"},
        {"task":"Reply to prayer requests","progress":"done"},
    ],
    "views": {"music": 3200, "reels": 5400}
}

# ---------- KPIs ----------
c1, c2, c3 = st.columns(3)
with c1:
    md(f"""<div class='card'>
    <h2 class='section-title'>YouTube</h2>
    <div class='row'><span>{DEFAULT_DATA['kpis']['youtube']} Subs</span></div>
    </div>""")
with c2:
    md(f"""<div class='card'>
    <h2 class='section-title'>Instagram</h2>
    <div class='row'><span>{DEFAULT_DATA['kpis']['instagram']} Followers</span></div>
    </div>""")
with c3:
    md(f"""<div class='card'>
    <h2 class='section-title'>TikTok</h2>
    <div class='row'><span>{DEFAULT_DATA['kpis']['tiktok']} Followers</span></div>
    </div>""")

# ---------- Main layout ----------
c1, c2 = st.columns([2,1])

with c1:
    md("""<div class='card'><h2 class='section-title'>Global Reach</h2>""")
    dots = ''.join([f"<circle class='dot' cx='{d['x']}' cy='{d['y']}' r='{d['r']}'></circle>" for d in DEFAULT_DATA['map_dots']])
    render_world_map(dots)
    md("</div>")

with c2:
    md("<div class='card'><h2 class='section-title'>Next Filming Timeslots</h2>")
    for slot in DEFAULT_DATA['timeslots']:
        md(f"<div class='row'><span>{slot['when']}</span><span>{slot['what']}</span></div>")
    md("</div>")

# ---------- Tasks with progress ----------
md("<div class='card'><h2 class='section-title'>Daily Tasks</h2>")
for t in DEFAULT_DATA['tasks_daily']:
    color = 'bar-red' if t['progress']=='not ready' else 'bar-yellow' if t['progress']=='in progress' else 'bar-green'
    width = '20%' if t['progress']=='not ready' else '60%' if t['progress']=='in progress' else '100%'
    md(f"""<div class='row'>
    <span>{t['task']}</span>
    <div class='hbar'><span class='{color}' style='width:{width}'></span></div>
    </div>""")
md("</div>")

# ---------- Weekly views ----------
md("<div class='card'><h2 class='section-title'>Weekly Views</h2>")
for name, val in DEFAULT_DATA['views'].items():
    color = '#42a5f5' if name=='music' else '#ab47bc'
    md(f"""<div class='row'>
    <span>{name.title()}</span>
    <div class='views-bar'><span style='width:{val/6000*100:.0f}%; background:{color}'></span></div>
    <span>{val}</span>
    </div>""")
md("</div>")
