import json
import time
import streamlit as st

st.set_page_config(
    page_title="LoudVoice TV Dashboard",
    page_icon="🎛️",
    layout="wide",
)

# ---------- Secrets & Mock ----------
USE_MOCK = st.secrets.get("USE_MOCK", "1") == "1"  # default to ON so it always runs

# If later you add real keys, flip USE_MOCK to "0" in Streamlit Secrets and consume your APIs here:
YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY")
INSTAGRAM_ACCESS_TOKEN = st.secrets.get("INSTAGRAM_ACCESS_TOKEN")
TIKTOK_ACCESS_TOKEN = st.secrets.get("TIKTOK_ACCESS_TOKEN")

# ---------- Data Layer ----------
DEFAULT_DATA = {
    "kpis": {"youtube": 12345, "instagram": 4321, "tiktok": 6789},
    "trending": [
        {"title":"How to Share Your Testimony","value":95},
        {"title":"The Power of Prayer","value":72},
        {"title":"Overcoming Adversity","value":58},
        {"title":"Faith in Action","value":45},
        {"title":"The Importance of Service","value":33},
    ],
    "map_dots": [
        {"x":25, "y":55, "r":6},
        {"x":40, "y":50, "r":4},
        {"x":75, "y":48, "r":4},
        {"x":95, "y":43, "r":3},
        {"x":120, "y":52, "r":5},
        {"x":150, "y":50, "r":4},
        {"x":175, "y":57, "r":5},
    ],
    "ministry": {
        "prayer": 15,
        "biblestudies": 8,
        "baptisms": 1,
        "weekly": [3,5,4,6,7,8,9,6,10,12,11,14]
    },
    "tasks": [
        {"title":"Outline next video","status":"In Progress"},
        {"title":"Shoot testimony interview","status":"Today"},
        {"title":"Edit EP. 49 short","status":"To Do"},
        {"title":"Publish Bahasa caption pack","status":"Queued"},
    ],
    "notes": "This is your TV dashboard. Add real data later; for now it’s using mock values."
}

def load_data():
    # In the future, replace this with real fetches (YouTube/IG/TikTok/Sheets/ClickUp)
    # when USE_MOCK is False and secrets are present.
    return DEFAULT_DATA

# ---------- Styles ----------
st.markdown("""
<style>
:root{
  --bg:#0f1221; --panel:#161a31; --muted:#8b93b5; --text:#eef1ff; --accent:#5ab0ff;
}
html, body, [class^="css"]  { background-color: var(--bg) !important; color: var(--text) !important; }
.block-container{ padding-top: 1.4rem; padding-bottom: 0rem; }
.card{background: var(--panel); border: 1px solid #2b3362; border-radius: 14px; padding: 16px 18px;}
.big{ font-size: 46px; font-weight: 800; margin: 0; }
.kpi-label{ color: var(--muted); font-weight: 600; font-size: 14px; letter-spacing:.3px; }
.row{ display: flex; align-items: center; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,.08); }
.row:last-child{ border-bottom: none; }
.bar{ height: 8px; background:#2a3054; border-radius:5px; flex:1; margin-left:12px; overflow:hidden; }
.bar > span{ display:block; height:100%; background: var(--accent); }
.muted{ color: var(--muted); font-size: 12px; }
.pill{ font-size:12px; padding:4px 8px; border-radius:999px; background:#2a3054; color:#cdd3ff; }
.section-title{ margin:0 0 12px 0; font-size:18px; color:#d6dbff; letter-spacing:.3px; }
.map-wrap{ position: relative; height: 340px; }
.map{ width: 100%; height: 100%; }
.dot{ fill: var(--accent); opacity:.85; }
.spark{ width: 100%; height: 100px; }
</style>
""", unsafe_allow_html=True)

# ---------- Header ----------
col_title, col_actions = st.columns([0.7, 0.3])
with col_title:
    st.markdown("### 🎛️ LoudVoice Dashboard")
    st.caption("TV-friendly. Runs in Streamlit Cloud. Mock data by default.")

with col_actions:
    st.caption("Auto-refresh every 60s")
    st.button("Refresh now", on_click=lambda: None)

# Auto-refresh interval (no heavy calls here; safe)
st_autorefresh = st.experimental_rerun  # alias; not used directly
st.experimental_set_query_params(_=int(time.time()//60))  # forces rerun ~every minute

data = load_data()

# ---------- KPI Row ----------
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="kpi-label">YouTube Subscribers</div>', unsafe_allow_html=True)
    st.markdown(f'<p class="big">{data["kpis"]["youtube"]:,}</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="kpi-label">Instagram Followers</div>', unsafe_allow_html=True)
    st.markdown(f'<p class="big">{data["kpis"]["instagram"]:,}</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="kpi-label">TikTok Followers</div>', unsafe_allow_html=True)
    st.markdown(f'<p class="big">{data["kpis"]["tiktok"]:,}</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# ---------- Map ----------
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Global Viewer Map</div>', unsafe_allow_html=True)

# Simple abstract world with dots (no external libs)
svg_dots = "\n".join([
    f'<circle class="dot" cx="{pt["x"]}%" cy="{pt["y"]}%" r="{pt["r"]}"></circle>'
    for pt in data["map_dots"]
])
st.markdown(f"""
<div class="map-wrap">
  <svg class="map" viewBox="0 0 100 50" preserveAspectRatio="xMidYMid meet" aria-label="abstract world map">
    <rect x="0" y="15" width="100" height="20" fill="#1b2040" rx="6"></rect>
    <ellipse cx="28" cy="28" rx="18" ry="7" fill="#232a58"></ellipse>
    <ellipse cx="60" cy="27" rx="22" ry="8" fill="#232a58"></ellipse>
    <ellipse cx="82" cy="30" rx="10" ry="6" fill="#232a58"></ellipse>
    {svg_dots}
  </svg>
</div>
""", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# ---------- Trending + Ministry ----------
left, right = st.columns([0.6, 0.4])

with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Trending Videos by Region</div>', unsafe_allow_html=True)
    for item in data["trending"]:
        st.markdown(
            f'<div class="row"><div>{item["title"]}</div>'
            f'<div class="bar"><span style="width:{item["value"]}%"></span></div></div>',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Ministry Tracker</div>', unsafe_allow_html=True)
    cA, cB, cC = st.columns(3)
    cA.metric("Prayer Contacts", data["ministry"]["prayer"])
    cB.metric("Bible Studies", data["ministry"]["biblestudies"])
    cC.metric("Baptisms", data["ministry"]["baptisms"])

    # Simple sparkline SVG
    arr = data["ministry"]["weekly"]
    mx = max(arr) if arr else 1
    pts = " ".join([f"{i*100/(len(arr)-1):.2f},{100-(v/mx)*88-6:.2f}" for i, v in enumerate(arr)])
    st.markdown(f"""
    <svg class="spark" viewBox="0 0 100 100" preserveAspectRatio="none">
      <polygon fill="rgba(90,176,255,.18)" points="0,100 {pts} 100,100" />
      <polyline fill="none" stroke="#5ab0ff" stroke-width="1.5" points="{pts}" />
    </svg>
    <div class="muted">Last 12 weeks</div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# ---------- Tasks + Notes ----------
left2, right2 = st.columns([0.6, 0.4])

with left2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Today’s Tasks</div>', unsafe_allow_html=True)
    for t in data["tasks"]:
        st.markdown(
            f'<div class="row"><div>{t["title"]}</div><span class="pill">{t["status"]}</span></div>',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)

with right2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Notes</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='muted'>{data['notes']}</div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.caption("Tip: Put this app full screen on your TV (F11 or ⌃⌘F).")
