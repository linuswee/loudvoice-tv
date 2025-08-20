import streamlit as st
import plotly.graph_objects as go
import datetime

st.set_page_config(page_title="LoudVoice Dashboard", layout="wide")

# Custom CSS for styling
st.markdown("""
    <style>
        .main {background-color: #111;}
        h1 {font-size: 42px !important; font-weight: 800;}
        h2 {font-size: 28px !important;}
        h3 {font-size: 22px !important;}
        .stat-box {
            background: #1f2736; padding: 15px; border-radius: 10px;
            margin-bottom: 10px;
        }
        .bar {height: 12px; border-radius: 5px; margin-top: 5px;}
        .bar-red {background:#ff5a5f;}
        .bar-yellow {background:#ffd54a;}
        .bar-green {background:#2ecc71;}
        small {font-size:12px; color:#9aa3bd;}
    </style>
""", unsafe_allow_html=True)

# ---- Header ----
col1, col2 = st.columns([6,1])
with col1:
    st.markdown("<h1>LOUDVOICE</h1>", unsafe_allow_html=True)
with col2:
    now = datetime.datetime.now().strftime("%B %d, %Y %I:%M %p")
    st.markdown(f"<p style='text-align:right; color:grey;'>{now}</p>", unsafe_allow_html=True)


# ---- World Map (covers first 5 rows, col 1) ----
with st.container():
    st.subheader("🌍 World Map — YouTube Viewers")
    fig = go.Figure()

    fig.add_trace(go.Scattergeo(
        lon=[-95.7129, 101.9758, 151.2093, 37.6173, 78.9629],
        lat=[37.0902, 4.2105, -33.8688, 55.7558, 20.5937],
        text=["USA", "Malaysia", "Australia", "Russia", "India"],
        mode="markers",
        marker=dict(
            size=[40, 20, 15, 10, 25],
            color="#ffd54a",
            line=dict(color="#111", width=0.6)   # ✅ fixed
        )
    ))

    fig.update_geos(
        projection_type="natural earth",
        showcountries=True, showcoastlines=True, showland=True, 
        landcolor="#1f2736", oceancolor="#0e1117",
        bgcolor="#0e1117"
    )
    fig.update_layout(
        margin={"r":0,"t":0,"l":0,"b":0},
        paper_bgcolor="#0e1117",
        geo=dict(
            showframe=False,
            showcoastlines=True,
            projection_type="equirectangular"
        )
    )
    st.plotly_chart(fig, use_container_width=True)


# ---- Column 2 stacked ----
col_main = st.container()

with col_main:
    # 1st row col 2 -> Ministry Tracker
    st.subheader("⛪ Ministry Tracker")
    st.write("Prayer: 15")
    st.write("Studies: 8")
    st.write("Baptisms: 1")

    # 2nd row col 2 -> YouTube Stats
    st.subheader("▶️ YouTube Stats")
    st.markdown("**Subscribers:** 15,890")
    st.markdown("**Total Views:** 145,000,000")

    # 3rd row col 2 -> YouTube Views (Last 7 Days)
    st.subheader("📊 YouTube Views (Last 7 Days)")
    yt_views = {
        "Mon": 23500, "Tue": 27100, "Wed": 24800,
        "Thu": 30100, "Fri": 28900, "Sat": 33000, "Sun": 35120
    }
    max_val = max(yt_views.values())
    for day, val in yt_views.items():
        bar_width = int((val / max_val) * 100)
        st.markdown(
            f"{day} {val:,} <div style='background:#2e86de;width:{bar_width}%;' class='bar'></div>", 
            unsafe_allow_html=True
        )

    # 4th row col 2 -> Instagram Stats
    st.subheader("📸 Instagram Stats")
    st.markdown("**Followers:** 6,050")
    st.markdown("**Total Views:** 2,340,000")

    # 5th row col 2 -> TikTok Stats
    st.subheader("🎵 TikTok Stats")
    st.markdown("**Followers:** 11,032")
    st.markdown("**Total Views:** 9,450,000")


# ---- 3rd row, all columns ----
col1, col2 = st.columns(2)

with col1:
    st.subheader("✅ ClickUp Tasks (Upcoming)")
    tasks = {
        "Outline next video": "red",
        "Shoot testimony interview": "yellow",
        "Edit podcast episode": "green",
        "Schedule weekend posts": "yellow"
    }
    for task, status in tasks.items():
        st.markdown(
            f"{task} <div class='bar bar-{status}'></div>", 
            unsafe_allow_html=True
        )

with col2:
    st.subheader("🎬 Next Filming Timeslots")
    filming = [
        ("Tue 1:00–3:00 PM", "Worship Set"),
        ("Wed 10:30–12:00", "Testimony Recording"),
        ("Fri 9:00–10:30 AM", "Youth Reels")
    ]
    today = datetime.datetime.now().strftime("%B %d, %Y")
    st.markdown(f"<small>{today}</small>", unsafe_allow_html=True)
    for slot, activity in filming:
        st.write(f"{slot} — {activity}")
