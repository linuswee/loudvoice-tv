# app.py — LoudVoice Dashboard (layout tweaks per request)
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="LoudVoice Dashboard", page_icon="🎛️", layout="wide")

# ---------------- Styles (shorter headers, 3-col rows for bars) ----------------
st.markdown("""
<link rel="stylesheet"
      href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>
.block-container {max-width:1800px; padding-top:6px; padding-bottom:6px;}
html, body, [class^="css"] {background:#000 !important; color:#f5f7ff;}
header[data-testid="stHeader"], #MainMenu, footer{visibility:hidden;}

.title{color:#ffd54a; font-weight:800; font-size:20px; letter-spacing:.1em; margin:0;}
.section{color:#ffd54a; font-weight:700; font-size:14px; margin:2px 0 6px 0;} /* shorter */
.card{background:rgba(255,255,255,.03); border:1px solid rgba(255,255,255,.1);
      border-radius:12px; padding:10px 12px; margin-bottom:8px;
      box-shadow:0 4px 12px rgba(0,0,0,.22);}
.kpi-label{font-size:11px; color:#aab3cc; margin-bottom:0;}
.kpi-value{font-size:24px; font-weight:800;}

.icon{font-size:16px; margin-right:6px;}

/* 3-column grid rows so bars always start at same left edge */
.grid-views{display:grid; grid-template-columns: 56px 1fr 80px; gap:10px; align-items:center; margin:4px 0;}
.grid-tasks{display:grid; grid-template-columns: 260px 1fr 90px; gap:10px; align-items:center; margin:6px 0;}

.views-bar{height:10px; border-radius:5px; background:#1f2736; overflow:hidden;}
.views-bar>span{display:block; height:100%; background:#4aa3ff;}
.hbar{height:10px; border-radius:5px; background:#1f2736; overflow:hidden;}
.hbar>span{display:block; height:100%;}
.bar-green{background:#2ecc71;}
.bar-yellow{background:#ffd166;}
.bar-red{background:#ff5a5f;}
.small{font-size:12px; color:#9aa3bd;}
</style>
""", unsafe_allow_html=True)

YELLOW = "#ffd54a"

# ---------------- Mock data ----------------
yt = {"subs": 15890, "views": 145_000_000}
ig = {"follows": 6050, "views": 2_340_000}
tt = {"follows": 11032, "views": 9_450_000}
yt_last7 = [23500, 27100, 24800, 30100, 28900, 33000, 35120]
ministry = {"prayer": 15, "studies": 8, "baptisms": 1}
tasks = [
    ("Outline next video", "Not Done"),
    ("Shoot testimony interview", "In Progress"),
    ("Edit podcast episode", "Done"),
    ("Schedule weekend posts", "In Progress"),
]
timeslots = [
    ("Tue 1:00–3:00 PM", "Worship Set"),
    ("Wed 10:30–12:00", "Testimony Recording"),
    ("Fri 9:00–10:30 AM", "Youth Reels"),
]

# ---------------- Header ----------------
left, right = st.columns([0.75, 0.25])
with left:  st.markdown(f"<div class='title'>LOUDVOICE</div>", unsafe_allow_html=True)
with right: st.markdown(f"<div style='text-align:right;color:{YELLOW};font-size:12px;font-weight:600'>{datetime.now().strftime('%B %d, %Y %I:%M %p')}</div>", unsafe_allow_html=True)

# ---------------- Row 1: KPI cards ----------------
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("<div class='card'><div class='section'><i class='fab fa-youtube icon' style='color:#ff3d3d'></i>YouTube</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='kpi-label'>Subscribers</div><div class='kpi-value'>{yt['subs']:,}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='kpi-label'>Total Views</div><div class='kpi-value'>{yt['views']:,}</div></div>", unsafe_allow_html=True)
with c2:
    st.markdown("<div class='card'><div class='section'><i class='fab fa-instagram icon' style='color:#e1306c'></i>Instagram</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='kpi-label'>Followers</div><div class='kpi-value'>{ig['follows']:,}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='kpi-label'>Total Views</div><div class='kpi-value'>{ig['views']:,}</div></div>", unsafe_allow_html=True)
with c3:
    st.markdown("<div class='card'><div class='section'><i class='fab fa-tiktok icon'></i>TikTok</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='kpi-label'>Followers</div><div class='kpi-value'>{tt['follows']:,}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='kpi-label'>Total Views</div><div class='kpi-value'>{tt['views']:,}</div></div>", unsafe_allow_html=True)

# ---------------- Row 2: Map + YouTube last 7 days ----------------
m1, m2 = st.columns([1.4, 1.0])  # Ministry moves to Row 3; give views more room
with m1:
    st.markdown("<div class='card'><div class='section'>World Map — YouTube Viewers</div>", unsafe_allow_html=True)
    # Simple toned map for now (we can upgrade later)
    geo_df = pd.DataFrame({
        "place": ["Malaysia", "Philippines", "United States", "India", "Kenya", "Australia"],
        "lat": [4.21, 12.88, 37.09, 20.59, -0.02, -25.27],
        "lon": [101.98, 121.77, -95.71, 78.96, 37.90, 133.77],
        "views": [22000, 15000, 52000, 30000, 12000, 9000],
    })
    fig = go.Figure(go.Scattergeo(
        lat=geo_df["lat"], lon=geo_df["lon"],
        text=geo_df["place"] + " — " + geo_df["views"].map(lambda v: f"{v:,}"),
        mode="markers",
        marker=dict(size=(geo_df["views"]/3500).clip(lower=6, upper=22),
                    color="#ffd54a", line=dict(color="#111", width=0.6)),
        hovertemplate="%{text}<extra></extra>"
    ))
    fig.update_layout(geo=dict(showland=True, landcolor="#0b0f16",
                               showcountries=True, countrycolor="rgba(255,255,255,.15)",
                               showocean=True, oceancolor="#070a0f"),
                      margin=dict(l=0,r=0,t=0,b=0), height=300,
                      paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True, theme=None)
    st.markdown("</div>", unsafe_allow_html=True)

with m2:
    st.markdown("<div class='card'><div class='section'>YouTube Views (Last 7 Days)</div>", unsafe_allow_html=True)
    days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    maxv = max(yt_last7)
    for d,v in zip(days, yt_last7):
        pct = int((v/maxv)*100)
        st.markdown(
            f"<div class='grid-views'>"
            f"<div>{d}</div>"
            f"<div class='views-bar'><span style='width:{pct}%'></span></div>"
            f"<div style='text-align:right'>{v:,}</div>"
            f"</div>",
            unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------- Row 3: ClickUp Tasks (left) + Timeslots (middle) + Ministry (right) ----------------
b1, b2, b3 = st.columns([1.2, 0.8, 0.6])

def pct_for_status(status: str) -> int:
    status = status.lower()
    if "done" in status: return 100      # green
    if "progress" in status: return 50   # yellow
    return 10                            # red

def class_for_status(status: str) -> str:
    status = status.lower()
    if "done" in status: return "bar-green"
    if "progress" in status: return "bar-yellow"
    return "bar-red"

with b1:
    st.markdown("<div class='card'><div class='section'>ClickUp Tasks (Upcoming)</div>", unsafe_allow_html=True)
    for task, status in tasks:
        st.markdown(
            f"<div class='grid-tasks'>"
            f"<div>{task}<div class='small'>{status}</div></div>"
            f"<div class='hbar'><span class='{class_for_status(status)}' style='width:{pct_for_status(status)}%'></span></div>"
            f"<div style='text-align:right'>{pct_for_status(status)}%</div>"
            f"</div>",
            unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with b2:
    st.markdown("<div class='card'><div class='section'>Next Filming Timeslots</div>", unsafe_allow_html=True)
    for t, label in timeslots:
        st.markdown(f"<div class='grid-tasks' style='grid-template-columns: 160px 1fr 160px;'>"
                    f"<div>{t}</div>"
                    f"<div></div>"
                    f"<div style='color:{YELLOW}; text-align:right'>{label}</div>"
                    f"</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with b3:
    st.markdown("<div class='card'><div class='section'>Ministry Tracker</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='grid-tasks' style='grid-template-columns: 1fr 1fr 1fr;'>"
                f"<div><div class='small'>Prayer</div><div class='kpi-value'>{ministry['prayer']}</div></div>"
                f"<div><div class='small'>Studies</div><div class='kpi-value'>{ministry['studies']}</div></div>"
                f"<div><div class='small'>Baptisms</div><div class='kpi-value'>{ministry['baptisms']}</div></div>"
                f"</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.caption("Headers shortened • Ministry moved to row 3 • Bars aligned with 3-column grids • Task bar widths: red 10%, yellow 50%, green 100%.")
