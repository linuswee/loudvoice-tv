
# app.py — LoudVoice Dashboard (final template)
# Layout: Map (left) • Right: Ministry → Channel Stats (YT/IG/TT) → 7‑day views
# Bottom row: ClickUp tasks + Next Filming
# - Forces YouTube stats to come from YT_PRIMARY_CHANNEL_ID (or YOUTUBE_CHANNEL_ID)
# - Uses YOUTUBE_API_KEY for live subs + total views
# - Optional YouTube Analytics (true last‑7‑days + country map) via OAuth refresh token
# - Numbers formatted as K/M/B everywhere

import os
import json
from datetime import datetime, timedelta

import pandas as pd
import requests
import streamlit as st
import plotly.graph_objects as go

# Optional Google imports (only needed when Analytics creds provided)
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GOOGLE_OK = True
except Exception:
    GOOGLE_OK = False

# ─────────────────────────────────────────────
# Page config & query params
# ─────────────────────────────────────────────
st.set_page_config(page_title="LoudVoice TV", page_icon="🎛️", layout="wide")

def _get_qp():
    # Streamlit 1.33+
    try:
        return st.query_params
    except Exception:
        return st.experimental_get_query_params()

qp = _get_qp()
ZOOM = (qp.get("zoom", ["100"])[0] if isinstance(qp.get("zoom"), list) else qp.get("zoom", "100"))
COMPACT = str(qp.get("compact", ["0"])[0] if isinstance(qp.get("compact"), list) else qp.get("compact", "0")).lower() in ("1","true","yes")
st.markdown(f"<style>body{{zoom:{ZOOM}%}}</style>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Styles
# ─────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css');
html, body, [class^="css"] { background:#0b0f16 !important; color:#eef3ff }
header[data-testid="stHeader"], #MainMenu, footer { visibility:hidden; }
.block-container { max-width:1820px; padding-top:8px; padding-bottom:8px }
.title { color:#ffd54a; font-weight:900; font-size:34px; letter-spacing:.12em; margin:0 0 10px 0 }
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

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def fmt_num(n: int) -> str:
    """Format with K/M/B, trim trailing .0"""
    try:
        n = int(n)
    except Exception:
        return str(n)
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

# ─────────────────────────────────────────────
# YouTube Data API — live subs + total views
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def yt_channel_stats(api_key: str, channel_id: str):
    url = "https://www.googleapis.com/youtube/v3/channels"
    p = {"part": "statistics", "id": channel_id, "key": api_key}
    data = http_get(url, p)
    stats = data["items"][0]["statistics"]
    return {"subs": int(stats.get("subscriberCount","0")), "total": int(stats.get("viewCount","0"))}

# ─────────────────────────────────────────────
# YouTube Analytics — true last‑7‑days & by‑country
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def yt_analytics_last7_and_countries(client_id, client_secret, refresh_token):
    if not GOOGLE_OK:
        raise RuntimeError("Google client libs not installed.")
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
    start_date = end_date - timedelta(days=6)

    daily = (
        analytics.reports()
        .query(ids="channel==MINE", startDate=start_date.isoformat(), endDate=end_date.isoformat(),
               metrics="views", dimensions="day", sort="day")
        .execute()
    )
    country = (
        analytics.reports()
        .query(ids="channel==MINE", startDate=start_date.isoformat(), endDate=end_date.isoformat(),
               metrics="views", dimensions="country", sort="-views", maxResults=200)
        .execute()
    )
    daily_vals = [int(row[1]) for row in daily.get("rows",[])]
    cdf = pd.DataFrame(country.get("rows",[]) or [], columns=["country","views"])
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
    return pd.DataFrame(data, columns=["country","lat","lon"])

# ─────────────────────────────────────────────
# Optional IG/TT stubs (kept for layout completeness; still mocked unless wired)
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def ig_stats(access_token: str, ig_user_id: str):
    try:
        info = http_get(f"https://graph.facebook.com/v19.0/{ig_user_id}",
                        {"fields":"followers_count","access_token":access_token})
        followers = int(info.get("followers_count",0))
    except Exception:
        followers = 0
    # 7-day mock placeholder
    return {"followers": followers, "views7": 42300}

@st.cache_data(ttl=300)
def tt_stats(access_token: str, business_id: str):
    # Basic mock/stub (optionally wire later)
    return {"followers": 11032, "views7": 57900}

# ─────────────────────────────────────────────
# Mock defaults
# ─────────────────────────────────────────────
MOCK = {
    "yt_subs": 15_890, "yt_total": 145_000_000,
    "yt_last7": [23_500, 27_100, 24_800, 30_100, 28_900, 33_000, 35_120],
    "yt_countries": pd.DataFrame({"country":["US","MY","PH","IN","KE","AU"],
                                  "views":[52000,22000,15000,30000,12000,9000]}),
    "ig_followers": 6_050, "ig_views7": 42_300,
    "tt_followers": 11_032, "tt_views7": 57_900,
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

# ─────────────────────────────────────────────
# Fetch live data
# ─────────────────────────────────────────────
yt_api_key = st.secrets.get("YOUTUBE_API_KEY")
# Force primary channel via this secret (preferred), or fallback to legacy YOUTUBE_CHANNEL_ID
primary_id = st.secrets.get("YT_PRIMARY_CHANNEL_ID") or st.secrets.get("YOUTUBE_CHANNEL_ID")

try:
    yt_live = yt_channel_stats(yt_api_key, primary_id) if yt_api_key and primary_id else None
except Exception:
    yt_live = None

yt_client_id = st.secrets.get("YT_CLIENT_ID")
yt_client_secret = st.secrets.get("YT_CLIENT_SECRET")
yt_refresh_token = st.secrets.get("YT_REFRESH_TOKEN")

yt_last7 = None
yt_country_df = None
if yt_client_id and yt_client_secret and yt_refresh_token:
    try:
        lst7, cdf = yt_analytics_last7_and_countries(yt_client_id, yt_client_secret, yt_refresh_token)
        yt_last7 = lst7 if lst7 else None
        yt_country_df = cdf if not cdf.empty else None
    except Exception:
        st.info("Using mock for YT 7‑day & country (Analytics call failed).")

ig_token = st.secrets.get("IG_ACCESS_TOKEN")
ig_user_id = st.secrets.get("IG_BUSINESS_ID")
try:
    ig_live = ig_stats(ig_token, ig_user_id) if ig_token and ig_user_id else None
except Exception:
    ig_live = None

tt_token = st.secrets.get("TT_ACCESS_TOKEN")
tt_biz_id = st.secrets.get("TT_BUSINESS_ID")
try:
    tt_live = tt_stats(tt_token, tt_biz_id) if tt_token and tt_biz_id else None
except Exception:
    tt_live = None

# Compose
youtube = {
    "subs":  (yt_live["subs"]  if yt_live else MOCK["yt_subs"]),
    "total": (yt_live["total"] if yt_live else MOCK["yt_total"]),
}
ig = {"followers": (ig_live["followers"] if ig_live else MOCK["ig_followers"]),
      "views7":    (ig_live["views7"]     if ig_live else MOCK["ig_views7"])}
tt = {"followers": (tt_live["followers"] if tt_live else MOCK["tt_followers"]),
      "views7":    (tt_live["views7"]     if tt_live else MOCK["tt_views7"])}
yt_last7 = yt_last7 or MOCK["yt_last7"]
yt_country_df = yt_country_df if yt_country_df is not None else MOCK["yt_countries"]
ministry = MOCK["ministry"]
tasks = sorted(MOCK["tasks"], key=lambda t: 1 if "done" in t[1].lower() else 0)
filming = MOCK["filming"]

# Merge lat/lon for plotting
try:
    cent = country_centroids()
    map_df = yt_country_df.merge(cent, on="country", how="left").dropna()
except Exception:
    map_df = pd.DataFrame({
        "country":["US","MY","PH","IN","KE","AU"],
        "views":[52000,22000,15000,30000,12000,9000],
        "lat":[37.09,4.21,12.88,20.59,-0.02,-25.27],
        "lon":[-95.71,101.98,121.77,78.96,37.90,133.77],
    })

# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
t1, t2 = st.columns([0.75, 0.25])
with t1:
    st.markdown("<div class='title'>LOUDVOICE</div>", unsafe_allow_html=True)
with t2:
    st.markdown(f"<div class='timestamp'>{datetime.now().strftime('%B %d, %Y %I:%M %p')}</div>", unsafe_allow_html=True)

MAP_HEIGHT = 340 if not COMPACT else 260

# ─────────────────────────────────────────────
# Main layout
# ─────────────────────────────────────────────
left, right = st.columns([1.25, 0.75])

# Left: World Map
with left:
    st.markdown("<div class='card'><div class='section'>World Map — YouTube Viewers (True, last 7 days)</div>", unsafe_allow_html=True)
    # Compute marker sizes (6-22px)
    max_views = max(map_df["views"].max(), 1)
    sizes = (map_df["views"] / max_views * 22).clip(lower=6, upper=22)
    fig = go.Figure(go.Scattergeo(
        lat=map_df["lat"], lon=map_df["lon"],
        text=map_df.apply(lambda r: f"{r['country']} — {fmt_num(int(r['views']))}", axis=1),
        mode="markers",
        marker=dict(size=sizes, color="#ffd54a", line=dict(color="#111", width=0.6)),
    ))
    fig.update_layout(
        geo=dict(showland=True, landcolor="#0b0f16",
                 showcountries=True, countrycolor="rgba(255,255,255,.15)",
                 showocean=True, oceancolor="#070a0f"),
        margin=dict(l=0, r=0, t=0, b=0),
        height=MAP_HEIGHT, paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, theme=None, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    # Row 1 — Ministry
    st.markdown("<div class='card'><div class='section'>Ministry Tracker</div>", unsafe_allow_html=True)
    st.markdown(
        f"""
<div class="mini-grid">
  <div class="mini-card"><div class="mini-label">Prayer</div><div class="mini-value">{ministry['prayer']}</div></div>
  <div class="mini-card"><div class="mini-label">Studies</div><div class="mini-value">{ministry['studies']}</div></div>
  <div class="mini-card"><div class="mini-label">Baptisms</div><div class="mini-value">{ministry['baptisms']}</div></div>
</div>""",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # Row 2 — Channel Stats
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
</div>""",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # Row 3 — YouTube Views (Last 7 Days)
    st.markdown("<div class='card'><div class='section'>YouTube Views (Last 7 Days)</div>", unsafe_allow_html=True)
    days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    vals = (yt_last7 + [yt_last7[-1]]*7)[:7] if yt_last7 else [0]*7
    maxv = max(vals) or 1
    for d, v in zip(days, vals):
        pct = int((v / maxv) * 100)
        st.markdown(
            f"<div class='grid-views'>"
            f"<div>{d}</div>"
            f"<div class='views-bar'><span style='width:{pct}%'></span></div>"
            f"<div style='text-align:right'>{fmt_num(int(v))}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Bottom: ClickUp + Filming
# ─────────────────────────────────────────────
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

with b2:
    st.markdown("<div class='card'><div class='section'>Next Filming Timeslots</div>", unsafe_allow_html=True)
    for daydate, time_str, label in filming:
        st.markdown(
            f"<div class='film-row'><div><b>{daydate}</b> — {time_str}</div><div class='film-right'>{label}</div></div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

# Footer tip
st.caption("Tip → add ?zoom=115 for TV distance and ?compact=1 for tighter spacing on phones.")
