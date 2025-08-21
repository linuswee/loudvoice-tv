# app.py — LoudVoice TV dashboard (YT live stats + true 7‑day views + world map)
# Layout: Map (left) • Right: Ministry Tracker → Channel Stats (YT/IG/TT) → 7‑day views
# Bottom row: ClickUp (mock) + Next Filming (mock)
# Notes:
# - Live YT subs/total views need:   YOUTUBE_API_KEY, YOUTUBE_CHANNEL_ID     (Streamlit Secrets)
# - True last‑7‑days + country map:  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN (Secrets)
# - IG/TT are optional (mock if not configured)

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# Try Google libs (only required for YouTube Analytics)
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    GOOGLE_OK = True
except Exception:
    GOOGLE_OK = False


# ───────────────────────────────────────────────────────────────────────────────
# Streamlit page + URL switches
# ───────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="LoudVoice TV", page_icon="🎛️", layout="wide")

qp = st.query_params
ZOOM = qp.get("zoom", ["100"])[0]
COMPACT = qp.get("compact", ["0"])[0].lower() in ("1", "true", "yes")
st.markdown(f"<style>body{{zoom:{ZOOM}%}}</style>", unsafe_allow_html=True)

LOCAL_TZ = ZoneInfo("Asia/Kuala_Lumpur")  # set to your local timezone


# ───────────────────────────────────────────────────────────────────────────────
# Styles
# ───────────────────────────────────────────────────────────────────────────────
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

/* Ministry mini 3-col */
.mini-grid{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px }
.mini-card{ background:rgba(255,255,255,.03); border:1px solid rgba(255,255,255,.10);
            border-radius:10px; padding:8px 10px; text-align:center }
.mini-label{ font-size:11px; color:#aab3cc; margin:0 }
.mini-value{ font-size:22px; font-weight:800; margin:2px 0 0 }

/* Channel stats 3-col */
.kpi-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px }
.kpi-card { background:rgba(255,255,255,.03); border:1px solid rgba(255,255,255,.10); border-radius:10px; padding:10px 12px; }
.kpi-card .kpi-head{ display:flex; align-items:center; gap:8px; margin-bottom:4px }
.kpi-card .icon{ font-size:14px; margin-right:6px }
.kpi-card .kpi-name{ font-size:14px; font-weight:800 }
.kpi-card .kpi-label{ font-size:10px; color:#aab3cc; margin:0 }
.kpi-card .kpi-value{ font-size:18px; font-weight:800; margin:0 }

/* 7-day views (aligned bars) */
.grid-views{ display:grid; grid-template-columns:64px 1fr 76px; gap:10px; align-items:center; margin:6px 0 }
.views-bar{ height:10px; border-radius:6px; background:#1f2736; overflow:hidden }
.views-bar>span{ display:block; height:100%; background:#4aa3ff }

/* Tasks + filming */
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
  .card{ padding:8px 10px; border-radius:10px }
  .kpi-card{ padding:8px 10px } .kpi-card .kpi-value{ font-size:16px } .kpi-card .icon{ font-size:13px }
  .grid-views{ grid-template-columns:56px 1fr 64px }
}
</style>
""",
    unsafe_allow_html=True,
)


# ───────────────────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────────────────
def fmt_num(n: int | float) -> str:
    """Format as K / M / B with trimmed .0"""
    n = float(n)
    if n >= 1_000_000_000:
        v = n / 1_000_000_000
        return (f"{v:.1f}".rstrip("0").rstrip(".")) + "B"
    if n >= 1_000_000:
        v = n / 1_000_000
        return (f"{v:.1f}".rstrip("0").rstrip(".")) + "M"
    if n >= 1_000:
        v = n / 1_000
        return (f"{v:.1f}".rstrip("0").rstrip(".")) + "K"
    return str(int(n))


@st.cache_data(ttl=300)
def http_get(url, params=None, headers=None):
    r = requests.get(url, params=params, headers=headers, timeout=25)
    r.raise_for_status()
    return r.json()


# ───────────────────────────────────────────────────────────────────────────────
# YouTube Data API — live subs + total views
# ───────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def yt_channel_stats(api_key: str, channel_id: str) -> dict | None:
    try:
        data = http_get(
            "https://www.googleapis.com/youtube/v3/channels",
            {"part": "statistics", "id": channel_id, "key": api_key},
        )
        if not data.get("items"):
            return None
        stats = data["items"][0]["statistics"]
        return {"subs": int(stats["subscriberCount"]), "total": int(stats["viewCount"])}
    except Exception:
        return None


# ───────────────────────────────────────────────────────────────────────────────
# YouTube Analytics — true last‑7‑days & country map (requires OAuth refresh token)
# ───────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def yt_analytics_last7_and_countries(client_id, client_secret, refresh_token):
    if not GOOGLE_OK:
        raise RuntimeError("Google client libraries not available.")

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

    # We end analytics at *yesterday* so today's partial numbers are excluded
    utc_today = datetime.now(timezone.utc).date()
    end_date = utc_today - timedelta(days=1)          # yesterday
    start_date = end_date - timedelta(days=6)         # 7-day window inclusive

    # 1) Daily views
    daily = (
        analytics.reports()
        .query(
            ids="channel==MINE",
            startDate=start_date.isoformat(),
            endDate=end_date.isoformat(),
            metrics="views",
            dimensions="day",
            sort="day",
        )
        .execute()
    )

    # 2) Views by country (ISO2)
    country = (
        analytics.reports()
        .query(
            ids="channel==MINE",
            startDate=start_date.isoformat(),
            endDate=end_date.isoformat(),
            metrics="views",
            dimensions="country",
            sort="-views",
            maxResults=200,
        )
        .execute()
    )

    # Normalize
    # daily rows: [[YYYY-MM-DD, views], ...]
    day_rows = daily.get("rows", []) or []
    daily_df = pd.DataFrame(day_rows, columns=["date", "views"])
    daily_df["views"] = daily_df["views"].astype(int)
    daily_df["date"] = pd.to_datetime(daily_df["date"])
    daily_df["dow"] = daily_df["date"].dt.day_name().str[:3]  # Mon, Tue ...

    # Build dict by weekday for reordering
    by_weekday = {d: int(v) for d, v in zip(daily_df["dow"], daily_df["views"])}

    # country rows
    country_rows = country.get("rows", []) or []
    country_df = pd.DataFrame(country_rows, columns=["country", "views"])
    country_df["views"] = country_df["views"].astype(int)

    return by_weekday, country_df


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


# ───────────────────────────────────────────────────────────────────────────────
# Optional IG / TikTok (mock default)
# ───────────────────────────────────────────────────────────────────────────────
def mock_ig_tt():
    return {"followers": 6_050, "views7": 42_300}, {"followers": 11_032, "views7": 57_900}


# ───────────────────────────────────────────────────────────────────────────────
# Mock fallbacks
# ───────────────────────────────────────────────────────────────────────────────
MOCK = {
    "yt_subs": 30_800,
    "yt_total": 6_000_000,
    "by_weekday": {"Mon": 9800, "Tue": 11200, "Wed": 8500, "Thu": 12900, "Fri": 13200, "Sat": 12100, "Sun": 10400},
    "countries": pd.DataFrame({"country": ["US", "MY", "PH", "IN", "KE", "AU"], "views": [52000, 22000, 15000, 30000, 12000, 9000]}),
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


# ───────────────────────────────────────────────────────────────────────────────
# Fetch live data where possible
# ───────────────────────────────────────────────────────────────────────────────
yt_api_key = st.secrets.get("YOUTUBE_API_KEY")
yt_channel_id = st.secrets.get("YOUTUBE_CHANNEL_ID")

yt_live = yt_channel_stats(yt_api_key, yt_channel_id) if yt_api_key and yt_channel_id else None

yt_client_id = st.secrets.get("YT_CLIENT_ID")
yt_client_secret = st.secrets.get("YT_CLIENT_SECRET")
yt_refresh = st.secrets.get("YT_REFRESH_TOKEN")

by_weekday = None
country_df = None
if yt_client_id and yt_client_secret and yt_refresh:
    try:
        by_weekday, country_df = yt_analytics_last7_and_countries(yt_client_id, yt_client_secret, yt_refresh)
    except Exception:
        by_weekday, country_df = None, None

# Compose values with fallbacks
youtube = {
    "subs": (yt_live["subs"] if yt_live else MOCK["yt_subs"]),
    "total": (yt_live["total"] if yt_live else MOCK["yt_total"]),
}
by_weekday = by_weekday or MOCK["by_weekday"]
country_df = country_df if country_df is not None else MOCK["countries"]

ig, tt = mock_ig_tt()  # (use your integrations later)
ministry = MOCK["ministry"]
tasks = sorted(MOCK["tasks"], key=lambda t: 1 if "done" in t[1].lower() else 0)
filming = MOCK["filming"]

# Merge country lat/lon for plotting
cent = country_centroids()
map_df = country_df.merge(cent, on="country", how="left").dropna()


# ───────────────────────────────────────────────────────────────────────────────
# Header
# ───────────────────────────────────────────────────────────────────────────────
left_head, right_head = st.columns([0.75, 0.25])
with left_head:
    st.markdown("<div class='title'>LOUDVOICE</div>", unsafe_allow_html=True)
with right_head:
    now_local = datetime.now(LOCAL_TZ).strftime("%B %d, %Y %I:%M %p")
    st.markdown(f"<div class='timestamp'>{now_local}</div>", unsafe_allow_html=True)


# ───────────────────────────────────────────────────────────────────────────────
# Main layout: Map (left) • Right: Ministry → Channel Stats → 7‑day views
# ───────────────────────────────────────────────────────────────────────────────
left, right = st.columns([1.25, 0.75])

MAP_HEIGHT = 340 if not COMPACT else 260

with left:
    st.markdown("<div class='card'><div class='section'>World Map — YouTube Viewers (True, last 7 days)</div>", unsafe_allow_html=True)
    if not map_df.empty:
        size_series = (map_df["views"] / max(map_df["views"].max(), 1) * 22).clip(lower=6, upper=22)
        fig = go.Figure(
            go.Scattergeo(
                lat=map_df["lat"],
                lon=map_df["lon"],
                text=map_df["country"] + " — " + map_df["views"].map(lambda v: fmt_num(int(v))),
                mode="markers",
                marker=dict(size=size_series, color="#ffd54a", line=dict(color="#111", width=0.6)),
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
    else:
        st.write("No country data.")
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    # Ministry tracker (3-col)
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

    # Channel stats (YT / IG / TT)
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

    # 7‑day views (horizontal bars, special order: YTD, TUE, MON, SUN, SAT, FRI, THU)
    st.markdown("<div class='card'><div class='section'>YouTube Views (Last 7 Days)</div>", unsafe_allow_html=True)

    # Build values by weekday (Mon..Sun) from by_weekday dict; ensure all keys exist
    base_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    vals_by_day = {d: int(by_weekday.get(d, 0)) for d in base_days}

    # Yesterday label (YTD) and order without duplicating yesterday
    ytd_name = (datetime.now(LOCAL_TZ) - timedelta(days=1)).strftime("%a")  # e.g., 'Wed'
    # Desired base order after YTD:
    desired_order = ["Tue", "Mon", "Sun", "Sat", "Fri", "Thu", "Wed"]
    ordered_days = ["YTD"] + [d for d in desired_order if d != ytd_name]

    # Build list of (label, value)
    def value_for(label: str) -> int:
        if label == "YTD":
            return vals_by_day.get(ytd_name, 0)
        return vals_by_day.get(label, 0)

    ordered_vals = [value_for(lbl) for lbl in ordered_days]
    maxv = max(ordered_vals) or 1

    # Render rows
    for lbl, v in zip(ordered_days, ordered_vals):
        pct = int((v / maxv) * 100)
        st.markdown(
            f"<div class='grid-views'>"
            f"<div>{lbl}</div>"
            f"<div class='views-bar'><span style='width:{pct}%'></span></div>"
            f"<div style='text-align:right'>{fmt_num(v)}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


# ───────────────────────────────────────────────────────────────────────────────
# Bottom row: ClickUp (mock) + Next Filming (mock)
# ───────────────────────────────────────────────────────────────────────────────
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

st.caption(
    "Tips → `?zoom=115` for TV distance; `?compact=1` for phones. "
    "YouTube Analytics powers the last‑7‑days & map when credentials are set."
)
