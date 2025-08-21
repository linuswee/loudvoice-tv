
# app.py — LoudVoice TV (cards + bars) — APP_VERSION v3.1
# ------------------------------------------------------------------
# What it does
# - Real YouTube stats via Data API (subs + total views)
# - Real last-7-day views + country map via YouTube Analytics (OAuth refresh token)
# - Filming timeslots from Google Sheets (service account)
# - ClickUp tasks (status-mapped progress bars)
# - TV-friendly "cards + aligned bars" layout you approved
#
# Required packages (requirements.txt):
# streamlit
# requests
# pandas
# plotly
# gspread
# google-auth
#
# Secrets (Streamlit → Settings → Secrets):
# YOUTUBE_API_KEY = "AIza..."
# YT_PRIMARY_CHANNEL_ID = "UC..."
# YT_CLIENT_ID = "....apps.googleusercontent.com"
# YT_CLIENT_SECRET = "..."
# YT_REFRESH_TOKEN = "ya29..."
#
# # Google Sheets (service account JSON and your sheet)
# GSERVICE_ACCOUNT = """{ ...full service account JSON... }"""
# GSHEETS_URL = "https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit#gid=0"
#   or GSHEETS_ID = "<SHEET_ID>"
#
# # ClickUp
# CLICKUP_TOKEN = "pk_..."
# CLICKUP_LIST_ID = "123456789"
# ------------------------------------------------------------------

APP_VERSION = "LoudVoice • cards+bars v3.1"

import json
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# ---------- Page & URL switches ----------
st.set_page_config(page_title="LoudVoice TV", page_icon="📺", layout="wide")

# If your Streamlit version doesn’t have st.query_params, fall back.
def _get_qp():
    try:
        return st.query_params  # new API
    except Exception:
        return st.experimental_get_query_params()  # legacy

qp = _get_qp()
ZOOM = (qp.get("zoom", ["100"])[0] if isinstance(qp, dict) else "100")
COMPACT = (qp.get("compact", ["0"])[0].lower() in ("1","true","yes") if isinstance(qp, dict) else False)
st.markdown(f"<style>html,body{{zoom:{ZOOM}%}}</style>", unsafe_allow_html=True)

# ---------- Styles (cards + bars) ----------
st.markdown(r"""
<style>
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css');
html, body { background:#0b0f16 !important; color:#eef3ff }
header[data-testid="stHeader"], #MainMenu, footer { visibility:hidden; }
.block-container { max-width:1820px; padding-top:8px; padding-bottom:8px }

.title { color:#ffd54a; font-weight:900; font-size:34px; letter-spacing:.12em; margin:0 0 10px 0 }
.badge { display:inline-block; font-size:11px; padding:2px 8px; border-radius:999px; margin-left:8px; vertical-align:middle }
.badge-ok { background:#183b22; color:#9ff0b1; border:1px solid #245e35 }
.badge-warn { background:#43240e; color:#ffd166; border:1px solid #6c4318 }
.badge-err { background:#4a1f1f; color:#ff9b9b; border:1px solid #7a2e2e }
.timestamp { color:#ffd54a; font-size:12px; font-weight:700; text-align:right }

.card { background:rgba(255,255,255,.03); border:1px solid rgba(255,255,255,.10);
        border-radius:12px; padding:10px 14px; margin-bottom:14px; box-shadow:0 4px 12px rgba(0,0,0,.22); }
.section { color:#ffd54a; font-weight:800; font-size:15px; margin:0 0 8px 0 }

.kpi-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px }
.kpi-card { background:rgba(255,255,255,.03); border:1px solid rgba(255,255,255,.10);
           border-radius:10px; padding:10px 12px; }
.kpi-card .kpi-head{ display:flex; align-items:center; gap:8px; margin-bottom:4px }
.kpi-card .icon{ font-size:14px; margin-right:6px }
.kpi-card .kpi-name{ font-size:14px; font-weight:800 }
.kpi-card .kpi-label{ font-size:10px; color:#aab3cc; margin:0 }
.kpi-card .kpi-value{ font-size:18px; font-weight:800; margin:0 }

.mini-grid{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px }
.mini-card{ background:rgba(255,255,255,.03); border:1px solid rgba(255,255,255,.10);
            border-radius:10px; padding:8px 10px; text-align:center }
.mini-label{ font-size:11px; color:#aab3cc; margin:0 }
.mini-value{ font-size:22px; font-weight:800; margin:2px 0 0 }

.grid-views{ display:grid; grid-template-columns:64px 1fr 90px; gap:10px; align-items:center; margin:6px 0 }
.views-bar{ height:10px; border-radius:6px; background:#1f2736; overflow:hidden }
.views-bar>span{ display:block; height:100%; background:#4aa3ff }

.grid-tasks-2{ display:grid; grid-template-columns:1fr 1.2fr; gap:12px; align-items:center; margin:6px 0 }
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
  .grid-views{ grid-template-columns:56px 1fr 70px }
}
</style>
""", unsafe_allow_html=True)

# ---------- Helpers ----------
def human_format(n) -> str:
    try:
        n = float(n)
    except Exception:
        return str(n)
    units = ["","K","M","B","T"]
    i = 0
    while abs(n) >= 1000 and i < len(units)-1:
        n /= 1000.0
        i += 1
    s = f"{n:.1f}".rstrip("0").rstrip(".")
    return f"{s}{units[i]}"

@st.cache_data(ttl=300)
def http_get(url, params=None, headers=None):
    r = requests.get(url, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=300)
def http_post(url, data=None, headers=None):
    r = requests.post(url, data=data, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

# ---------- YouTube: Data API (subs + total) ----------
@st.cache_data(ttl=300)
def yt_channel_stats(api_key: str, channel_id: str):
    url = "https://www.googleapis.com/youtube/v3/channels"
    p = {"part": "statistics", "id": channel_id, "key": api_key}
    data = http_get(url, p)
    items = data.get("items", [])
    if not items:
        raise RuntimeError("Channel ID not found or key invalid.")
    s = items[0]["statistics"]
    return {"subs": int(s.get("subscriberCount", 0)), "total": int(s.get("viewCount", 0))}

# ---------- YouTube: Analytics (7‑day + countries) via OAuth refresh token ----------
@st.cache_data(ttl=300)
def yt_access_token(client_id, client_secret, refresh_token):
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    resp = http_post(token_url, data=data)
    return resp["access_token"]

@st.cache_data(ttl=300)
def yt_last7_and_countries(client_id, client_secret, refresh_token):
    access = yt_access_token(client_id, client_secret, refresh_token)
    headers = {"Authorization": f"Bearer {access}"}

    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=6)

    # 1) Daily views
    url = "https://youtubeanalytics.googleapis.com/v2/reports"
    q1 = {
        "ids": "channel==MINE",
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "metrics": "views",
        "dimensions": "day",
        "sort": "day",
    }
    d1 = http_get(url, q1, headers=headers)
    daily = [int(r[1]) for r in d1.get("rows", [])]

    # 2) Country views
    q2 = {
        "ids": "channel==MINE",
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "metrics": "views",
        "dimensions": "country",
        "sort": "-views",
        "maxResults": 200,
    }
    d2 = http_get(url, q2, headers=headers)
    rows = d2.get("rows", []) or []
    cdf = pd.DataFrame(rows, columns=["country","views"])
    if not cdf.empty:
        cdf["views"] = cdf["views"].astype(int)
    return daily, cdf

@st.cache_data
def country_centroids():
    data = [
        ("US", 37.09, -95.71), ("MY", 4.21, 101.98), ("PH", 12.88, 121.77),
        ("IN", 20.59, 78.96),  ("KE", -0.02, 37.90), ("AU", -25.27, 133.77),
        ("ID", -0.79, 113.92), ("SG", 1.29, 103.85), ("GB", 55.38, -3.43),
        ("CA", 56.13, -106.35),("NG", 9.08, 8.68),  ("BR", -14.23, -51.92),
        ("DE", 51.17, 10.45),  ("FR", 46.23, 2.21),  ("JP", 36.20, 138.25),
        ("KR", 35.91, 127.76), ("TH", 15.87, 100.99), ("VN", 14.06, 108.28),
        ("MX", 23.63, -102.55),("ES", 40.46, -3.75),
    ]
    return pd.DataFrame(data, columns=["country","lat","lon"])

# ---------- ClickUp tasks ----------
@st.cache_data(ttl=120)
def clickup_tasks(token: str, list_id: str, include_closed=False):
    if not token or not list_id:
        return []
    headers = {"Authorization": token}
    params = {"archived": "false"}
    url = f"https://api.clickup.com/api/v2/list/{list_id}/task"
    try:
        data = http_get(url, params=params, headers=headers)
    except Exception:
        return []
    tasks = []
    for t in data.get("tasks", []):
        if not include_closed and t.get("status", {}).get("status") == "closed":
            continue
        title = t.get("name", "Untitled")
        status = t.get("status", {}).get("status", "unknown")
        tasks.append((title, status))
    return tasks

def task_pct(status: str) -> int:
    s = (status or "").lower()
    if "done" in s or "complete" in s or "closed" in s:
        return 100
    if "progress" in s or "doing" in s or "review" in s:
        return 50
    return 10

def task_cls(status: str) -> str:
    s = (status or "").lower()
    if "done" in s or "complete" in s or "closed" in s:
        return "bar-green"
    if "progress" in s or "doing" in s or "review" in s:
        return "bar-yellow"
    return "bar-red"

# ---------- Google Sheets (filming) ----------
@st.cache_data(ttl=120)
def filming_from_sheet(sa_json_str: str, sheet_url: str = None, sheet_id: str = None):
    if not sa_json_str or not (sheet_url or sheet_id):
        return []
    try:
        import gspread
        from google.oauth2.service_account import Credentials as SACreds
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly"
        ]
        info = json.loads(sa_json_str)
        creds = SACreds.from_service_account_info(info, scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_url(sheet_url) if sheet_url else gc.open_by_key(sheet_id)
        ws = sh.sheet1
        rows = ws.get_all_records()
        items = []
        for r in rows:
            # Expect columns: Date, Time, Activity (case-insensitive)
            date = r.get("Date") or r.get("date") or r.get("DAY") or ""
            time = r.get("Time") or r.get("time") or r.get("TIMING") or ""
            what = r.get("Activity") or r.get("activity") or r.get("WHAT") or ""
            if date or time or what:
                items.append((str(date), str(time), str(what)))
        return items[:12]  # cap
    except Exception:
        return []

# ---------- Secrets ----------
YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY")
CHANNEL_ID = st.secrets.get("YT_PRIMARY_CHANNEL_ID") or st.secrets.get("YOUTUBE_CHANNEL_ID")

YT_CLIENT_ID = st.secrets.get("YT_CLIENT_ID")
YT_CLIENT_SECRET = st.secrets.get("YT_CLIENT_SECRET")
YT_REFRESH_TOKEN = st.secrets.get("YT_REFRESH_TOKEN")

GSERVICE_ACCOUNT = st.secrets.get("GSERVICE_ACCOUNT")  # JSON string
GSHEETS_URL = st.secrets.get("GSHEETS_URL")
GSHEETS_ID = st.secrets.get("GSHEETS_ID")

CLICKUP_TOKEN = st.secrets.get("CLICKUP_TOKEN")
CLICKUP_LIST_ID = st.secrets.get("CLICKUP_LIST_ID")

# ---------- Header ----------
h1, h2 = st.columns([0.75, 0.25])
with h1:
    st.markdown(f"<div class='title'>LOUDVOICE"
                f"<span class='badge badge-ok'>App {APP_VERSION}</span></div>", unsafe_allow_html=True)
with h2:
    now_local = datetime.now()
    st.markdown(f"<div class='timestamp'>{now_local.strftime('%b %d, %Y %I:%M %p')}</div>", unsafe_allow_html=True)

# ---------- Fetch data with explicit status flags ----------
status_msgs = []

# YouTube Data API
yt_live = None
try:
    if YOUTUBE_API_KEY and CHANNEL_ID:
        yt_live = yt_channel_stats(YOUTUBE_API_KEY, CHANNEL_ID)
        status_msgs.append("<span class='badge badge-ok'>Data API: Live</span>")
    else:
        raise RuntimeError("Missing YOUTUBE_API_KEY or CHANNEL_ID")
except Exception as e:
    status_msgs.append(f"<span class='badge badge-err'>Data API: {str(e)[:60]}</span>")
    yt_live = {"subs": 30800, "total": 6000000}

# YouTube Analytics
yt_last7 = None
country_df = None
try:
    if YT_CLIENT_ID and YT_CLIENT_SECRET and YT_REFRESH_TOKEN:
        yt_last7, country_df = yt_last7_and_countries(YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN)
        if not yt_last7 or len(yt_last7) < 1:
            raise RuntimeError("Empty analytics rows")
        status_msgs.append("<span class='badge badge-ok'>Analytics: Live</span>")
    else:
        raise RuntimeError("Missing OAuth secrets")
except Exception as e:
    status_msgs.append(f"<span class='badge badge-warn'>Analytics: Mock ({str(e)[:60]})</span>")
    yt_last7 = [12900, 13200, 12100, 10400, 9800, 11200, 8500]
    country_df = pd.DataFrame({
        "country":["US","MY","PH","IN","KE","AU"],
        "views":[52000,22000,15000,30000,12000,9000]
    })

# ClickUp
try:
    tasks = clickup_tasks(CLICKUP_TOKEN, CLICKUP_LIST_ID) or []
    if tasks:
        # unfinished first
        tasks = sorted(tasks, key=lambda t: 1 if "done" in (t[1] or "").lower() or "closed" in (t[1] or "").lower() else 0)
        status_msgs.append("<span class='badge badge-ok'>ClickUp: Live</span>")
    else:
        status_msgs.append("<span class='badge badge-warn'>ClickUp: None</span>")
except Exception as e:
    tasks = []
    status_msgs.append("<span class='badge badge-warn'>ClickUp err</span>")

# Google Sheets filming
try:
    filming = filming_from_sheet(GSERVICE_ACCOUNT or "", GSHEETS_URL, GSHEETS_ID) or []
    if filming:
        status_msgs.append("<span class='badge badge-ok'>Sheets: Live</span>")
    else:
        status_msgs.append("<span class='badge badge-warn'>Sheets: Empty</span>")
except Exception as e:
    filming = []
    status_msgs.append("<span class='badge badge-warn'>Sheets err</span>")

# Status row
st.markdown(" ".join(status_msgs), unsafe_allow_html=True)

# Compose for display
youtube = {"subs": yt_live["subs"], "total": yt_live["total"]}
ig = {"followers": 6050, "views7": 42300}   # placeholders until IG wired
tt = {"followers": 11032, "views7": 57900}  # placeholders until TT wired
ministry = {"prayer": 15, "studies": 8, "baptisms": 1}

# ---------- Map DF merge ----------
def merge_map_df(df):
    try:
        cent = country_centroids()
        m = df.merge(cent, on="country", how="left").dropna()
        if m.empty:
            return cent.assign(views=0)
        return m
    except Exception:
        cent = country_centroids()
        cent["views"] = 0
        return cent

map_df = merge_map_df(country_df)

# ---------- Layout: Left (Map) • Right (Ministry + Stats + 7-day bars) ----------
left, right = st.columns([1.25, 0.75])

with left:
    st.markdown("<div class='card'><div class='section'>World Map — YouTube Viewers (last 7 days)</div>", unsafe_allow_html=True)
    # Marker size scaled by views
    max_views = int(map_df["views"].max()) if not map_df.empty else 1
    sizes = (map_df["views"] / max(max_views, 1) * 22).clip(lower=6, upper=22) if not map_df.empty else []
    fig = go.Figure(go.Scattergeo(
        lat=map_df.get("lat", []),
        lon=map_df.get("lon", []),
        text=(map_df["country"] + " — " + map_df["views"].map(lambda v: human_format(int(v)))) if not map_df.empty else None,
        mode="markers",
        marker=dict(size=sizes, color="#ffd54a", line=dict(color="#111", width=0.6)),
    ))
    fig.update_layout(
        geo=dict(showland=True, landcolor="#0b0f16",
                 showcountries=True, countrycolor="rgba(255,255,255,.15)",
                 showocean=True, oceancolor="#070a0f"),
        margin=dict(l=0, r=0, t=0, b=0),
        height=(260 if COMPACT else 340),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, theme=None, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    # Ministry tracker (compact 3-col)
    st.markdown("<div class='card'><div class='section'>Ministry Tracker</div>", unsafe_allow_html=True)
    st.markdown(
        f"""
<div class="mini-grid">
  <div class="mini-card"><div class="mini-label">Prayer</div><div class="mini-value">{ministry['prayer']}</div></div>
  <div class="mini-card"><div class="mini-label">Studies</div><div class="mini-value">{ministry['studies']}</div></div>
  <div class="mini-card"><div class="mini-label">Baptisms</div><div class="mini-value'>{ministry['baptisms']}</div></div>
</div>""",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # Channel Stats
    st.markdown("<div class='card'><div class='section'>Channel Stats</div>", unsafe_allow_html=True)
    st.markdown(
        f"""
<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-head"><i class="fab fa-youtube icon" style="color:#ff3d3d"></i><span class="kpi-name">YT</span></div>
    <div class="kpi-label">Subs</div><div class="kpi-value">{human_format(youtube['subs'])}</div>
    <div class="kpi-label">Total</div><div class="kpi-value">{human_format(youtube['total'])}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-head"><i class="fab fa-instagram icon" style="color:#e1306c"></i><span class="kpi-name">IG</span></div>
    <div class="kpi-label">Follows</div><div class="kpi-value">{human_format(ig['followers'])}</div>
    <div class="kpi-label">7‑day Views</div><div class="kpi-value">{human_format(ig['views7'])}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-head"><i class="fab fa-tiktok icon"></i><span class="kpi-name">TT</span></div>
    <div class="kpi-label">Follows</div><div class="kpi-value">{human_format(tt['followers'])}</div>
    <div class="kpi-label">7‑day Views</div><div class="kpi-value">{human_format(tt['views7'])}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # 7‑Day Views aligned bars (order requested)
    st.markdown("<div class='card'><div class='section'>YouTube Views (Last 7 Days)</div>", unsafe_allow_html=True)
    # Normalize to exactly 7 numbers
    if not yt_last7: yt_last7 = [0]*7
    if len(yt_last7) < 7: yt_last7 = ([yt_last7[0]]*(7-len(yt_last7))) + yt_last7
    yt_last7 = yt_last7[-7:]
    labels_order = ["YTD","Tue","Mon","Sun","Sat","Fri","Thu"]
    vals = yt_last7[::-1]  # consistent pairing for display
    pairs = list(zip(labels_order, vals))
    maxv = max([v for _,v in pairs] + [1])
    st.markdown(f"<div class='grid-views'><div>YTD</div><div class='views-bar'><span style='width:0%'></span></div><div style='text-align:right'>0</div></div>", unsafe_allow_html=True)
    for lbl, v in pairs[1:]:
        pct = int((int(v) / maxv) * 100) if maxv else 0
        st.markdown(
            f"<div class='grid-views'><div>{lbl}</div><div class='views-bar'><span style='width:{pct}%'></span></div><div style='text-align:right'>{human_format(int(v))}</div></div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

# ---------- Bottom row: ClickUp + Filming ----------
b1, b2 = st.columns([1.2, 0.8])

with b1:
    st.markdown("<div class='card'><div class='section'>ClickUp Tasks (Upcoming)</div>", unsafe_allow_html=True)
    if tasks:
        for name, status in tasks[:12]:
            st.markdown(
                f"<div class='grid-tasks-2'>"
                f"<div>{name}<div class='small'>{status}</div></div>"
                f"<div class='hbar'><span class='{task_cls(status)}' style='width:{task_pct(status)}%'></span></div>"
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.markdown("<div class='small'>No tasks found (set CLICKUP_TOKEN & CLICKUP_LIST_ID).</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with b2:
    st.markdown("<div class='card'><div class='section'>Next Filming Timeslots</div>", unsafe_allow_html=True)
    if filming:
        for daydate, time_str, what in filming:
            st.markdown(f"<div class='film-row'><div><b>{daydate}</b> — {time_str}</div><div class='film-right'>{what}</div></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='small'>No rows in sheet (add Date / Time / Activity columns).</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# Footer version tag
st.caption(APP_VERSION)
