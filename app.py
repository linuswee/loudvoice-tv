# app.py — LoudVoice Dashboard (desktop + mobile responsive)
# Layout: Left map • Right column = (1) Ministry (2) 3-up KPIs (3) 7‑day views
# Bottom row: ClickUp tasks + Next Filming (with day/date/time)

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="LoudVoice Dashboard", page_icon="🎛️", layout="wide")

# ─────────────────────────────────────────────────────────────
# URL switches (useful for TV/mobile): ?zoom=115&compact=1
# ─────────────────────────────────────────────────────────────
qp = st.query_params
ZOOM = qp.get("zoom", ["100"])[0]
COMPACT = qp.get("compact", ["0"])[0].lower() in ("1", "true", "yes")

# ─────────────────────────────────────────────────────────────
# Styles (desktop + responsive mobile)
# ─────────────────────────────────────────────────────────────
st.markdown(
f"""
<style>
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css');

/* Global + zoom for TV viewing */
html, body, [class^="css"] {{ background:#0b0f16 !important; color:#eef3ff }}
body {{ zoom: {ZOOM}% }}
header[data-testid="stHeader"], #MainMenu, footer {{ visibility: hidden; }}
.block-container {{ max-width: 1820px; padding-top: 8px; padding-bottom: 8px }}

/* Typography */
.title {{ color:#ffd54a; font-weight:850; font-size:32px; letter-spacing:.14em; margin:0 0 10px 0 }}
.timestamp {{ color:#ffd54a; font-size:12px; font-weight:700; text-align:right }}

/* Cards */
.card {{
  background: rgba(255,255,255,.03);
  border: 1px solid rgba(255,255,255,.10);
  border-radius: 12px;
  padding: 12px 14px;
  margin-bottom: 10px;
  box-shadow: 0 4px 12px rgba(0,0,0,.22);
}}
.section {{ color:#ffd54a; font-weight:800; font-size:15px; margin:2px 0 6px 0 }}

/* Compact KPI pieces */
.kpi-head {{ display:flex; align-items:center; gap:8px; margin-bottom:4px }}
.kpi-label {{ font-size:11px; color:#aab3cc; margin:0 }}
.kpi-value {{ font-size:24px; font-weight:800; margin:0 }}
.icon {{ font-size:16px; margin-right:6px }}
.small {{ font-size:12px; color:#9aa3bd }}

/* Aligned-bar grids */
.grid-views {{ display:grid; grid-template-columns:56px 1fr 76px; gap:10px; align-items:center; margin:4px 0 }}
.grid-tasks {{ display:grid; grid-template-columns:260px 1fr 70px; gap:10px; align-items:center; margin:6px 0 }}
.views-bar {{ height:10px; border-radius:6px; background:#1f2736; overflow:hidden }}
.views-bar > span {{ display:block; height:100%; background:#4aa3ff }}
.hbar {{ height:10px; border-radius:6px; background:#1f2736; overflow:hidden }}
.hbar > span {{ display:block; height:100% }}
.bar-green {{ background:#2ecc71 }} .bar-yellow {{ background:#ffd166 }} .bar-red {{ background:#ff5a5f }}

/* ---------- Responsive tweaks for phones/tablets ---------- */
@media (max-width: 1100px) {{
  .block-container {{ padding-left:8px; padding-right:8px; max-width:100% }}
  .title {{ font-size:26px; letter-spacing:.10em }}
  .timestamp {{ display:none }}
  /* Force Streamlit columns to stack */
  section.main > div:has(> div[data-testid="stHorizontalBlock"]) div[data-testid="column"] {{
    width:100% !important; flex:0 0 100% !important;
  }}
  .card {{ padding:10px 12px; border-radius:10px }}
  .kpi-value {{ font-size:20px }}
  .grid-views {{ grid-template-columns:48px 1fr 64px }}
  .grid-tasks {{ grid-template-columns: 1fr 1fr 64px }} /* name wraps; bar same width */
}}

/* Optional "compact" mode via ?compact=1 (also applies on desktop) */
{("""
@media (max-width: 4000px) {
  .title{font-size:26px}
  .kpi-value{font-size:20px}
  .card{padding:10px 12px}
}
""" if COMPACT else "")}
</style>
""",
unsafe_allow_html=True,
)

YELLOW = "#ffd54a"

# ─────────────────────────────────────────────────────────────
# Mock Data
# ─────────────────────────────────────────────────────────────
youtube = {"subs": 15_890, "total": 145_000_000}
instagram = {"followers": 6_050, "total": 2_340_000}
tiktok = {"followers": 11_032, "total": 9_450_000}
yt_last7 = [23_500, 27_100, 24_800, 30_100, 28_900, 33_000, 35_120]

geo_df = pd.DataFrame({
    "place": ["Malaysia","Philippines","United States","India","Kenya","Australia"],
    "lat":   [4.21, 12.88, 37.09, 20.59, -0.02, -25.27],
    "lon":   [101.98,121.77,-95.71, 78.96, 37.90, 133.77],
    "views": [22_000, 15_000, 52_000, 30_000, 12_000, 9_000],
})

ministry = {"prayer": 15, "studies": 8, "baptisms": 1}

tasks = [
    ("Outline next video", "Not Done"),
    ("Shoot testimony interview", "In Progress"),
    ("Edit podcast episode", "Done"),
    ("Schedule weekend posts", "In Progress"),
]

filming = [
    ("Tue, Aug 26, 2025", "1:00–3:00 PM", "Worship Set"),
    ("Wed, Aug 27, 2025", "10:30–12:00", "Testimony Recording"),
    ("Fri, Aug 29, 2025", "9:00–10:30 AM", "Youth Reels"),
]

# ─────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────
h1, h2 = st.columns([0.75, 0.25])
with h1:
    st.markdown("<div class='title'>LOUDVOICE</div>", unsafe_allow_html=True)
with h2:
    st.markdown(
        f"<div class='timestamp'>{datetime.now().strftime('%B %d, %Y %I:%M %p')}</div>",
        unsafe_allow_html=True,
    )

# Map height (slightly smaller if compact)
MAP_HEIGHT = 500 if not COMPACT else 430

# ─────────────────────────────────────────────────────────────
# Main two‑column layout
# ─────────────────────────────────────────────────────────────
left, right = st.columns([1.25, 0.75])

# Left — World Map
with left:
    st.markdown("<div class='card'><div class='section'>World Map — YouTube Viewers</div>", unsafe_allow_html=True)
    fig = go.Figure(
        go.Scattergeo(
            lat=geo_df["lat"],
            lon=geo_df["lon"],
            text=geo_df["place"] + " — " + geo_df["views"].map(lambda v: f"{v:,}"),
            mode="markers",
            marker=dict(
                size=(geo_df["views"] / 3500).clip(lower=6, upper=24),
                color="#ffd54a",
                line=dict(color="#111", width=0.6),
            ),
        )
    )
    fig.update_layout(
        geo=dict(
            showland=True,
            landcolor="#0b0f16",
            showcountries=True,
            countrycolor="rgba(255,255,255,.15)",
            showocean=True,
            oceancolor="#070a0f",
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=MAP_HEIGHT,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, theme=None)
    st.markdown("</div>", unsafe_allow_html=True)

# Right — Row1: Ministry, Row2: 3-up KPIs, Row3: 7‑day views
with right:
    # Row 1 — compact Ministry
    st.markdown(
        "<div class='card'><div class='section'><i class='fa-solid fa-hands-praying icon'></i>Ministry Tracker</div>",
        unsafe_allow_html=True,
    )
    a, b, c = st.columns(3)
    a.metric("Prayer", ministry["prayer"])
    b.metric("Studies", ministry["studies"])
    c.metric("Baptisms", ministry["baptisms"])
    st.markdown("</div>", unsafe_allow_html=True)

    # Row 2 — YouTube / Instagram / TikTok (side by side)
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='section'>Channel Stats</div>", unsafe_allow_html=True)
    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown("<div class='kpi-head'><i class='fab fa-youtube icon' style='color:#ff3d3d'></i><b>YouTube</b></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='kpi-label'>Subscribers</div><div class='kpi-value'>{youtube['subs']:,}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='kpi-label'>Total Views</div><div class='kpi-value'>{youtube['total']:,}</div>", unsafe_allow_html=True)
    with k2:
        st.markdown("<div class='kpi-head'><i class='fab fa-instagram icon' style='color:#e1306c'></i><b>Instagram</b></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='kpi-label'>Followers</div><div class='kpi-value'>{instagram['followers']:,}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='kpi-label'>Total Views</div><div class='kpi-value'>{instagram['total']:,}</div>", unsafe_allow_html=True)
    with k3:
        st.markdown("<div class='kpi-head'><i class='fab fa-tiktok icon'></i><b>TikTok</b></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='kpi-label'>Followers</div><div class='kpi-value'>{tiktok['followers']:,}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='kpi-label'>Total Views</div><div class='kpi-value'>{tiktok['total']:,}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Row 3 — YouTube Views (Last 7 Days) with aligned bars
    st.markdown("<div class='card'><div class='section'>YouTube Views (Last 7 Days)</div>", unsafe_allow_html=True)
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    maxv = max(yt_last7)
    for d, v in zip(days, yt_last7):
        pct = int((v / maxv) * 100)
        st.markdown(
            f"<div class='grid-views'>"
            f"<div>{d}</div>"
            f"<div class='views-bar'><span style='width:{pct}%'></span></div>"
            f"<div style='text-align:right'>{v:,}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# Bottom row: ClickUp + Next Filming
# ─────────────────────────────────────────────────────────────
b1, b2 = st.columns([1.2, 0.8])

with b1:
    st.markdown("<div class='card'><div class='section'>ClickUp Tasks (Upcoming)</div>", unsafe_allow_html=True)

    def pct(status: str) -> int:
        s = status.lower()
        return 100 if "done" in s else 50 if "progress" in s else 10

    def cls(status: str) -> str:
        s = status.lower()
        return "bar-green" if "done" in s else "bar-yellow" if "progress" in s else "bar-red"

    for name, status in tasks:
        st.markdown(
            f"<div class='grid-tasks'>"
            f"<div>{name}<div class='small'>{status}</div></div>"
            f"<div class='hbar'><span class='{cls(status)}' style='width:{pct(status)}%'></span></div>"
            f"<div style='text-align:right'>{pct(status)}%</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

with b2:
    st.markdown("<div class='card'><div class='section'>Next Filming Timeslots</div>", unsafe_allow_html=True)
    for daydate, time, label in filming:
        st.markdown(
            f"<div class='grid-tasks' style='grid-template-columns: 220px 1fr 170px;'>"
            f"<div><b>{daydate}</b><div class='small'>{time}</div></div>"
            f"<div></div>"
            f"<div style='color:{YELLOW}; text-align:right'>{label}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

st.caption(
    "Responsive layout: use ?zoom=115 for TV distance and ?compact=1 for tighter spacing on phones. "
    "Bars are aligned; filming shows day, date, and time."
)
