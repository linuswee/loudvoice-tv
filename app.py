import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="LoudVoice Dashboard", layout="wide")

# --- CUSTOM CSS (smaller fonts, compact layout) ---
st.markdown("""
    <style>
        body { zoom: 0.9; } /* make everything fit tighter */
        .big-font { font-size:22px !important; font-weight:600; }
        .med-font { font-size:18px !important; font-weight:500; }
        .small-font { font-size:14px !important; }
        .stMetric { font-size:18px !important; }
        .block-container { padding-top: 1rem; padding-bottom: 0rem; }
    </style>
    <!-- Load FontAwesome for icons -->
    <link rel="stylesheet"
          href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
""", unsafe_allow_html=True)

# --- MOCK DATA ---
yt_subs, yt_views = 15890, 145000000
ig_followers, ig_views = 6050, 2340000
tt_followers, tt_views = 11032, 9450000
prayers, studies, baptisms = 15, 8, 1
yt_last7 = [23500, 27100, 24800, 30100, 28900, 33000, 35120]

# --- HEADER ---
st.markdown("<h2 style='color:gold; font-weight:700;'>LOUDVOICE DASHBOARD</h2>", unsafe_allow_html=True)
st.markdown(f"<p style='color:gray;'>{datetime.now().strftime('%B %d, %Y %I:%M %p')}</p>", unsafe_allow_html=True)

# --- FIRST ROW ---
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("<i class='fab fa-youtube' style='color:red;'></i> <span class='big-font'>YouTube</span>", unsafe_allow_html=True)
    st.metric("Subscribers", f"{yt_subs:,}")
    st.metric("Total Views", f"{yt_views:,}")

with c2:
    st.markdown("<i class='fab fa-instagram' style='color:#E1306C;'></i> <span class='big-font'>Instagram</span>", unsafe_allow_html=True)
    st.metric("Followers", f"{ig_followers:,}")
    st.metric("Total Views", f"{ig_views:,}")

with c3:
    st.markdown("<i class='fab fa-tiktok' style='color:white;'></i> <span class='big-font'>TikTok</span>", unsafe_allow_html=True)
    st.metric("Followers", f"{tt_followers:,}")
    st.metric("Total Views", f"{tt_views:,}")

# --- SECOND ROW ---
c4, c5, c6 = st.columns([2,1.5,1])

# 🌍 World Map
with c4:
    st.markdown("<span class='big-font'>World Map - YouTube Viewers</span>", unsafe_allow_html=True)
    df = pd.DataFrame({
        "Country": ["Malaysia", "Philippines", "US", "India", "Kenya"],
        "Lat": [4.2105, 12.8797, 37.0902, 20.5937, -0.0236],
        "Lon": [101.9758, 121.7740, -95.7129, 78.9629, 37.9062],
        "Views": [20000, 15000, 50000, 30000, 10000]
    })
    fig = go.Figure(go.Scattergeo(
        lon = df["Lon"],
        lat = df["Lat"],
        text = df["Country"] + ": " + df["Views"].astype(str),
        mode = "markers",
        marker=dict(size=df["Views"]/2000, color="gold", line_color="black", line_width=0.5)
    ))
    fig.update_layout(
        geo=dict(showland=True, landcolor="black", bgcolor="rgba(0,0,0,0)"),
        margin={"r":0,"t":0,"l":0,"b":0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig, use_container_width=True)

# 📊 YouTube Views Last 7 Days
with c5:
    st.markdown("<span class='big-font'>YouTube Views (Last 7 Days)</span>", unsafe_allow_html=True)
    days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    views_df = pd.DataFrame({"Day": days, "Views": yt_last7})
    st.bar_chart(views_df.set_index("Day"))

# 🛐 Ministry Tracker
with c6:
    st.markdown("<span class='big-font'>Ministry Tracker</span>", unsafe_allow_html=True)
    st.metric("Prayer", prayers)
    st.metric("Studies", studies)
    st.metric("Baptisms", baptisms)

# --- THIRD ROW ---
c7, c8 = st.columns([2,1])

with c7:
    st.markdown("<span class='big-font'>ClickUp Tasks (Upcoming)</span>", unsafe_allow_html=True)
    tasks = {
        "Outline next video": "Not Done",
        "Shoot testimony interview": "In Progress",
        "Edit podcast episode": "Done",
        "Schedule weekend posts": "In Progress"
    }
    colors = {"Not Done": "red", "In Progress": "orange", "Done": "green"}
    for task, status in tasks.items():
        st.markdown(f"<span class='small-font'>{task}</span>", unsafe_allow_html=True)
        st.progress(1 if status=="Done" else (0.5 if status=="In Progress" else 0), text=status)

with c8:
    st.markdown("<span class='big-font'>Next Filming Timeslots</span>", unsafe_allow_html=True)
    filming = [
        ("Tue 1–3 PM", "Worship Set"),
        ("Wed 10:30–12", "Testimony Recording"),
        ("Fri 9–10:30 AM", "Youth Reels")
    ]
    for t, act in filming:
        st.markdown(f"<b>{t}</b> – {act}", unsafe_allow_html=True)
