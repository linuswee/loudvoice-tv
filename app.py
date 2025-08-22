__LV_VERSION__ = "v3.1b-cards-alignedbars (sha:0523c1c9)"

# app.py — LoudVoice Dashboard (cards + aligned bars layout)
import os
import json
from datetime import datetime, timedelta
import pandas as pd
import requests
import streamlit as st
import plotly.graph_objects as go
# === [ANCHOR] IMPORTS END ===

# Optional Google libs (only needed for YouTube Analytics true 7-day + countries)
GOOGLE_OK = True
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
except Exception:
    GOOGLE_OK = False

# -------------------------------
# Page config & compact helpers
# -------------------------------
st.set_page_config(page_title="LOUDVOICE", page_icon="📊", layout="wide")

qp = st.query_params
ZOOM = qp.get("zoom", ["100"])[0]
COMPACT = qp.get("compact", ["0"])[0].lower() in ("1", "true", "yes")
st.markdown(f"<style>body{{zoom:{ZOOM}%}}</style>", unsafe_allow_html=True)

# -------------------------------
# Styles
# -------------------------------
st.markdown(
    """
    <style>
    @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css');
    html, body, [class^="css"] { background:#0b0f16 !important; color:#eef3ff }
    header[data-testid="stHeader"], #MainMenu, footer { visibility:hidden; }
    .block-container { max-width:1820px; padding-top:8px; padding-bottom:10px }
    .title { color:#ffd54a; font-weight:900; font-size:34px; letter-spacing:.12em; margin:0 0 6px 0 }
    .timestamp { color:#ffd54a; font-size:12px; font-weight:700; text-align:right }
    .card { background:rgba(255,255,255,.03); border:1px solid rgba(255,255,255,.10);
            border-radius:12px; padding:10px 14px; margin-bottom:14px; box-shadow:0 4px 12px rgba(0,0,0,.22); }
    .section { color:#ffd54a; font-weight:800; font-size:15px; margin:0 0 8px 0 }
    .mini-grid{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px }
    .mini-card{ background:rgba(255,255,255,.03); border:1px solid rgba(255,255,255,.10);
                border-radius:10px; padding:8px 10px; text-align:center }
    .mini-label{ font-size:11px; color:#aab3cc; margin:0 }
    .mini-value{ font-size:22px; font-weight:800; margin:2px 0 0 }
    .kpi-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px }
    .kpi-card { background:rgba(255,255,255,.03); border:1px solid rgba(255,255,255,.10); border-radius:10px; padding:10px 12px; }
    .kpi-card .kpi-head{ display:flex; align-items:center; gap:8px; margin-bottom:4px }
    .kpi-card .icon{ font-size:14px; margin-right:6px }
    .kpi-card .kpi-name{ font-size:14px; font-weight:800 }
    .kpi-card .kpi-label{ font-size:10px; color:#aab3cc; margin:0 }
    .kpi-card .kpi-value{ font-size:18px; font-weight:800; margin:0 }
    .grid-views{ display:grid; grid-template-columns:56px 1fr 76px; gap:10px; align-items:center; margin:4px 0 }
    .views-bar{ height:10px; border-radius:6px; background:#1f2736; overflow:hidden }
    .views-bar>span{ display:block; height:100%; background:#4aa3ff }
    .grid-tasks-2{ display:grid; grid-template-columns:1fr 1.1fr; gap:12px; align-items:center; margin:6px 0 }
    .hbar{ height:10px; border-radius:6px; background:#1f2736; overflow:hidden }
    .hbar>span{ display:block; height:100% }
    .bar-green{ background:#2ecc71 } .bar-yellow{ background:#ffd166 } .bar-red{ background:#ff5a5f }
    .small { font-size:12px; color:#9aa3bd }
    .film-row{ display:grid; grid-template-columns: 1fr auto; gap:12px; align-items:center; padding:6px 0; }
    .film-right{ color:#ffd54a; white-space:nowrap }
    @media (max-width:1100px){
      .block-container{ padding-left:8px; padding-right:8px; max-width:100% }
      .title{ font-size:28px; letter-spacing:.10em } .timestamp{ display:none }
      section.main > div:has(> div[data-testid="stHorizontalBlock"]) div[data-testid="column"]{
        width:100% !important; flex:0 0 100% !important;
      }
      .card{ padding:8px 10px; border-radius:10px } .kpi-grid{ gap:10px }
      .kpi-card{ padding:8px 10px } .kpi-card .kpi-value{ font-size:16px } .kpi-card .icon{ font-size:13px }
      .grid-views{ grid-template-columns:48px 1fr 64px }
    }
    </style>
    """,
    unsafe_allow_html=True,
)
# === [ANCHOR] STYLES END ===

# -------------------------------
# Helpers & Data calls
# -------------------------------
def fmt_num(n: int) -> str:
    if n >= 1_000_000_000:
        v = n / 1_000_000_000
        return (f"{v:.1f}".rstrip("0").rstrip(".")) + "B"
    if n >= 1_000_000:
        v = n / 1_000_000
        return (f"{v:.1f}".rstrip("0").rstrip(".")) + "M"
    if n >= 1_000:
        v = n / 1_000
        return (f"{v:.1f}".rstrip("0").rstrip(".")) + "K"
    return f"{n}"

@st.cache_data(ttl=300)
def http_get(url, params=None, headers=None):
    r = requests.get(url, params=params, headers=headers, timeout=25)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=300)
def yt_channel_stats(api_key: str, channel_id: str):
    url = "https://www.googleapis.com/youtube/v3/channels"
    p = {"part": "statistics", "id": channel_id, "key": api_key}
    data = http_get(url, p)
    items = data.get("items", [])
    if not items:
        raise RuntimeError("No channel found for the given ID/API key.")
    stats = items[0]["statistics"]
    return {"subs": int(stats.get("subscriberCount", 0)), "total": int(stats.get("viewCount", 0))}

@st.cache_data(ttl=300)
def yt_analytics_lastN_and_countries(client_id, client_secret, refresh_token, days=28):
    if not GOOGLE_OK:
        raise RuntimeError("Google client libraries unavailable.")
    creds = Credentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/yt-analytics.readonly"],
    )
    if not creds.valid:
        creds.refresh(Request())
    analytics = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)

    end_date = datetime.utcnow().date()
    # inclusive range → for N days, subtract (N-1)
    start_date = end_date - timedelta(days=days - 1)

    daily = analytics.reports().query(
        ids="channel==MINE",
        startDate=start_date.isoformat(),
        endDate=end_date.isoformat(),
        metrics="views",
        dimensions="day",
        sort="day",
    ).execute()

    country = analytics.reports().query(
        ids="channel==MINE",
        startDate=start_date.isoformat(),
        endDate=end_date.isoformat(),
        metrics="views",
        dimensions="country",
        sort="-views",
        maxResults=200,
    ).execute()

    daily_vals = [int(row[1]) for row in daily.get("rows", [])]
    country_rows = country.get("rows", []) or []
    cdf = pd.DataFrame(country_rows, columns=["country", "views"])
    if not cdf.empty:
        cdf["views"] = cdf["views"].astype(int)
    return daily_vals, cdf

@st.cache_data
def country_centroids():
    data = [
        ("US", 37.09, -95.71), ("MY", 4.21, 101.98), ("PH", 12.88, 121.77),
        ("IN", 20.59, 78.96), ("KE", -0.02, 37.90), ("AU", -25.27, 133.77),
        ("ID", -0.79, 113.92), ("SG", 1.29, 103.85), ("GB", 55.38, -3.43),
        ("CA", 56.13, -106.35), ("NG", 9.08, 8.68), ("BR", -14.23, -51.92),
        ("DE", 51.17, 10.45), ("FR", 46.23, 2.21), ("JP", 36.20, 138.25),
        ("KR", 35.91, 127.76), ("TH", 15.87, 100.99), ("VN", 14.06, 108.28),
        ("MX", 23.63, -102.55), ("ES", 40.46, -3.75),
    ]
    return pd.DataFrame(data, columns=["country", "lat", "lon"])

# -------------------------------
# Mock data (when live calls fail)
# -------------------------------
MOCK = {
    "yt_subs": 30_800, "yt_total": 5_991_195,
    "yt_last7": [23500, 27100, 24800, 30100, 28900, 33000, 35120],
    "yt_countries": pd.DataFrame({"country":["US","MY","PH","IN","KE","AU"], "views":[52000,22000,15000,30000,12000,9000]}),
    "ig_followers": 6_000, "ig_views7": 42_300,
    "tt_followers": 11_000, "tt_views7": 57_900,
    "ministry": {"prayer": 15, "studies": 8, "baptisms": 1},
    "tasks": [
        ("Shoot testimony interview", "In Progress"),
        ("Schedule weekend posts", "In Progress"),
        ("Outline next video", "Not Done"),
        ("Edit podcast episode", "Done"),
    ],
    "filming": [
        ("Tue, Aug 26, 2025", "1:00–3:00 PM", "Worship Set"),
        ("Wed, Aug 27, 2025", "10:30–12:00", "Testimony Recording"),
        ("Fri, Aug 29, 2025", "9:00–10:30 AM", "Youth Reels"),
    ],
}

def task_pct(status: str) -> int:
    s = status.lower()
    return 100 if "done" in s else 50 if "progress" in s else 10

def task_cls(status: str) -> str:
    s = status.lower()
    return "bar-green" if "done" in s else "bar-yellow" if "progress" in s else "bar-red"

# -------------------------------
# Fetch live data (with fallbacks)
# -------------------------------
youtube = {"subs": MOCK["yt_subs"], "total": MOCK["yt_total"]}
yt_last7_vals = MOCK["yt_last7"]
yt_country_df = MOCK["yt_countries"]

yt_api_key = st.secrets.get("YOUTUBE_API_KEY")
yt_channel_id = st.secrets.get("YT_PRIMARY_CHANNEL_ID") or st.secrets.get("YOUTUBE_CHANNEL_ID")

if yt_api_key and yt_channel_id:
    try:
        live = yt_channel_stats(yt_api_key, yt_channel_id)
        youtube = {"subs": live["subs"], "total": live["total"]}
    except Exception:
        pass

yt_client_id = st.secrets.get("YT_CLIENT_ID")
yt_client_secret = st.secrets.get("YT_CLIENT_SECRET")
yt_refresh_token = st.secrets.get("YT_REFRESH_TOKEN")

analytics_ok = False
if yt_client_id and yt_client_secret and yt_refresh_token:
    try:
        DAYS_FOR_MAP = 28
        lst7, cdf = yt_analytics_lastN_and_countries(
            yt_client_id, yt_client_secret, yt_refresh_token, days=DAYS_FOR_MAP)
        if lst7:
            yt_last7_vals = lst7
        if cdf is not None and not cdf.empty:
            yt_country_df = cdf
        analytics_ok = True
    except Exception:
        analytics_ok = False

# IG / TT (still optional placeholders)
ig = {"followers": st.secrets.get("IG_FOLLOWERS", MOCK["ig_followers"]), "views7": st.secrets.get("IG_VIEWS7", MOCK["ig_views7"])}
tt = {"followers": st.secrets.get("TT_FOLLOWERS", MOCK["tt_followers"]), "views7": st.secrets.get("TT_VIEWS7", MOCK["tt_views7"])}

ministry = MOCK["ministry"]
tasks = sorted(MOCK["tasks"], key=lambda t: 1 if "done" in t[1].lower() else 0)
filming = MOCK["filming"]

# Map dataframe
try:
    cent = country_centroids()
    map_df = yt_country_df.merge(cent, on="country", how="left").dropna()
except Exception:
    map_df = MOCK["yt_countries"].merge(country_centroids(), on="country", how="left").dropna()
# === [ANCHOR] DATA FETCHERS END ===

# -------------------------------
# Header
# -------------------------------
t1, t2 = st.columns([0.75, 0.25])
with t1:
    st.markdown("<div class='title'>LOUDVOICE</div>", unsafe_allow_html=True)
with t2:
    now = datetime.now().strftime('%B %d, %Y %I:%M %p')
    st.markdown(f"<div class='timestamp'>{now}</div>", unsafe_allow_html=True)

if not analytics_ok:
    st.info("Using mock for YT 7‑day & country (Analytics call failed or not configured).")

MAP_HEIGHT = 340 if not COMPACT else 260
# === [ANCHOR] LAYOUT: HEADER END ===

# -------------------------------
# Main layout
# -------------------------------
left, right = st.columns([1.25, 0.75])

with left:
    st.markdown("<div class='card'><div class='section'>World Map — YouTube Viewers (True, last 28 days)</div>", unsafe_allow_html=True)
    fig = go.Figure(
        go.Scattergeo(
            lat=map_df["lat"],
            lon=map_df["lon"],
            text=map_df["country"] + " — " + map_df["views"].map(lambda v: fmt_num(int(v))),
            mode="markers",
            marker=dict(
                size=(map_df["views"] / max(map_df["views"].max(), 1) * 22).clip(lower=6, upper=22),
                color="#ffd54a",
                line=dict(color="#111", width=0.6),
            ),
        )
    )
    fig.update_layout(
        geo=dict(showland=True, landcolor="#0b0f16",
                 showcountries=True, countrycolor="rgba(255,255,255,.15)",
                 showocean=True, oceancolor="#070a0f"),
        margin=dict(l=0, r=0, t=0, b=0),
        height=MAP_HEIGHT,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, theme=None, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)
# === [ANCHOR] LAYOUT: MAP CARD END ===

with right:
    # Ministry tracker (3 columns)
    st.markdown("<div class='card'><div class='section'>Ministry Tracker</div>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="mini-grid">
          <div class="mini-card"><div class="mini-label">Prayer</div><div class="mini-value">{ministry['prayer']}</div></div>
          <div class="mini-card"><div class="mini-label">Studies</div><div class="mini-value">{ministry['studies']}</div></div>
          <div class="mini-card"><div class="mini-label">Baptisms</div><div class="mini-value">{ministry['baptisms']}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)
# === [ANCHOR] LAYOUT: MINISTRY CARD END ===

    # Channel stats (YT/IG/TT)
    st.markdown("<div class='card'><div class='section'>Channel Stats</div>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="kpi-grid">
          <div class="kpi-card">
            <div class="kpi-head"><i class="fab fa-youtube icon" style="color:#ff3d3d"></i><span class="kpi-name">YT</span></div>
            <div class="kpi-label">Subs</div><div class="kpi-value">{fmt_num(youtube['subs'])}</div>
            <div class="kpi-label">Total</div><div class="kpi-value">{fmt_num(youtube['total'])}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-head"><i class="fab fa-instagram icon" style="color:#e1306c"></i><span class="kpi-name">IG</span></div>
            <div class="kpi-label">Follows</div><div class="kpi-value">{fmt_num(ig['followers'])}</div>
            <div class="kpi-label">7‑day Views</div><div class="kpi-value">{fmt_num(ig['views7'])}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-head"><i class="fab fa-tiktok icon"></i><span class="kpi-name">TT</span></div>
            <div class="kpi-label">Follows</div><div class="kpi-value">{fmt_num(tt['followers'])}</div>
            <div class="kpi-label">7‑day Views</div><div class="kpi-value">{fmt_num(tt['views7'])}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)
# === [ANCHOR] LAYOUT: CHANNEL STATS CARD END ===

    # Last 7 days aligned bars — newest first label order (YTD, Tue, Mon, Sun, Sat, Fri, Thu)
    st.markdown("<div class='card'><div class='section'>YouTube Views (Last 7 Days)</div>", unsafe_allow_html=True)
    # Build labels order
    labels = ["YTD", "Tue", "Mon", "Sun", "Sat", "Fri", "Thu"]  # as per agreed quirky order
    # Use yt_last7_vals (list oldest->newest). We'll reverse to newest->oldest then map into labels end-to-start.
    vals = yt_last7_vals[:]
    if len(vals) >= 7:
        vals = vals[-7:]  # ensure 7
    maxv = max(vals) if vals else 1
    # For display, align biggest bar to 100%
    display_pairs = list(zip(labels[::-1], (vals + [vals[-1]]*7)[:7]))[::-1]
    for d, v in display_pairs:
        pct = int((v / maxv) * 100) if maxv else 0
        st.markdown(
            f"<div class='grid-views'>"
            f"<div>{d}</div>"
            f"<div class='views-bar'><span style='width:{pct}%'></span></div>"
            f"<div style='text-align:right'>{fmt_num(int(v))}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)
# === [ANCHOR] LAYOUT: 7DAY VIEWS CARD END ===

# -------------------------------
# Bottom: ClickUp tasks + Filming
# -------------------------------
b1, b2 = st.columns([1.2, 0.8])

with b1:
    st.markdown("<div class='card'><div class='section'>ClickUp Tasks (Upcoming)</div>", unsafe_allow_html=True)
    for name, status in tasks:
        st.markdown(
            f"<div class='grid-tasks-2'>"
            f"<div>{name}<div class='small'>{status}</div></div>"
            f"<div class='hbar'><span class='{task_cls(status)}' style='width:{task_pct(status)}%'></span></div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)
# === [ANCHOR] LAYOUT: CLICKUP TASKS CARD END ===

with b2:
    st.markdown("<div class='card'><div class='section'>Next Filming Timeslots</div>", unsafe_allow_html=True)
    for daydate, time_str, label in filming:
        st.markdown(
            f"<div class='film-row'><div><b>{daydate}</b> — {time_str}</div><div class='film-right'>{label}</div></div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)
# === [ANCHOR] LAYOUT: FILMING CARD END ===

st.caption("Tips → ?zoom=115 for TV; ?compact=1 for phones. Provide YOUTUBE_API_KEY & YT_PRIMARY_CHANNEL_ID for KPIs, and YT_CLIENT_ID/SECRET/REFRESH for true 7‑day & country map.")
