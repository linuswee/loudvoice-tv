__LV_VERSION__ = "v3.1b-cards-alignedbars (sha:0523c1c9, refactor-01)"

# app.py — LoudVoice Dashboard (cards + aligned bars layout)

from datetime import datetime, timedelta
import re
import pytz
import json
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

from streamlit.runtime.scriptrunner import add_script_run_ctx
from streamlit_autorefresh import st_autorefresh  # pip install streamlit-autorefresh

# Optional: long country names
import pycountry
import numpy as np

# Optional Google libs (only needed for YouTube Analytics)
GOOGLE_OK = True
try:
    # OAuth for YouTube
    from google.oauth2.credentials import Credentials as UserCredentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
except Exception:
    GOOGLE_OK = False
import base64
from pathlib import Path

import gspread
# Service Account for Google Sheets
from google.oauth2.service_account import Credentials as SACredentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe

SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

# -------------------------------
# Page config & compact helpers
# -------------------------------

LOCAL_TZ_NAME = "Asia/Kuala_Lumpur"           # string
LOCAL_TZ = pytz.timezone(LOCAL_TZ_NAME)       # tz object

st.set_page_config(
    page_title="LOUDVOICE",
    page_icon="assets/loudvoice_favicon.ico",  # favicon
    layout="wide"
)

st.markdown("""
<style>
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css');

/* ========== LOUDVOICE — minimal, unified CSS ========== */
/* ... your same CSS ... */
.kpi-head{ display:flex; align-items:center; gap:8px; margin-bottom:4px; }
.icon{ font-size:15px; }   /* add this so the FA glyph has a size */
</style>
""", unsafe_allow_html=True)

st.markdown("""
<link rel="stylesheet"
      href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css"
      integrity="sha512-bx8wN/so2HnIY7+q3sU5o7bQ/ud9l1z4PCtRj2CFf7RYI0ehCyBN8DQ3lmgwPcj3doGht+jOZQf1BPZpbnRgfQ=="
      crossorigin="anonymous" referrerpolicy="no-referrer" />
""", unsafe_allow_html=True)

# Inject favicon + iOS Home Screen icon into <head>
st.markdown(
    """
    <script>
    (function () {
      const head = document.getElementsByTagName('head')[0];

      function upsert(rel, href, sizes) {
        let sel = `link[rel='${rel}']` + (sizes ? `[sizes='${sizes}']` : '');
        let el = document.querySelector(sel);
        if (!el) {
          el = document.createElement('link');
          el.rel = rel;
          if (sizes) el.sizes = sizes;
          head.appendChild(el);
        }
        // cache-bust so iOS/ Safari stop using the old one
        el.href = href + `?v=${Date.now()}`;
      }

      // Standard favicon for browsers
      upsert('icon', 'assets/loudvoice_favicon.ico');

      // iOS Home Screen icon (rounded automatically by iOS)
      upsert('apple-touch-icon', 'assets/loudvoice_logo.png', '180x180');

      // (Optional) pinned tab mask for Safari macOS if you have an SVG:
      // upsert('mask-icon', 'assets/loudvoice_mask.svg');
      // document.querySelector("link[rel='mask-icon']").setAttribute('color', '#ffd54a');
    })();
    </script>
    """,
    unsafe_allow_html=True,
)
st_autorefresh(interval=5 * 60 * 1000, key="auto_refresh")  # 5 minutes
qp = st.query_params

HIDE_CB = qp.get("legend", ["1"])[0].lower() in ("0","false","no")  # legend=0 hides colorbar
MAP_H_QP = qp.get("map_h", [""])[0]
MAP_H_QP = int(MAP_H_QP) if MAP_H_QP.isdigit() else None

ZOOM = qp.get("zoom", ["80"])[0]   # default 80%; override with ?zoom=100 if needed
COMPACT = qp.get("compact", ["0"])[0].lower() in ("1", "true", "yes")
# QoL: force clear all Streamlit caches via ?clear_cache=1
if qp.get("clear_cache", ["0"])[0] in ("1","true","yes"):
    st.cache_data.clear()
    st.toast("Cache cleared", icon="♻️")

# Optional debug panel via ?debug=1
DEBUG = qp.get("debug", ["0"])[0].lower() in ("1","true","yes")

# -------------------------------
# Styles
# -------------------------------
st.markdown("""
<style>
/* ================= LOUDVOICE — Unified CSS ================= */

/* ---- Theme tokens ---- */
:root{
  --bg:#0b0f16;
  --ink:#eef3ff;
  --ink-dim:#aab3cc;
  --brand:#ffd54a;
  --card-bg:rgba(255,255,255,.03);
  --card-bd:rgba(255,255,255,.10);
  --shadow:0 4px 12px rgba(0,0,0,.22);
  --radius:12px;
}

/* ---- App chrome + base ---- */
html, body, [class^="css"]{ background:var(--bg)!important; color:var(--ink); }
#MainMenu, header[data-testid="stHeader"], div[data-testid="stToolbar"], div[data-testid="stDecoration"], footer{ display:none!important; }

/* ---- Full width container ---- */
div[data-testid="stAppViewContainer"] > .main{
  max-width:100vw!important;
  padding-left:0!important; padding-right:0!important;
  overflow:visible!important;
}
section.main{ overflow:visible!important; }
section.main > div.block-container{
  max-width:100vw!important;
  padding:8px 12px 10px!important;
  margin-left:0!important; margin-right:0!important;
  min-height:100vh!important;
}
/* Stretch horizontal blocks */
section.main > div.block-container > div:has(> div[data-testid="stHorizontalBlock"]){ max-width:100%!important; }
section.main > div.block-container > div:has(> div[data-testid="stHorizontalBlock"]) div[data-testid="column"]{
  flex:1 1 0!important; width:auto!important;
}
/* Spacing reset */
div[data-testid="stAppViewContainer"] > .main,
section.main,
section.main > div.block-container,
div[data-testid="stHorizontalBlock"]{ padding-top:0!important; margin-top:0!important; }
section.main > div.block-container > :first-child{ margin-top:0!important; }

/* ---- Brand bits ---- */
.lv-logo{ width:40px; height:auto; }
.title{
  color:var(--brand); font-weight:900; font-size:38px; letter-spacing:.12em;
  margin:0 0 6px 0!important;
}
.timestamp{ color:var(--brand); font-size:12px; font-weight:700; text-align:right; }
.section{
  color:var(--brand); font-weight:800; font-size:20px;
  margin:0;                                         /* base */
}
.small{ font-size:13px; color:#9aa3bd; }

/* ---- Cards ---- */
.card{
  background:var(--card-bg);
  border:1px solid var(--card-bd);
  border-radius:var(--radius);
  padding:4px 4px;
  margin-bottom:2px;
  box-shadow:var(--shadow);
}
/* 2px gap under *all* card headers */
.card > .section{ margin-bottom:2px!important; }

/* ---- Mini stats (Ministry Tracker) ---- */
.mini-grid{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px; }
.mini-card{ background:var(--card-bg); border:1px solid var(--card-bd); border-radius:10px; padding:8px 10px; text-align:center; }
.mini-label{ font-size:11px; color:var(--ink-dim); margin:0; }
.mini-value{ font-size:24px; font-weight:800; margin:2px 0 0; }

/* ---- YouTube KPI grid ---- */
.kpi-yt-grid, .kpi-yt-row{
  display:grid; grid-template-columns:2fr 1fr 1fr; gap:4px; align-items:center;
  font-variant-numeric:tabular-nums;
}
.kpi-yt-header{ margin:0 0 2px; }                  /* 2px gap below "Channel Stats" to this row */
.kpi-cell-right{ justify-self:end; }
.kpi-yt-left{ display:flex; align-items:center; gap:4px; font-weight:800; margin:0; padding:0; }

.kpi-yt-row{ margin:2px 0; align-items:baseline; }
.kpi-yt-row .col-names{ font-size:16px; font-weight:400; color:var(--ink); }
.kpi-yt-row .col-subs,
.kpi-yt-row .col-views{ text-align:right; font-size:16px; font-weight:800; color:var(--ink); }

.kpi-pill{ font-size:13px; background:rgba(255,255,255,.08); padding:6px 10px; border-radius:999px; white-space:nowrap; }
.kpi-pill b{ font-size:16px; margin-left:6px; }

/* ---- Bars (7-day views + task progress) ---- */
.grid-views{ display:grid; grid-template-columns:64px 1fr 76px; gap:10px; align-items:center; margin:4px 0; }
.views-bar{ height:10px; border-radius:6px; background:#1f2736; overflow:hidden; }
.views-bar>span{ display:block; height:100%; background:#4aa3ff; }
/* 2px gap below the "YouTube Views" header to the info line / first row */
.card .section + .small{ margin-top:2px!important; }

.grid-tasks-2{ display:grid; grid-template-columns:1fr 1.1fr; gap:12px; align-items:center; margin:6px 0; }
.hbar{ height:10px; border-radius:6px; background:#1f2736; overflow:hidden; }
.hbar>span{ display:block; height:100%; }   /* color inline */

/* ---- Filming list ---- */
.film-row{ display:grid; grid-template-columns:1fr auto; gap:12px; align-items:center; padding:6px 0; }
.film-right{ color:var(--brand); white-space:nowrap; }

/* ---- Icons ---- */
.icon{ font-size:15px; }

/* ---- Responsive ---- */
@media (max-width:1100px){
  section.main > div.block-container{ padding-left:8px!important; padding-right:8px!important; }
  .lv-logo{ width:28px; }
  .title{ font-size:28px; letter-spacing:.10em; }
  .timestamp{ display:none; }
  .card{ padding:8px 10px; border-radius:10px; }
  .grid-views{ grid-template-columns:48px 1fr 64px; }
  section.main > div:has(> div[data-testid="stHorizontalBlock"]) div[data-testid="column"]{
    width:100%!important; flex:0 0 100%!important;
  }
}
</style>
""", unsafe_allow_html=True)

# =======================
# Helpers & Data calls
# =======================

DAYS_FOR_MAP = 28                # 28‑day country map window
# Default 600 desktop, tighter on phones; allow ?map_h=### to override
MAP_HEIGHT = MAP_H_QP or (360 if COMPACT else 620)

def embed_img_b64(path: str) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode("utf-8")

def fmt_num(n: int) -> str:
    if n >= 1_000_000_000: v = n / 1_000_000_000; return (f"{v:.1f}".rstrip("0").rstrip(".")) + "B"
    if n >= 1_000_000:     v = n / 1_000_000;     return (f"{v:.1f}".rstrip("0").rstrip(".")) + "M"
    if n >= 1_000:         v = n / 1_000;         return (f"{v:.1f}".rstrip("0").rstrip(".")) + "K"
    return f"{n}"

@st.cache_data(ttl=300)
def http_get(url, params=None, headers=None):
    r = requests.get(url, params=params, headers=headers, timeout=25)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=300)
def yt_channel_stats(api_key: str, channel_id: str):
    """Simple KPI card numbers (subs + lifetime views)."""
    data = http_get(
        "https://www.googleapis.com/youtube/v3/channels",
        {"part": "statistics", "id": channel_id, "key": api_key},
    )
    items = data.get("items", [])
    if not items:
        raise RuntimeError("No channel found for the given ID/API key.")
    stats = items[0]["statistics"]
    return {"subs": int(stats.get("subscriberCount", 0)), "total": int(stats.get("viewCount", 0))}
    
# ---- Aggregation helpers ----
def yt_channels_aggregate(api_key: str, channel_ids: list[str]) -> dict:
    """Sum subs + lifetime views across multiple 'UC...' channels (Data API)."""
    total_subs, total_views = 0, 0
    for cid in (channel_ids or []):
        try:
            stats = yt_channel_stats(api_key, cid)
            total_subs += stats["subs"]
            total_views += stats["total"]
        except Exception as e:
            st.warning(f"Error fetching channel {cid}: {e}")
    return {"subs": total_subs, "total": total_views}

def _analytics_daily_for_refresh_token(client_id, client_secret, refresh_token, days=14) -> pd.DataFrame:
    """Daily views for ONE channel by OAuth bundle -> DataFrame[date, views]."""
    if not GOOGLE_OK:
        return pd.DataFrame()
    creds = UserCredentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/yt-analytics.readonly",
                "https://www.googleapis.com/auth/youtube.readonly"],
    )
    if not creds.valid:
        creds.refresh(Request())
    analytics = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
    end_date = (datetime.now(LOCAL_TZ).date() - timedelta(days=1))
    start_date = end_date - timedelta(days=days - 1)
    resp = analytics.reports().query(
        ids="channel==MINE",
        startDate=start_date.isoformat(),
        endDate=end_date.isoformat(),
        metrics="views",
        dimensions="day",
        sort="day",
    ).execute()
    rows = resp.get("rows", []) or []
    df = pd.DataFrame(rows, columns=["date", "views"])
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_convert(LOCAL_TZ).dt.normalize()
        df["views"] = df["views"].astype(int)
    return df

def _analytics_countries_for_refresh_token(client_id, client_secret, refresh_token, days=28) -> pd.DataFrame:
    """28-day country views for ONE channel -> DataFrame[country, views]."""
    if not GOOGLE_OK:
        return pd.DataFrame()
    creds = UserCredentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/yt-analytics.readonly",
                "https://www.googleapis.com/auth/youtube.readonly"],
    )
    if not creds.valid:
        creds.refresh(Request())
    analytics = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
    end_date = (datetime.now(LOCAL_TZ).date() - timedelta(days=1))
    start_date = end_date - timedelta(days=days - 1)
    resp = analytics.reports().query(
        ids="channel==MINE",
        startDate=start_date.isoformat(),
        endDate=end_date.isoformat(),
        metrics="views",
        dimensions="country",
        sort="-views",
        maxResults=200,
    ).execute()
    rows = resp.get("rows", []) or []
    df = pd.DataFrame(rows, columns=["country", "views"])
    if not df.empty:
        df["views"] = df["views"].astype(int)
    return df

def aggregate_daily_from_oauth_bundles(bundles: list[dict], days=14) -> pd.DataFrame:
    """Sum daily views across many OAuth bundles -> DataFrame[date, views]."""
    total = pd.DataFrame(columns=["date", "views"])
    for b in bundles or []:
        df = _analytics_daily_for_refresh_token(b["client_id"], b["client_secret"], b["refresh_token"], days=days)
        if df.empty: 
            continue
        if total.empty:
            total = df.copy()
        else:
            total = total.merge(df, on="date", how="outer", suffixes=("", "_x"))
            # sum across any 'views' columns
            view_cols = [c for c in total.columns if c.startswith("views")]
            total["views"] = total[view_cols].fillna(0).sum(axis=1).astype(int)
            total = total[["date", "views"]]
    total = total.sort_values("date")
    return total

def aggregate_countries_from_oauth_bundles(bundles: list[dict], days=28) -> pd.DataFrame:
    """Sum country views across many OAuth bundles -> DataFrame[country, views]."""
    from collections import defaultdict
    acc = defaultdict(int)
    for b in bundles or []:
        df = _analytics_countries_for_refresh_token(b["client_id"], b["client_secret"], b["refresh_token"], days=days)
        for _, r in df.iterrows():
            acc[str(r["country"])] += int(r["views"])
    if not acc:
        return pd.DataFrame()
    out = pd.DataFrame({"country": list(acc.keys()), "views": list(acc.values())})
    return out

# ---- YouTube Analytics: country views (last N days) ----
@st.cache_data(ttl=300)
def yt_analytics_country_lastN(
    client_id: str,
    client_secret: str,
    refresh_token: str,
    days: int = 28,
    channel_id: str | None = None,
):
    """
    Returns a DataFrame with columns: ['country', 'views'] for the last N days.
    Uses *yesterday* as end date to match Studio’s published windows.
    """
    if not GOOGLE_OK:
        raise RuntimeError("Google client libraries unavailable.")

    # YouTube OAuth places (all three helpers where you create creds):
    creds = UserCredentials(
    None,
    refresh_token=refresh_token,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=client_id,
    client_secret=client_secret,
    scopes=["https://www.googleapis.com/auth/yt-analytics.readonly",
            "https://www.googleapis.com/auth/youtube.readonly"],
    )
    if not creds.valid:
        creds.refresh(Request())

    analytics = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)

    end_date = (datetime.now(LOCAL_TZ).date() - timedelta(days=1))          # yesterday
    start_date = end_date - timedelta(days=days - 1)                   # inclusive window
    #ids_val = f"channel=={channel_id}" if channel_id else "channel==MINE"
    ids_val = "channel==MINE"  # ← force OAuth-authorized channel

    resp = analytics.reports().query(
        ids=ids_val,
        startDate=start_date.isoformat(),
        endDate=end_date.isoformat(),
        metrics="views",
        dimensions="country",
        sort="-views",
        maxResults=200,
    ).execute()

    rows = resp.get("rows", []) or []
    df = pd.DataFrame(rows, columns=["country", "views"])
    if not df.empty:
        df["views"] = df["views"].astype(int)
    return df

@st.cache_data(ttl=300)
def yt_analytics_lastN_and_countries(client_id, client_secret, refresh_token, days: int = 28):
    """
    YouTube Analytics: daily views (last N) + country views (last N).
    Uses yesterday as end date to avoid partial-day lag.
    Returns: daily_df[date, views], cdf[country, views]
    """
    if not GOOGLE_OK:
        return pd.DataFrame(), pd.DataFrame(), "Google client libraries unavailable."

    try:
        creds = UserCredentials(
            None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/yt-analytics.readonly",
                    "https://www.googleapis.com/auth/youtube.readonly"],
        )
        if not creds.valid:
            creds.refresh(Request())

        analytics = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)

        end_date = (datetime.now(LOCAL_TZ).date() - timedelta(days=1))  # yesterday
        start_date = end_date - timedelta(days=days - 1)

        # Daily views (channel timezone is not directly controllable; we normalize below)
        daily = analytics.reports().query(
            ids="channel==MINE",
            startDate=start_date.isoformat(),
            endDate=end_date.isoformat(),
            metrics="views",
            dimensions="day",
            sort="day",
        ).execute()
        daily_rows = daily.get("rows", []) or []
        daily_df = pd.DataFrame(daily_rows, columns=["date", "views"])
        if not daily_df.empty:
            daily_df["date"] = pd.to_datetime(daily_df["date"])
            daily_df["views"] = daily_df["views"].astype(int)

        # Country views (ISO‑2)
        country = analytics.reports().query(
            ids="channel==MINE",
            startDate=start_date.isoformat(),
            endDate=end_date.isoformat(),
            metrics="views",
            dimensions="country",
            sort="-views",
            maxResults=200,
        ).execute()
        cdf = pd.DataFrame(country.get("rows", []) or [], columns=["country", "views"])
        if not cdf.empty:
            cdf["views"] = cdf["views"].astype(int)

        return daily_df, cdf, ""
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), str(e)

@st.cache_data
def add_country_names(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    def to_name(code: str):
        try:
            rec = pycountry.countries.get(alpha_2=code)
            return rec.name if rec else code
        except Exception:
            return code
    if "country" in out.columns:
        out["name"] = out["country"].apply(to_name)
    return out

def _adaptive_ticks(z_raw_max: int):
    """
    Build log-scale ticks from real counts:
      - include 10, 20, 50, 100, 200, 500 if useful
      - then 1K, 2K, 5K, 10K, ... up to the max
    """
    import numpy as np

    vmax = int(z_raw_max) if z_raw_max is not None else 0
    if vmax < 1:
        vmax = 1

    candidates = [
        10, 20, 50, 100, 200, 500,
        1_000, 2_000, 5_000, 10_000, 20_000, 50_000,
        100_000, 200_000, 500_000,
        1_000_000, 2_000_000, 5_000_000
    ]
    vals = [v for v in candidates if v <= vmax]
    if not vals:
        vals = [1]

    def human(v: int) -> str:
        if v < 1_000:
            return str(v)
        if v < 1_000_000:
            return f"{v // 1_000}K"
        return f"{v // 1_000_000}M"

    tickvals = [np.log10(v + 1) for v in vals]  # map real counts to log axis
    ticktext = [human(v) for v in vals]
    return tickvals, ticktext

def build_choropleth(choro_df: pd.DataFrame, height: int) -> go.Figure:
    import numpy as np
    z_raw = choro_df["views"].astype(int).clip(lower=0)
    z = np.log10(z_raw + 1)
    tickvals, ticktext = _adaptive_ticks(int(z_raw.max()))

    bottom_band = 0.0 if HIDE_CB else 0.06
    colorbar_y  = (bottom_band/2.0) if not HIDE_CB else -0.2

    proj_scale = 1.22 if not COMPACT else 1.55  # a bit tighter for phones

    fig = go.Figure(go.Choropleth(
        locations=choro_df["iso3"], z=z,
        customdata=np.stack([choro_df["name"], z_raw], axis=1),
        hovertemplate="<b>%{customdata[0]}</b><br>Views: %{customdata[1]:,}<extra></extra>",
        colorscale=[[0.00, "#0b0f16"], [0.20, "#ffe600"], [0.40, "#ff3b3b"], [0.70, "#4285f4"], [1.00, "#34a853"]],
        marker_line_color="rgba(255,255,255,.08)", marker_line_width=0.5,
        showscale=not HIDE_CB,
        colorbar=dict(
            title="Views (log scale)", orientation="h",
            x=0.5, xanchor="center", y=colorbar_y, yanchor="middle",
            lenmode="fraction", len=0.92, thickness=12, outlinewidth=0,
            ticks="outside", tickvals=tickvals, ticktext=ticktext,
        ),
    ))

    fig.update_layout(
        geo=dict(
            projection=dict(type="natural earth", scale=proj_scale),
            center=dict(lat=5, lon=0),
            # IMPORTANT: remove auto-fit so the scale sticks
            # (fitbounds="locations"),  # ← delete this line
            # Crop some ocean/poles for a fuller look on mobile:
            lataxis=dict(range=[-55, 82]),
            bgcolor="rgba(0,0,0,0)",
            showocean=True, oceancolor="#070a0f",
            showland=True, landcolor="#0b0f16",
            showcountries=True, countrycolor="rgba(255,255,255,.10)",
            domain=dict(x=[0.00, 1.00], y=[bottom_band, 1.00]),
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig

def country_to_iso3(name: str) -> str:
    """Convert country name to ISO-3 code for Plotly choropleth."""
    try:
        return pycountry.countries.lookup(name).alpha_3
    except LookupError:
        overrides = {
            "United States": "USA",
            "South Korea": "KOR",
            "North Korea": "PRK",
            "Russia": "RUS",
            "Iran": "IRN",
            "Vietnam": "VNM",
            "Taiwan": "TWN",
            "Bolivia": "BOL",
            "Venezuela": "VEN",
            "Tanzania": "TZA",
            "Syria": "SYR",
            "Laos": "LAO",
            "Brunei": "BRN",
            "Czechia": "CZE",
            "Slovakia": "SVK",
            "Macedonia": "MKD",
            "Moldova": "MDA",
            "Palestine": "PSE",
            "Kosovo": "XKX",
        }
        return overrides.get(name, None)

def oauth_channel_identity(client_id: str, client_secret: str, refresh_token: str) -> dict:
    """
    Returns the OAuth-authenticated channel identity + stats:
    {channelId, title, subs, views}
    """
    if not GOOGLE_OK:
        raise RuntimeError("Google client libraries unavailable.")

    creds = UserCredentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/yt-analytics.readonly",
                "https://www.googleapis.com/auth/youtube.readonly"],
    )
    if not creds.valid:
        creds.refresh(Request())

    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    info = yt.channels().list(part="snippet,statistics", mine=True).execute()
    item = (info.get("items") or [{}])[0]

    return {
        "channelId": item.get("id"),
        "title": (item.get("snippet") or {}).get("title", ""),
        "subs": int((item.get("statistics") or {}).get("subscriberCount", 0)),
        "views": int((item.get("statistics") or {}).get("viewCount", 0)),
    }

# ---- YouTube Analytics: daily views (last N days) ----
@st.cache_data(ttl=300)
def yt_analytics_daily_lastN(
    client_id: str,
    client_secret: str,
    refresh_token: str,
    days: int = 7,
    channel_id: str | None = None,
):
    """
    Returns a DataFrame with columns: ['date', 'views'] for the last N days.
    Uses *yesterday* as end date (Studio shows complete days).
    """
    if not GOOGLE_OK:
        raise RuntimeError("Google client libraries unavailable.")

    creds = UserCredentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/yt-analytics.readonly",
                "https://www.googleapis.com/auth/youtube.readonly"],
    )
    if not creds.valid:
        creds.refresh(Request())

    analytics = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)

    end_date = (datetime.now(LOCAL_TZ).date() - timedelta(days=1))          # yesterday
    start_date = end_date - timedelta(days=days - 1)                   # inclusive window
    # ids_val = f"channel=={channel_id}" if channel_id else "channel==MINE"
    ids_val = "channel==MINE"  # ← force OAuth-authorized channel

    resp = analytics.reports().query(
        ids=ids_val,
        startDate=start_date.isoformat(),
        endDate=end_date.isoformat(),
        metrics="views",
        dimensions="day",
        sort="day",
    ).execute()

    rows = resp.get("rows", []) or []
    df = pd.DataFrame(rows, columns=["date", "views"])
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df["views"] = df["views"].astype(int)
    return df

def normalize_daily_to_local(daily_df: pd.DataFrame, tz: str) -> pd.DataFrame:
    """
    Studio graphs are shown in the property’s timezone.
    API days can feel off if your local TZ differs.
    We shift the date label so totals by 'day' match Studio’s day buckets.
    """
    if daily_df.empty:
        return daily_df
    # Treat API day boundaries as UTC midnight and map to local date
    s = pd.to_datetime(daily_df["date"], utc=True)
    local_dates = s.dt.tz_convert(tz).dt.date
    out = (
        pd.DataFrame({"date": local_dates, "views": daily_df["views"].astype(int)})
        .groupby("date", as_index=False)["views"]
        .sum()
    )
    out["date"] = pd.to_datetime(out["date"])
    return out

# --- Studio hard-map: country name -> views (you can extend this anytime) ---
STUDIO_COUNTRY_VIEWS = {
    "Philippines": 11163,
    "United States": 2849,
    "Malaysia": 1254,
    "Indonesia": 1178,
    "India": 828,
    "Australia": 564,
    "Canada": 461,
    "Thailand": 377,
    "United Kingdom": 264,
    "Singapore": 197,
    "South Africa": 193,
    "United Arab Emirates": 169,
    "Austria": 116,
    "Kenya": 102,
    "New Zealand": 101,
    "Romania": 86,
    "Germany": 73,
    "Taiwan": 61,
    "Cambodia": 58,
    "Vietnam": 57,
    "Hong Kong": 53,
    "Japan": 51,
    "Papua New Guinea": 50,
    "Mexico": 39,
    "Myanmar (Burma)": 34,
    "Brazil": 30,
    "Croatia": 27,
    "Peru": 24,
    "Dominican Republic": 22,
    "Saudi Arabia": 22,
    "Botswana": 21,
    "Denmark": 20,
    "Nigeria": 15,
    "Qatar": 14,
    "Guyana": 13,
    "Sri Lanka": 12,
    "Zambia": 11,
    "Jamaica": 10,
    "South Korea": 10,
    # "Uganda": <value not shown in your list>
}

# Name → ISO3 overrides for tricky names
ISO3_OVERRIDES = {
    "United States": "USA",
    "United Kingdom": "GBR",
    "South Korea": "KOR",
    "North Korea": "PRK",
    "Myanmar (Burma)": "MMR",
    "Taiwan": "TWN",
    "Hong Kong": "HKG",
    "United Arab Emirates": "ARE",
    "Vietnam": "VNM",
    "Czechia": "CZE",
    "Ivory Coast": "CIV",
    "Côte d’Ivoire": "CIV",
    "Russia": "RUS",
    "Syria": "SYR",
    "Palestine": "PSE",
    "Tanzania": "TZA",
    "DR Congo": "COD",
    "Republic of the Congo": "COG",
    "Eswatini": "SWZ",
    "Cabo Verde": "CPV",
    "Micronesia": "FSM",
    "Papua New Guinea": "PNG",
    "North Macedonia": "MKD",
}

def name_to_iso3(name: str) -> str | None:
    if name in ISO3_OVERRIDES:
        return ISO3_OVERRIDES[name]
    try:
        return pycountry.countries.lookup(name).alpha_3
    except Exception:
        return None

def build_choro_dataframe(views_by_name: dict) -> pd.DataFrame:
    """
    Build a dataframe with one row for EVERY country in the world (pycountry),
    filling views=0 where we don't have data. Also returns nice local names.
    """
    # Map your provided names -> ISO3
    mapped = {}
    for nm, v in views_by_name.items():
        iso3 = name_to_iso3(nm)
        if iso3:
            mapped[iso3] = int(v)

    # Base list: all countries (ISO3 + long name)
    rows = []
    for c in pycountry.countries:
        iso3 = getattr(c, "alpha_3", None)
        if not iso3:
            continue
        rows.append({"iso3": iso3, "name": c.name, "views": mapped.get(iso3, 0)})

    df = pd.DataFrame(rows)
    return df
    
# ---- ClickUp: upcoming tasks -------------------------------------------------
@st.cache_data(ttl=120)
def clickup_tasks_upcoming(token: str, list_id: str, limit: int = 12):
    url = f"https://api.clickup.com/api/v2/list/{list_id}/task"
    headers = {"Authorization": token}
    params = {
        "archived": "false",
        "subtasks": "true",
        "order_by": "due_date",
        "reverse": "false",
        "page": 0,
        "include_closed": "false",
    }
    try:
        r = requests.get(url, headers=headers, params=params, timeout=20)
        r.raise_for_status()
        items = (r.json() or {}).get("tasks", [])
    except Exception as e:
        return [], f"ClickUp error: {e}"

    out = []
    for t in items:
        status      = (t.get("status") or {}).get("status", "")
        status_type = (t.get("status") or {}).get("type", "")
        status_hex  = (t.get("status") or {}).get("color")  # "#ff5a5f" etc
        if status_type == "done":
            continue

        name = t.get("name", "Untitled")
        url  = t.get("url")  # deep link to ClickUp

        # due string + overdue flag
        due_ms = t.get("due_date")
        due_str, overdue = "", False
        if due_ms:
            try:
                due_dt  = datetime.utcfromtimestamp(int(due_ms) / 1000)
                overdue = due_dt.date() < datetime.utcnow().date()
                due_str = due_dt.strftime("%a, %b %d")
            except Exception:
                pass

        # first assignee
        assignees = t.get("assignees") or []
        who = ""
        if assignees:
            nm = assignees[0].get("username") or assignees[0].get("email","")
            who = nm.split("@")[0].title()

        prio = (t.get("priority") or {}).get("priority","")

        out.append({
            "name": name, "status": status, "status_hex": status_hex,
            "due_str": due_str, "overdue": overdue,
            "who": who, "url": url, "prio": prio
        })

    out.sort(key=lambda x: (x["due_str"] == "", x["due_str"], x["name"].lower()))
    return out[:limit], ""

def task_pct(status: str) -> int:
    s = status.lower(); return 100 if "done" in s else 50 if "progress" in s else 10
def task_cls(status: str) -> str:
    s = status.lower(); return "bar-green" if "done" in s else "bar-yellow" if "progress" in s else "bar-red"

def _secret_missing(name: str) -> bool:
    v = st.secrets.get(name)
    if not v:
        st.info(f"Missing secret: `{name}` — using mock data for that section.")
        return True
    return False

import requests
from datetime import datetime

@st.cache_data(ttl=120)
def clickup_calendar_events_from_view(
    token: str,
    view_id: str,
    limit: int = 12,
    tz_name: str = LOCAL_TZ_NAME,
):
    """
    Pull tasks from a specific ClickUp *View* (e.g., your Calendar view).
    Handles multi-day spans via start_date + due_date. Skips fully past items.
    Returns (events, error_message). On HTTP errors, error_message contains details.
    """
    headers = {"Authorization": token}
    base = f"https://api.clickup.com/api/v2/view/{view_id}/task"

    tz = pytz.timezone(tz_name)
    now_local = datetime.now(tz)

    all_items = []
    page = 0
    per_page = 100

    while True:
        params = {
            "include_closed": "false",
            "subtasks": "true",
            "page": page,
            # don’t set order_by (server sometimes 500s on start_date); sort client-side
        }
        try:
            r = requests.get(base, headers=headers, params=params, timeout=25)
            r.raise_for_status()
            items = (r.json() or {}).get("tasks", [])
        except Exception as e:
            return [], f"ClickUp View API error: {e}"

        if not items:
            break

        all_items.extend(items)
        if len(items) < per_page or len(all_items) >= 500:
            break
        page += 1

    events = []
    for t in all_items:
        start_ms = t.get("start_date")
        end_ms   = t.get("due_date")

        if not start_ms and not end_ms:
            continue

        try:
            if start_ms:
                start_dt = datetime.utcfromtimestamp(int(start_ms)/1000).replace(tzinfo=pytz.UTC).astimezone(tz)
            else:
                start_dt = datetime.utcfromtimestamp(int(end_ms)/1000).replace(tzinfo=pytz.UTC).astimezone(tz)
            end_dt = datetime.utcfromtimestamp(int((end_ms or start_ms))/1000).replace(tzinfo=pytz.UTC).astimezone(tz)
        except Exception:
            continue

        if end_dt < now_local:
            continue

        events.append({
            "title": t.get("name", "Untitled"),
            "url": t.get("url") or "#",
            "start": start_dt,
            "end": end_dt,
        })

    events.sort(key=lambda e: (e["start"], e["end"]))
    return events[:limit], ""

# ---- Google Sheets: Ministry & Filming (READ ONLY) ----------------------------
import re
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials as SACredentials
from gspread_dataframe import get_as_dataframe

SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

@st.cache_resource
def gs_client():
    creds = SACredentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPE
    )
    return gspread.authorize(creds)

def _open_ws(doc_id: str, worksheet: str):
    gc = gs_client()
    sh = gc.open_by_key(doc_id)
    return sh.worksheet(worksheet)

@st.cache_data(ttl=60)
def read_sheet(doc_id: str, worksheet: str) -> pd.DataFrame:
    """
    Read a worksheet and auto-detect which row contains headers.
    Normalizes headers to lowercase snake_case (e.g. 'Title:' -> 'title').
    Much more forgiving of preface rows and merged-header styles.
    """
    import re
    ws = _open_ws(doc_id, worksheet)
    rows = ws.get_all_values()
    if not rows:
        return pd.DataFrame()

    # Helper: normalize a header cell to test intent
    def norm_hdr(v: str) -> str:
        s = re.sub(r"[^\w]+", "_", (v or "").strip().lower())
        return re.sub(r"^_+|_+$", "", s)

    # Scan the first 20 rows to find the best header row
    header_row_idx = None
    best_score = -1
    for i, r in enumerate(rows[:20]):
        # Score by presence of any likely header keywords
        probes = [norm_hdr(x) for x in r]
        score = sum(p in ("date", "time", "title", "event", "timeslot", "when") for p in probes)
        # Prefer rows that aren't mostly empty
        nonempty = sum(bool((x or "").strip()) for x in r)
        score += 0.1 * nonempty
        if score > best_score:
            best_score = score
            header_row_idx = i

    if header_row_idx is None:
        header_row_idx = 0  # ultimate fallback

    header = rows[header_row_idx]
    data   = rows[header_row_idx + 1:]

    # Build DataFrame and drop fully blank columns
    df = pd.DataFrame(data, columns=header).fillna("")
    df = df.loc[:, ~(df.columns.astype(str).str.strip() == "")]

    # Normalize headers
    def _norm(s):
        s = str(s or "").strip().lower()
        s = re.sub(r"[^\w]+", "_", s)
        s = re.sub(r"^_+|_+$", "", s)
        return s
    df.columns = [_norm(c) for c in df.columns]

    # Drop fully blank rows
    if not df.empty:
        df = df[~(df.apply(lambda r: all(str(x).strip()=="" for x in r), axis=1))]

    return df.reset_index(drop=True)

# ---------- Ministry helpers (READ ONLY) ---------------------------------------
def load_ministry_totals(doc_id: str, worksheet: str = "Ministry") -> dict:
    """
    Supports either:
      A) row format with columns: [type, count]  -> sums by type
      B) wide format with columns: [prayer, studies, baptisms] on first row
      (timestamp/details are ignored if present)
    """
    out = {"prayer": 0, "studies": 0, "baptisms": 0}
    df = read_sheet(doc_id, worksheet)
    if df.empty:
        return out

    cols = set(df.columns)

    # A) Tidy rows: type + count
    if {"type", "count"} <= cols:
        # coerce numeric
        tmp = pd.to_numeric(df["count"], errors="coerce").fillna(0).astype(int)
        # standardize type labels
        kind = df["type"].str.strip().str.lower().replace({
            "prayer": "prayer",
            "prayers": "prayer",
            "study": "studies",
            "studies": "studies",
            "baptism": "baptisms",
            "baptisms": "baptisms",
        })
        agg = pd.DataFrame({"type": kind, "count": tmp}).groupby("type")["count"].sum()
        for k in out.keys():
            if k in agg.index:
                out[k] = int(agg[k])
        return out

    # B) Wide totals on first row
    for k in out.keys():
        if k in cols:
            try:
                out[k] = int(pd.to_numeric(df.iloc[0][k], errors="coerce") or 0)
            except Exception:
                out[k] = 0

    return out

# ---------- Filming helpers (READ ONLY) ----------------------------------------
def _first_nonempty(series: pd.Series, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in series.index and str(series[c]).strip():
            return str(series[c]).strip()
    return None

def load_upcoming_filming(doc_id: str, worksheet: str = "Filming Integration", limit: int = 6) -> list[tuple[str, str, str]]:
    """
    Returns up to `limit` rows as [(Mon, Aug 22, '09:20', 'Title'), ...].
    More tolerant header matching + good debug.
    """
    import re

    df = read_sheet(doc_id, worksheet)
    if df.empty:
        if DEBUG: st.info("[filming] read_sheet returned EMPTY")
        return []

    # Normalize again (belt & suspenders) and strip stray underscores/spaces
    def clean(s: str) -> str:
        s = str(s or "").strip().lower()
        s = re.sub(r"[^\w]+", "_", s)
        s = re.sub(r"^_+|_+$", "", s)
        # collapse things like 'title_' or 'date__' back to 'title'/'date'
        s = s.rstrip("_")
        return s

    df.columns = [clean(c) for c in df.columns]

    # Be generous about what we accept for each field
    title_candidates = ("title", "what", "event", "piece", "song")
    date_candidates  = ("date", "day", "when", "shoot_date")
    time_candidates  = ("time", "timeslot", "start", "start_time")

    def pick(cols, opts):
        for o in opts:
            if o in cols: return o
        # last resort: partial contains (e.g., "date_something")
        for c in cols:
            for o in opts:
                if o in c: return c
        return None

    cols = set(df.columns)
    title_col = pick(cols, title_candidates)
    date_col  = pick(cols, date_candidates)
    time_col  = pick(cols, time_candidates)

    if DEBUG:
        st.info(f"[filming] columns={list(df.columns)}")
        st.info(f"[filming] picked → title={title_col}, date={date_col}, time={time_col}")

    if not date_col or not title_col:
        return []

    today = pd.Timestamp.now(tz=LOCAL_TZ).normalize().tz_localize(None)
    this_year = today.year

    def parse_date(val: str) -> pd.Timestamp | None:
        s = str(val or "").strip()
        if not s:
            return None
    
        # d/m[/yy] or d-m[-yy]
        m = re.match(r"^\s*(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\s*$", s)
        if m:
            d, mth, yr = int(m.group(1)), int(m.group(2)), m.group(3)
            yr = int(yr) if yr else this_year
            if yr < 100:
                yr += 2000
            try:
                return pd.Timestamp(year=yr, month=mth, day=d)
            except Exception:
                return None
    
        # allow "Aug 27", "27 Aug", etc.
        d = pd.to_datetime(s, dayfirst=True, errors="coerce")
        return None if pd.isna(d) else pd.Timestamp(d)
    
    dates = df[date_col].apply(parse_date)
    times = df[time_col].astype(str).str.strip() if time_col else pd.Series([""] * len(df))
    times_sort = pd.to_datetime(times, format="%H:%M", errors="coerce") if time_col else pd.Series([pd.NaT] * len(df))
    titles = df[title_col].astype(str).str.strip()

    tmp = (pd.DataFrame({"date": dates, "time_str": times, "time_sort": times_sort, "title": titles})
             .dropna(subset=["date"]))

    if DEBUG:
        st.write("[filming] sample parsed rows:", tmp.head(12))

    if tmp.empty:
        return []

    # Future first; if not enough, backfill nearest past
    fut  = tmp[tmp["date"] >= today].sort_values(["date", "time_sort"], kind="stable")
    past = tmp[tmp["date"] <  today].sort_values(["date", "time_sort"], ascending=[False, False], kind="stable")

    take = pd.concat([fut.head(limit), past.head(max(0, limit - len(fut)))], axis=0)

    def fmt_date(d: pd.Timestamp) -> str:
        return pd.to_datetime(d).strftime("%a, %b %d")

    out = [(fmt_date(r.date), (r.time_str or ""), r.title or "") for _, r in take.iterrows()]
    if DEBUG: st.info(f"[filming] out={len(out)} (fut={len(fut)} past={len(past)})")
    return out

@st.cache_data(ttl=120)
def clickup_calendar_events(token: str, list_id: str, limit: int = 10, tz_name: str = LOCAL_TZ_NAME):
    """Return upcoming events from ClickUp List, using start_date/due_date like Calendar view."""
    url = f"https://api.clickup.com/api/v2/list/{list_id}/task"
    headers = {"Authorization": token}
    params = {
        "archived": "false",
        "subtasks": "true",
        "include_closed": "false",
        "page": 0,
    }
    try:
        r = requests.get(url, headers=headers, params=params, timeout=20)
        r.raise_for_status()
        items = (r.json() or {}).get("tasks", [])
    except Exception as e:
        return [], f"ClickUp Calendar API error: {e}"

    tz = pytz.timezone(tz_name)
    now_local = datetime.now(tz)

    events = []
    for t in items:
        start_ms = t.get("start_date")
        end_ms   = t.get("due_date") or start_ms
        if not start_ms:
            continue

        try:
            start_dt = datetime.utcfromtimestamp(int(start_ms)/1000).replace(tzinfo=pytz.UTC).astimezone(tz)
            end_dt   = datetime.utcfromtimestamp(int(end_ms)/1000).replace(tzinfo=pytz.UTC).astimezone(tz)
        except Exception:
            continue

        if end_dt < now_local:
            continue

        events.append({
            "title": t.get("name", "Untitled"),
            "url": t.get("url") or "#",
            "start": start_dt,
            "end": end_dt,
        })

    events.sort(key=lambda e: e["start"])
    return events[:limit], ""

# --- helpers to get ids cleanly
def _get_clickup_ids():
    sect = st.secrets.get("clickup", {}) or {}
    token   = (sect.get("token")   or st.secrets.get("CLICKUP_TOKEN")   or "").strip()
    list_id = (sect.get("list_id") or st.secrets.get("CLICKUP_LIST_ID") or "").strip()
    view_id = (sect.get("view_id") or st.secrets.get("CLICKUP_VIEW_ID") or "").strip()
    return token, list_id, view_id

# =======================
# Defaults / mocks (safe)
# =======================
MOCK = {
    "yt_subs": 30_800, "yt_total": 5_991_195,
    "yt_last7": [23500, 27100, 24800, 30100, 28900, 33000, 35120],
    "yt_countries": pd.DataFrame({"country":["US","MY","PH","IN","KE","AU"], "views":[52000,22000,15000,30000,12000,9000]}),
    "ig_followers": 6_000, "ig_views7": 42_300,
    "tt_followers": 11_000, "tt_views7": 57_900,
    "ministry": {"prayer": 15, "studies": 8, "baptisms": 1},
    "tasks": [("Shoot testimony interview","In Progress"),("Schedule weekend posts","In Progress"),
              ("Outline next video","Not Done"),("Edit podcast episode","Done")],
    "filming": [("Tue, Aug 26, 2025","1:00–3:00 PM","Worship Set"),
                ("Wed, Aug 27, 2025","10:30–12:00","Testimony Recording"),
                ("Fri, Aug 29, 2025","9:00–10:30 AM","Youth Reels")],
}

# =======================
# Fetch live data
# =======================
youtube = {"subs": MOCK["yt_subs"], "total": MOCK["yt_total"]}
ig = {"followers": MOCK["ig_followers"], "views7": MOCK["ig_views7"]}
tt = {"followers": MOCK["tt_followers"], "views7": MOCK["tt_views7"]}
ministry = MOCK["ministry"]

# ---- ClickUp live tasks (fallback to mock) ----
def _get_clickup_creds():
    sect = st.secrets.get("clickup", {})
    tok = sect.get("token") or st.secrets.get("CLICKUP_TOKEN")
    lst = sect.get("list_id") or st.secrets.get("CLICKUP_LIST_ID")
    return tok, lst

tasks: list = []
cu_token, cu_list = _get_clickup_creds()

if not cu_token or not cu_list:
    st.info("Missing secret(s): CLICKUP_TOKEN / CLICKUP_LIST_ID — using mock data for that section.")
    # mock as dicts so the UI code (chips/links/overdue) still works
    tasks = [
        {"name": n, "status": s, "due_str": "", "status_hex": "#ff5a5f",
         "who": "", "url": "#", "overdue": False}
        for (n, s) in MOCK["tasks"]
    ]
else:
    try:
        with st.spinner("Loading ClickUp tasks…"):
            tasks_live, cu_err = clickup_tasks_upcoming(cu_token, cu_list, limit=12)
        if cu_err:
            st.warning(cu_err)
            tasks = [
                {"name": n, "status": s, "due_str": "", "status_hex": "#ff5a5f",
                 "who": "", "url": "#", "overdue": False}
                for (n, s) in MOCK["tasks"]
            ]
        else:
            tasks = tasks_live  # <-- keep dicts (do NOT convert to tuples)
    except Exception as e:
        st.warning(f"ClickUp error: {e}")
        tasks = [
            {"name": n, "status": s, "due_str": "", "status_hex": "#ff5a5f",
             "who": "", "url": "#", "overdue": False}
            for (n, s) in MOCK["tasks"]
        ]
filming = MOCK["filming"]

# --- Per-channel YT stats for the 4-row KPI layout
yt_api_key = st.secrets.get("YOUTUBE_API_KEY", "")
yt_channels = st.secrets.get("YT_CHANNELS", [])  # [{id:"UC...", label:"..."}, ...]

yt_per = []
if yt_api_key and yt_channels:
    for ch in yt_channels:
        try:
            s = yt_channel_stats(yt_api_key, ch["id"])  # {"subs": int, "total": int}
            yt_per.append({"label": ch["label"], "subs": s["subs"], "total": s["total"]})
        except Exception as e:
            st.warning(f"YT stats error for {ch.get('label','(unknown)')}: {e}")
            yt_per.append({"label": ch["label"], "subs": 0, "total": 0})
else:
    yt_per = [
        {"label": "YT LoudVoice",           "subs": 0, "total": 0},
        {"label": "YT LoudVoice Insights",  "subs": 0, "total": 0},
        {"label": "YT LoudVoice Bahasa",    "subs": 0, "total": 0},
        {"label": "YT LoudVoice Chinese",   "subs": 0, "total": 0},
    ]

# KPI card via Data API (aggregate across multiple channels)
channel_ids = st.secrets.get("YT_CHANNEL_IDS", [])  # list of UC IDs
if yt_api_key and channel_ids:
    try:
        youtube = yt_channels_aggregate(yt_api_key, channel_ids)
    except Exception as e:
        st.warning(f"KPI aggregation error: {e}")

# Analytics (28‑day map + real last‑7 with *local* dates)
yt_client_id     = st.secrets.get("YT_CLIENT_ID")
yt_client_secret = st.secrets.get("YT_CLIENT_SECRET")
yt_refresh_token = st.secrets.get("YT_REFRESH_TOKEN")

# --- Aggregated Analytics ---
oauth_bundles = st.secrets.get("YT_OAUTH_CHANNELS", [])

oauth_title = ""
try:
    # Prefer dedicated single OAuth creds if provided
    if yt_client_id and yt_client_secret and yt_refresh_token:
        ident = oauth_channel_identity(yt_client_id, yt_client_secret, yt_refresh_token)
        oauth_title = ident.get("title") or ""
    # Else fall back to first bundle if you’re aggregating
    elif oauth_bundles:
        b0 = oauth_bundles[0]
        ident = oauth_channel_identity(b0["client_id"], b0["client_secret"], b0["refresh_token"])
        oauth_title = ident.get("title") or (b0.get("label") or "")
except Exception as e:
    if DEBUG: st.info(f"[oauth identity] {e}")

last7_df = pd.DataFrame()
cdf = pd.DataFrame()
if oauth_bundles:
    try:
        raw = aggregate_daily_from_oauth_bundles(oauth_bundles, days=14)
        if not raw.empty:
            last7_df = raw.tail(7)
        cdf = aggregate_countries_from_oauth_bundles(oauth_bundles, days=DAYS_FOR_MAP)
    except Exception as e:
        st.warning(f"YT Analytics aggregate error: {e}")

if last7_df.empty:
    yt_last7_vals   = MOCK["yt_last7"]
    yt_last7_labels = [(datetime.now(LOCAL_TZ).date() - timedelta(days=i)).strftime("%b %d")
                       for i in range(len(yt_last7_vals)-1, -1, -1)]
else:
    yt_last7_vals   = last7_df["views"].tolist()
    yt_last7_labels = last7_df["date"].dt.strftime("%b %d").tolist()

# 28-day countries aggregate (for the map)
cdf = pd.DataFrame()
analytics_err = ""
if oauth_bundles:
    try:
        cdf = aggregate_countries_from_oauth_bundles(oauth_bundles, days=DAYS_FOR_MAP)
    except Exception as e:
        analytics_err = str(e)

if not cdf.empty:
    choro_df = cdf.copy()
else:
    choro_df = MOCK["yt_countries"].copy()  # fallback

choro_df = add_country_names(choro_df)   # <-- add this line

# Ensure ISO-3 for map
choro_df["iso3"] = choro_df["country"].apply(country_to_iso3)
choro_df = choro_df.dropna(subset=["iso3"])

analytics_ok = not choro_df.empty
if analytics_err:
    st.warning(f"YT Analytics (country aggregate) error: {analytics_err}")

MIN_DOC  = st.secrets["gs_ministry_id"]
FILM_DOC = st.secrets["gs_filming_id"]

# Ministry totals (read-only)
ministry = load_ministry_totals(MIN_DOC, "Ministry")

# Filming list (next 5 upcoming including today)
filming = load_upcoming_filming(FILM_DOC, "Filming Integration", limit=6)

# =======================
# Header
# =======================
LOGO_B64 = embed_img_b64("assets/loudvoice_logo.png")

t1, t2 = st.columns([0.75, 0.25])
with t1:
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:10px;">
            <img class="lv-logo" src="data:image/png;base64,{LOGO_B64}" alt="LoudVoice logo" />
            <div class='title'>LOUDVOICE</div>
        </div>
        """,
        unsafe_allow_html=True
    )
with t2:
    now = datetime.now(LOCAL_TZ).strftime('%B %d, %Y %I:%M %p')
    st.markdown(f"<div class='timestamp'>{now}</div>", unsafe_allow_html=True)
if not analytics_ok:
    st.info("Using mock for YT 7‑day & country (Analytics call failed or not configured).")

# =======================
# Main layout
# =======================
left, right = st.columns([1.35, 0.65])  # wider map column so it fills visually

with left:
    st.markdown(
        f"<div class='card'><div class='section'>World Map — YouTube Viewers (True, last {DAYS_FOR_MAP} days)</div>",
        unsafe_allow_html=True,
    )

    # Use hard-mapped Studio data for now; every other country is present with 0
    # choro_df = build_choro_dataframe(STUDIO_COUNTRY_VIEWS)

    fig = build_choropleth(choro_df, MAP_HEIGHT)

    st.plotly_chart(fig, use_container_width=True, theme=None,
                    config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    # Ministry tracker
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

    # Channel stats
    connected = f"<span class='small'>Connected: All Channels</b></span>" if oauth_title else ""
    # --- YouTube-only Channel Stats ---------------------------------------
    st.markdown("<div class='card'><div class='section'>Channel Stats</div>", unsafe_allow_html=True)
    
    st.markdown("""
    <style>
    .kpi-yt { display:grid; grid-template-columns:2fr 1fr 1fr; gap:12px; }
    .kpi-yt-h1{ display:flex; align-items:center; gap:8px; font-weight:800; margin-bottom:6px; }
    .kpi-yt-row{ display:grid; grid-template-columns:2fr 1fr 1fr; gap:4px; align-items:center; margin:2px 0; padding: 0; }
    .kpi-yt-row.head > div {
      font-size: 14px;
      font-weight: 800;          /* <-- bold */
      color: var(--ink);         /* white like other bold text */
      padding-top: 0px;          /* reduce gap to Channel Stats heading */
      padding-bottom: 0px;
      margin-bottom: 0px;  /* closer to totals */
    }
    /* Also make the header "Total Views" right-aligned to match */
    .kpi-yt-row.head > div:nth-child(3){
      text-align:left;
    }
    .kpi-yt-row.vals .col-names { font-size:16px; font-weight:400; color:var(--ink); }  /* labels NOT bold */
    .kpi-yt-row.vals .col-subs,
    .kpi-yt-row.vals .col-views { text-align: right; font-size:16px; font-weight:800; color:var(--ink); }  /* numbers bold */
    .kpi-yt-row.total{ border-top:1px solid rgba(255,255,255,.10); padding-top:4px; margin-top:4px; }
    .kpi-yt-row.total .col-names{ font-weight:700; }  /* the word “Total” */
    .kpi-yt-head{ display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:8px; }
    .kpi-yt-left{ display:flex; align-items:center; gap:4px; font-weight:800; margin:0px; padding:0px; }
    .kpi-pill{ font-size:13px; background:rgba(255,255,255,.08); padding:6px 10px; border-radius:999px; white-space:nowrap;}
    .kpi-pill b{ font-size:16px; margin-left:6px; }
    .stack{ display:inline-block; line-height:1.35; }
    .stack .line{ display:block; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <style>
    /* Shared 3-col grid: names | subs | views */
    .kpi-yt-grid, .kpi-yt-row{
      display:grid;
      grid-template-columns: 2fr 1fr 1fr;
      gap:4px;
      align-items:center;
      margin-top: 0;        /* kill extra gap above YouTube row */
      margin-bottom: 2px;
    }
    .kpi-yt-header{ margin:0px 0 2px; }
    .kpi-cell-right{ justify-self:end; }          /* put pills at the right edge of their cells */
    
    .kpi-yt-row{ margin:2px 0; align-items:baseline; }
    .kpi-yt-row .col-names{ font-size:16px; font-weight:400; color:var(--ink); }
    .kpi-yt-row .col-subs,
    .kpi-yt-row .col-views{ text-align:right; font-size:16px; font-weight:800; color:var(--ink); }
    
    /* make digits align nicely */
    .kpi-yt-grid, .kpi-yt-row { font-variant-numeric: tabular-nums; }
    </style>
    """, unsafe_allow_html=True)
    
    def stack(lines):
        import html
        inner = "".join(f"<span class='line'>{html.escape(str(l))}</span>" for l in lines)
        return f"<span class='stack'>{inner}</span>"
    
    # Build rows for each channel (from yt_per)
    names  = [x["label"] for x in yt_per]
    subs   = [fmt_num(x["subs"])  if x["subs"]  else "–" for x in yt_per]
    totals = [fmt_num(x["total"]) if x["total"] else "–" for x in yt_per]
    
    # Use your already-computed totals
    agg_subs_label   = fmt_num(sum(x["subs"]  for x in yt_per))   # or: fmt_num(youtube.get("subs", 0))
    agg_total_label  = fmt_num(sum(x["total"] for x in yt_per))   # or: fmt_num(youtube.get("total", 0))
    
    st.markdown(
        f"""
        <div class="kpi-yt-grid kpi-yt-header">
          <div class="kpi-yt-left">
            <i class="fa-brands fa-youtube icon" style="color:#ff3d3d"></i>
            <span>YouTube</span>
          </div>
          <div class="kpi-cell-right"><span class="kpi-pill">Subs <b>{agg_subs_label}</b></span></div>
          <div class="kpi-cell-right"><span class="kpi-pill">Total Views <b>{agg_total_label}</b></span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
        
    # --- Values (uses the SAME 3-col grid) ---
    st.markdown(
        f"""
        <div class="kpi-yt-row">
          <div class="col-names">{stack(names)}</div>
          <div class="col-subs">{stack(subs)}</div>
          <div class="col-views">{stack(totals)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # YouTube Views (Last 7 Days) — with real daily dates
    st.markdown("<div class='card'><div class='section'>YouTube Views (Last 7 Days, complete data only)</div>", unsafe_allow_html=True)

    # optional little tooltip/note
    st.markdown("<div class='small'>ℹ️ YouTube Analytics can lag up to 48h. Latest day may be missing until processed.</div>", unsafe_allow_html=True)
    vals = yt_last7_vals[:]
    maxv = max(vals) if vals else 1
    for d, v in zip(yt_last7_labels, vals):
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

# --- Bottom row: 3 columns (Tasks | Filming | ClickUp Calendar) ---
c1, c2, c3 = st.columns([1.05, 1.0, 0.95])

with c1:
    st.markdown("<div class='card'><div class='section'>ClickUp Tasks (Upcoming)</div>", unsafe_allow_html=True)
    for t in tasks:
        if isinstance(t, dict):
            name, status, due_str = t["name"], t["status"], t["due_str"]
            status_hex = t.get("status_hex") or "#ff5a5f"
            who        = t.get("who") or ""
            url        = t.get("url") or "#"
            overdue    = t.get("overdue", False)
        else:
            name, status, due_str = t
            status_hex, who, url, overdue = "#ff5a5f", "", "#", False

        small_bits = ["<span class='small'>", status]
        if due_str: small_bits += [" · due ", due_str]
        if overdue: small_bits += [" <b style='color:#ff6b6b'>(overdue)</b>"]
        small_bits += ["</span>"]
        small_line = "".join(small_bits)
        who_chip = f"<span style='font-size:11px;background:rgba(255,255,255,.08);padding:2px 6px;border-radius:8px;margin-left:6px'>{who}</span>" if who else ""

        st.markdown(
            f"<div class='grid-tasks-2'>"
            f"<div><a href='{url}' target='_blank' style='color:#eef3ff;text-decoration:none'><b>{name}</b></a>{who_chip}"
            f"<div>{small_line}</div></div>"
            f"<div class='hbar'><span style='width:{task_pct(status)}%; background:{status_hex}'></span></div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown("<div class='card'><div class='section'>Next Filming Timeslots</div>", unsafe_allow_html=True)
    if not filming:
        st.markdown("<div class='small'>No upcoming timeslots found.</div>", unsafe_allow_html=True)
    for daydate, time_str, label in filming:
        st.markdown(
            f"<div class='film-row'><div><b>{daydate}</b> — {time_str}</div>"
            f"<div class='film-right'>{label}</div></div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

with c3:
    st.markdown("<div class='card'><div class='section'>ClickUp Calendar</div>", unsafe_allow_html=True)
    cu_token, cu_list, cu_view = _get_clickup_ids()

    if not cu_token or not (cu_view or cu_list):
        st.markdown("<div class='small'>Add <code>CLICKUP_TOKEN</code> and either <code>CLICKUP_VIEW_ID</code> (preferred) or <code>CLICKUP_LIST_ID</code> in <code>st.secrets</code>.</div>", unsafe_allow_html=True)
    else:
        cal_items, cal_err = ([], "")
        used = ""

        if cu_view:
            cal_items, cal_err = clickup_calendar_events_from_view(
                cu_token, cu_view, limit=12, tz_name=LOCAL_TZ_NAME
            )
            # If the view endpoint 404s (very common when the id is wrong),
            # fall back to list pull so the UI still shows something.
            if cal_err and "404" in cal_err:
                st.info("View ID returned 404. Falling back to list-based calendar.", icon="ℹ️")
                cu_view = ""  # disable for this run

        if not cu_view and cu_list and (not cal_items):
            cal_items, cal_err = clickup_calendar_events(
                cu_token, cu_list, limit=12, tz_name=LOCAL_TZ_NAME
            )
            used = f"list:{cu_list}" if not used else used + f" → list:{cu_list}"

        if cal_err:
            st.markdown(f"<div class='small'>⚠️ {cal_err}</div>", unsafe_allow_html=True)
        elif not cal_items:
            st.markdown("<div class='small'>No upcoming items.</div>", unsafe_allow_html=True)
        else:
            def fmt_range(ev):
                s, e = ev["start"], ev["end"]
                return f"<b>{s.strftime('%a, %b %d')}</b>" + (f" — {s.strftime('%H:%M')}" if s.date()==e.date() and (s.hour or s.minute) else f" → {e.strftime('%a, %b %d')}")
            for ev in cal_items:
                left = fmt_range(ev)
                right = f"<a href='{ev['url']}' target='_blank' style='color:var(--brand);text-decoration:none'>{ev['title']}</a>"
                st.markdown(f"<div class='film-row'><div>{left}</div><div class='film-right'>{right}</div></div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
