# app.py — LoudVoice Dashboard (Compact, Mock Data)
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

# ---------------- Page config ----------------
st.set_page_config(page_title="LoudVoice Dashboard", page_icon="🎛️", layout="wide")

# ---------------- Global styles (compact) ----------------
st.markdown("""
<link rel="stylesheet"
      href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">

<style>
.block-container {max-width:1800px; padding-top:6px; padding-bottom:6px;}
.title{color:#ffd54a; font-weight:800; font-size:22px; letter-spacing:.1em;}
.section{color:#ffd54a; font-weight:700; font-size:15px; margin-bottom:8px;}
.card{background:rgba(255,255,255,.03); border:1px solid rgba(255,255,255,.1);
      border-radius:12px; padding:10px 12px; margin-bottom:10px;
      box-shadow:0 4px 12px rgba(0,0,0,.25);}
.kpi-label{font-size:11px; color:#aaa; margin-bottom:2px;}
.kpi-value{font-size:24px; font-weight:800;}
.row{display:flex; justify-content:space-between; align-items:center; gap:8px;}
.views-bar{height:10px; border-radius:5px; background:#1f2736; overflow:hidden;}
.views-bar>span{display:block; height:100%; background:#4aa3ff;}
.hbar{height:8px; background:#1f2736; border-radius:5px; overflow:hidden;}
.hbar>span{display:block; height:100%;}
.bar-green{background:#2ecc71;} .bar-yellow{background:#ffd166;} .bar-red{background:#ff5a5f;}
.icon{font-size:16px; margin-right:6px;}
html, body, [class^="css"] {background:#000 !important; color:#f5f7ff;}
header[data-testid="stHeader"], #MainMenu, footer{visibility:hidden;}
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
with left:
    st.markdown(f"<div class='title'>LOUDVOICE</div>", unsafe_allow_html=True)
with right:
    st.markdown(f"<div style='text-align:right;color:{YELLOW};font-size:12px;font-weight:600'>"
                f"{datetime.now().strftime('%B %d, %Y %I:%M %p')}</div>", unsafe_allow_html=True)

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

# ---------------- Row 2: Map, views, ministry ----------------
m1, m2, m3 = st.columns([2, 1.2, 0.8])

with m1:
    st.markdown("<div class='card'><div class='section'>World Map — YouTube Viewers</div>", unsafe_allow_html=True)
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
        marker=dict(size=(geo_df["views"]/3000).clip(lower=6, upper=24),
                    color="#ffd54a", line=dict(color="#111", width=0.6)),
        hovertemplate="%{text}<extra></extra>"
    ))
    fig.update_layout(geo=dict(showland=True, landcolor="#0b0f16",
                               showcountries=True, countrycolor="rgba(255,255,255,.15)",
                               showocean=True, oceancolor="#070a0f"),
                      margin=dict(l=0,r=0,t=0,b=0), height=280,
                      paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True, theme=None)
    st.markdown("</div>", unsafe_allow_html=True)

with m2:
    st.markdown("<div class='card'><div class='section'>YouTube Views (Last 7 Days)</div>", unsafe_allow_html=True)
    days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    maxv = max(yt_last7)
    for d,v in zip(days, yt_last7):
        pct = int((v/maxv)*100)
        st.markdown(f"<div class='row'><div>{d}</div>"
                    f"<div class='views-bar' style='flex:1'><span style='width:{pct}%'></span></div>"
                    f"<div>{v:,}</div></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with m3:
    st.markdown("<div class='card'><div class='section'>Ministry Tracker</div>", unsafe_allow_html=True)
    st.markdown(f"Prayer: {ministry['prayer']}<br>Studies: {ministry['studies']}<br>Baptisms: {ministry['baptisms']}", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------- Row 3: Tasks + Filming ----------------
b1, b2 = st.columns([1.3, 0.7])
with b1:
    st.markdown("<div class='card'><div class='section'>ClickUp Tasks (Upcoming)</div>", unsafe_allow_html=True)
    for task, status in tasks:
        color = "bar-red" if status=="Not Done" else "bar-yellow" if status=="In Progress" else "bar-green"
        st.markdown(f"<div class='row'><div>{task}</div>"
                    f"<div class='hbar' style='flex:1'><span class='{color}' style='width:70%'></span></div></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with b2:
    st.markdown("<div class='card'><div class='section'>Next Filming Timeslots</div>", unsafe_allow_html=True)
    for t, label in timeslots:
        st.markdown(f"<div class='row'><div>{t}</div><div style='color:{YELLOW}'>{label}</div></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
