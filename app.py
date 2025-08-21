# app.py — LoudVoice TV + YouTube Analytics (optional IG / TikTok hooks)
import os
import json
import time
import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Google libs (only used if YouTube Analytics secrets present)
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GOOGLE_OK = True
except Exception:
    GOOGLE_OK = False  # we’ll still run; just fall back to mock

st.set_page_config(page_title="LoudVoice TV", page_icon="🎛️", layout="wide")

# ─────────────────────────────────────────────
# URL switches: ?zoom=115&compact=1
# ─────────────────────────────────────────────
qp = st.query_params
ZOOM = qp.get("zoom", ["100"])[0]
COMPACT = qp.get("compact", ["0"])[0].lower() in ("1", "true", "yes")
st.markdown(f"<style>body{{zoom:{ZOOM}%}}</style>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Styles (same look you approved)
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
    """15_890 -> 15.9K, 145_000_000 -> 145M (trim trailing .0)"""
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
# YouTube Data API — live subs + total views (API key)
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def yt_channel_stats(api_key: str, channel_id: str):
    url = "https://www.googleapis.com/youtube/v3/channels"
    p = {"part": "statistics", "id": channel_id, "key": api_key}
    data = http_get(url, p)
    stats = data["items"][0]["statistics"]
    return {"subs": int(stats["subscriberCount"]), "total": int(stats["viewCount"])}

# ─────────────────────────────────────────────
# YouTube Analytics API — true last‑7‑days & country map
# Requires: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def yt_analytics_last7_and_countries(
    client_id: str, client_secret: str, refresh_token: str
):
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
    start_date = end_date - timedelta(days=6)  # inclusive 7 days window

    # 1) Views by day
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
    # 2) Views by country (2-letter codes)
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

    # Normalize daily
    daily_vals = [int(row[1]) for row in daily.get("rows", [])]
    # Normalize country (we’ll map to lat/lon with a tiny lookup for plotting)
    country_rows = country.get("rows", []) or []
    country_df = pd.DataFrame(country_rows, columns=["country", "views"])
    country_df["views"] = country_df["views"].astype(int)
    return daily_vals, country_df

# Lightweight country centroid table (ISO2 -> rough lat/lon) for plotting
@st.cache_data
def country_centroids():
    # Minimal set; extend as needed
    data = [
        ("US", 37.09, -95.71),
        ("MY", 4.21, 101.98),
        ("PH", 12.88, 121.77),
        ("IN", 20.59, 78.96),
        ("KE", -0.02, 37.90),
        ("AU", -25.27, 133.77),
        ("ID", -0.79, 113.92),
        ("SG", 1.29, 103.85),
        ("GB", 55.38, -3.43),
        ("CA", 56.13, -106.35),
        ("NG", 9.08, 8.68),
        ("BR", -14.23, -51.92),
        ("DE", 51.17, 10.45),
        ("FR", 46.23, 2.21),
        ("JP", 36.20, 138.25),
        ("KR", 35.91, 127.76),
        ("TH", 15.87, 100.99),
        ("VN", 14.06, 108.28),
        ("MX", 23.63, -102.55),
        ("ES", 40.46, -3.75),
    ]
    return pd.DataFrame(data, columns=["country", "lat", "lon"])

# ─────────────────────────────────────────────
# Instagram Graph API (optional)
# Needs: IG_ACCESS_TOKEN, IG_BUSINESS_ID
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def ig_stats(access_token: str, ig_user_id: str):
    # Followers
    info = http_get(
        f"https://graph.facebook.com/v19.0/{ig_user_id}",
        {"fields": "followers_count,username", "access_token": access_token},
    )
    followers = int(info.get("followers_count", 0))

    # Last 7 days video views (approx: sum of video_views across recent media)
    media = http_get(
        f"https://graph.facebook.com/v19.0/{ig_user_id}/media",
        {"fields": "id,media_type,timestamp", "limit": 50, "access_token": access_token},
    ).get("data", [])

    since = datetime.utcnow() - timedelta(days=7)
    ids = [m["id"] for m in media if m.get("media_type") in ("VIDEO", "REELS") and
           datetime.fromisoformat(m["timestamp"].replace("Z","+00:00")) >= since]

    total_7d = 0
    for vid in ids[:20]:  # keep requests low
        try:
            ins = http_get(
                f"https://graph.facebook.com/v19.0/{vid}/insights",
                {"metric": "video_views,plays", "access_token": access_token},
            )
            for row in ins.get("data", []):
                if row["name"] in ("video_views", "plays"):
                    # IG returns a list of values by period; sum them
                    v = sum(int(x.get("value", 0)) for x in row.get("values", []))
                    total_7d += v
        except Exception:
            pass

    return {"followers": followers, "views7": total_7d}

# ─────────────────────────────────────────────
# TikTok Business API (optional)
# Needs: TT_ACCESS_TOKEN, TT_BUSINESS_ID (or advertiser id)
# We’ll try basic profile + 7d video views via reports (if available)
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def tt_stats(access_token: str, business_id: str):
    # NOTE: TikTok Business API access varies; this is a minimal stub.
    headers = {"Access-Token": access_token, "Content-Type": "application/json"}
    followers = None
    views7 = None
    try:
        # Profile (followers) — endpoint may differ per account type; example path:
        prof = http_get(
            "https://business-api.tiktok.com/open_api/v1.3/business/get/",
            {"business_id": business_id},
            headers=headers,
        )
        followers = prof.get("data", {}).get("follower_count")
    except Exception:
        pass

    try:
        # Reporting (7-day views) — illustrative, may require advertiser scope:
        end = datetime.utcnow().date()
        start = end - timedelta(days=6)
        rep = http_get(
            "https://business-api.tiktok.com/open_api/v1.3/reports/integrated/get/",
            {
                "business_id": business_id,
                "report_type": "BASIC",
                "data_level": "AUCTION_ADVERTISER",  # varies
                "dimensions": json.dumps(["stat_time_day"]),
                "metrics": json.dumps(["views"]),
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
            headers=headers,
        )
        rows = rep.get("data", {}).get("list", [])
        views7 = sum(int(r.get("views", 0)) for r in rows)
    except Exception:
        pass

    return {"followers": int(followers or 0), "views7": int(views7 or 0)}

# ─────────────────────────────────────────────
# Mock defaults (used whenever live calls aren’t available)
# ─────────────────────────────────────────────
MOCK = {
    "yt_subs": 15_890, "yt_total": 145_000_000,
    "yt_last7": [23_500, 27_100, 24_800, 30_100, 28_900, 33_000, 35_120],
    "yt_countries": pd.DataFrame({
        "country": ["US","MY","PH","IN","KE","AU"],
        "views":   [52_000,22_000,15_000,30_000,12_000,9_000]
    }),
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
# Fetch live data where possible
# ─────────────────────────────────────────────
yt_api_key = st.secrets.get("YOUTUBE_API_KEY")
yt_channel_id = st.secrets.get("YOUTUBE_CHANNEL_ID")

# YouTube live (subs/total)
try:
    yt_live = yt_channel_stats(yt_api_key, yt_channel_id) if yt_api_key and yt_channel_id else None
except Exception:
    yt_live = None

# YouTube Analytics (true last 7 days + country map)
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
    except Exception as e:
        st.info("Using mock for YT 7‑day & country (Analytics call failed).")

# IG
ig_token = st.secrets.get("IG_ACCESS_TOKEN")
ig_user_id = st.secrets.get("IG_BUSINESS_ID")
try:
    ig_live = ig_stats(ig_token, ig_user_id) if ig_token and ig_user_id else None
except Exception:
    ig_live = None

# TikTok
tt_token = st.secrets.get("TT_ACCESS_TOKEN")
tt_biz_id = st.secrets.get("TT_BUSINESS_ID")
try:
    tt_live = tt_stats(tt_token, tt_biz_id) if tt_token and tt_biz_id else None
except Exception:
    tt_live = None

# Compose final values (fallback to mock)
youtube = {
    "subs":  (yt_live["subs"]  if yt_live else MOCK["yt_subs"]),
    "total": (yt_live["total"] if yt_live else MOCK["yt_total"]),
}
ig = {
    "followers": (ig_live["followers"] if ig_live else MOCK["ig_followers"]),
    "views7":    (ig_live["views7"]     if ig_live else MOCK["ig_views7"]),
}
tt = {
    "followers": (tt_live["followers"] if tt_live else MOCK["tt_followers"]),
    "views7":    (tt_live["views7"]     if tt_live else MOCK["tt_views7"]),
}
yt_last7 = yt_last7 or MOCK["yt_last7"]
yt_country_df = yt_country_df if yt_country_df is not None else MOCK["yt_countries"]
ministry = MOCK["ministry"]
tasks = sorted(MOCK["tasks"], key=lambda t: 1 if "done" in t[1].lower() else 0)
filming = MOCK["filming"]

# Merge country lat/lon for plotting
try:
    cent = country_centroids()
    map_df = yt_country_df.merge(cent, on="country", how="left").dropna()
except Exception:
    # fallback to a tiny fixed set if merge fails
    map_df = pd.DataFrame({
        "country":["US","MY","PH","IN","KE","AU"],
        "views":[52_000,22_000,15_000,30_000,12_000,9_000],
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
# Main layout: Left (map) • Right (ministry + socials + 7‑day)
# ─────────────────────────────────────────────
left, right = st.columns([1.25, 0.75])

# Left — World Map (tight margins)
with left:
    st.markdown("<div class='card'><div class='section'>World Map — YouTube Viewers (True, last 7 days)</div>", unsafe_allow_html=True)
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

with right:
    # Row 1 — Ministry 3-col compact
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

    # Row 2 — Social channel stats (compact labels + K/M numbers)
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

    # Row 3 — YouTube Views (Last 7 Days) aligned bars — TRUE if Analytics available
    st.markdown("<div class='card'><div class='section'>YouTube Views (Last 7 Days)</div>", unsafe_allow_html=True)
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    # If Analytics returned <7 rows (rare timezone edges), pad/trim
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
# Bottom row: ClickUp + Next Filming
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

st.caption("Tips → ?zoom=115 for TV; ?compact=1 for phones. YouTube Analytics powers the last‑7‑days & map when credentials are set.")
