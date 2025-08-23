__LV_VERSION__ = "v3.1b-cards-alignedbars (sha:0523c1c9, refactor-01)"

# app.py — LoudVoice Dashboard (cards + aligned bars layout)

from datetime import datetime, timedelta
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
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
except Exception:
    GOOGLE_OK = False

# -------------------------------
# Page config & compact helpers
# -------------------------------
st.set_page_config(page_title="LOUDVOICE", page_icon="📊", layout="wide")
st_autorefresh(interval=5 * 60 * 1000, key="auto_refresh")  # 5 minutes
qp = st.query_params
ZOOM = qp.get("zoom", ["100"])[0]
COMPACT = qp.get("compact", ["0"])[0].lower() in ("1", "true", "yes")
# QoL: force clear all Streamlit caches via ?clear_cache=1
if qp.get("clear_cache", ["0"])[0] in ("1","true","yes"):
    st.cache_data.clear()
    st.toast("Cache cleared", icon="♻️")

# Optional debug panel via ?debug=1
DEBUG = qp.get("debug", ["0"])[0].lower() in ("1","true","yes")
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

# =======================
# Helpers & Data calls
# =======================

LOCAL_TZ = "Asia/Kuala_Lumpur"   # change if your Studio timezone differs
DAYS_FOR_MAP = 28                # 28‑day country map window
MAP_HEIGHT = 600 if not COMPACT else 420  # taller map so it fills space

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

    end_date = (datetime.utcnow().date() - timedelta(days=1))          # yesterday
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

        end_date = (datetime.utcnow().date() - timedelta(days=1))  # yesterday
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

    # Reserve a *thin* bottom band just for the colorbar
    bottom_band = 0.08                 # was ~0.16; smaller = more room for the map
    colorbar_y  = bottom_band / 2.0    # centers the bar in that band
    fig = go.Figure(
        go.Choropleth(
            locations=choro_df["iso3"],
            z=z,
            customdata=np.stack([choro_df["name"], z_raw], axis=1),
            hovertemplate="<b>%{customdata[0]}</b><br>Views: %{customdata[1]:,}<extra></extra>",
            colorscale=[
                [0.00, "#0b0f16"],  # black
                [0.20, "#ffe600"],  # yellow
                [0.40, "#ff3b3b"],  # red
                [0.70, "#4285f4"],  # blue
                [1.00, "#34a853"],  # green
            ],
            marker_line_color="rgba(255,255,255,.08)",
            marker_line_width=0.5,
            colorbar=dict(
                title="Views (log scale)",
                orientation="h",
                x=0.5, xanchor="center",
                y=colorbar_y, yanchor="middle",   # drop it further down
                lenmode="fraction", len=0.96,     # make it almost full width
                thickness=16,
                outlinewidth=0,
                ticks="outside",
                tickvals=tickvals,
                ticktext=ticktext,
            ),
        )
    )

    fig.update_layout(
    geo=dict(
        projection_type="natural earth",
        bgcolor="rgba(0,0,0,0)",
        showocean=True, oceancolor="#070a0f",
        showland=True, landcolor="#0b0f16",
        showcountries=True, countrycolor="rgba(255,255,255,.10)",
        domain=dict(x=[0.00, 1.00], y=[bottom_band, 1.00]),  # map uses everything above the legend
    ),
    margin=dict(l=0, r=0, t=0, b=0),  # no extra bottom margin
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

    creds = Credentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=[
            "https://www.googleapis.com/auth/youtube.readonly",
            "https://www.googleapis.com/auth/yt-analytics.readonly",
        ],
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

    end_date = (datetime.utcnow().date() - timedelta(days=1))          # yesterday
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

def build_world_map(map_df: pd.DataFrame, height: int) -> go.Figure:
    sizes = (map_df["views"] / max(map_df["views"].max(), 1) * 22).clip(lower=6, upper=22)
    fig = go.Figure(
        go.Scattergeo(
            lat=map_df["lat"],
            lon=map_df["lon"],
            text=map_df["name"] + " — " + map_df["views"].astype(int).map(fmt_num),
            mode="markers",
            marker=dict(color="#ffd54a", size=sizes, line=dict(color="#111", width=0.6)),
            hovertemplate="<b>%{text}</b><extra></extra>",
        )
    )
    fig.update_layout(
        geo=dict(
            showland=True, landcolor="#0b0f16",
            showcountries=True, countrycolor="rgba(255,255,255,.15)",
            showocean=True, oceancolor="#070a0f",
            fitbounds="locations",  # <— zoom to your bubbles so it fills the card
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig

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
    """
    Returns a list of dicts [{name, status, due_str}] from a ClickUp List.
    - Sorts by due date
    - Hides archived and completed items
    """
    url = f"https://api.clickup.com/api/v2/list/{list_id}/task"
    headers = {"Authorization": token}
    params = {
        "archived": "false",
        "subtasks": "true",
        "order_by": "due_date",
        "reverse": "false",
        "page": 0,
        "include_closed": "false",  # exclude 'done/closed'
    }
    try:
        r = requests.get(url, headers=headers, params=params, timeout=20)
        r.raise_for_status()
        items = (r.json() or {}).get("tasks", [])
    except Exception as e:
        # Bubble a friendly error to the UI
        return [], f"ClickUp error: {e}"

    out = []
    for t in items:
        status = (t.get("status") or {}).get("status", "")  # e.g. 'to do', 'in progress', 'review', 'complete'
        status_type = (t.get("status") or {}).get("type", "")  # e.g. 'open', 'done'
        if status_type == "done":
            continue  # hide completed

        name = t.get("name", "Untitled")
        due_ms = t.get("due_date")  # millisecond timestamp string
        due_str = ""
        if due_ms:
            try:
                due_dt = datetime.utcfromtimestamp(int(due_ms) / 1000)
                due_str = due_dt.strftime("%a, %b %d")
            except Exception:
                pass
        out.append({"name": name, "status": status, "due_str": due_str})

    # sort by due first, then name
    out.sort(key=lambda x: (x["due_str"] == "", x["due_str"], x["name"].lower()))
    return out[:limit], ""

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

# =======================
# Fetch live data
# =======================
youtube = {"subs": MOCK["yt_subs"], "total": MOCK["yt_total"]}
ig = {"followers": MOCK["ig_followers"], "views7": MOCK["ig_views7"]}
tt = {"followers": MOCK["tt_followers"], "views7": MOCK["tt_views7"]}
ministry = MOCK["ministry"]

# ---- ClickUp live tasks (fallback to mock) ----
tasks = []
if _secret_missing("CLICKUP_TOKEN") or _secret_missing("CLICKUP_LIST_ID"):
    tasks = [(n, s, "") for (n, s) in MOCK["tasks"]]
else:
    cu_token = st.secrets.get("CLICKUP_TOKEN")
    cu_list  = st.secrets.get("CLICKUP_LIST_ID")

if cu_token and cu_list:
    with st.spinner("Loading ClickUp tasks…"):
        tasks_live, cu_err = clickup_tasks_upcoming(cu_token, cu_list, limit=12)
    if cu_err:
        st.warning(cu_err)
    else:
        # Convert to tuples for the UI loop: (name, status, due_str)
        tasks = [(t["name"], t["status"], t["due_str"]) for t in tasks_live]

if not tasks:
    # fallback to your mock
    tasks = [(n, s, "") for (n, s) in MOCK["tasks"]]
    
filming = MOCK["filming"]

# KPI card via Data API
yt_api_key = st.secrets.get("YOUTUBE_API_KEY")
yt_channel_id = st.secrets.get("YT_PRIMARY_CHANNEL_ID") or st.secrets.get("YOUTUBE_CHANNEL_ID")
if yt_api_key and yt_channel_id:
    try:
        youtube = yt_channel_stats(yt_api_key, yt_channel_id)
    except Exception:
        pass

# Analytics (28‑day map + real last‑7 with *local* dates)
yt_client_id     = st.secrets.get("YT_CLIENT_ID")
yt_client_secret = st.secrets.get("YT_CLIENT_SECRET")
yt_refresh_token = st.secrets.get("YT_REFRESH_TOKEN")

# Use OAuth identity to 1) confirm we’re on the right channel and
# 2) drive Channel Stats numbers (subs + lifetime views).
oauth_title = ""
if yt_client_id and yt_client_secret and yt_refresh_token:
    try:
        who = oauth_channel_identity(yt_client_id, yt_client_secret, yt_refresh_token)
        oauth_title = who.get("title", "")
        # Override the KPI card numbers with the *actual* authenticated channel’s stats
        youtube = {"subs": who["subs"], "total": who["views"]}
    except Exception as _e:
        # keep existing youtube numbers if this fails
        pass
        
daily_df = pd.DataFrame()
cdf = pd.DataFrame()
analytics_err = ""
if yt_client_id and yt_client_secret and yt_refresh_token:
    with st.spinner("Fetching YouTube Analytics…"):
        daily_df, cdf, analytics_err = yt_analytics_lastN_and_countries(
            yt_client_id, yt_client_secret, yt_refresh_token, days=DAYS_FOR_MAP
        )
    if not daily_df.empty:
        daily_df = normalize_daily_to_local(daily_df, LOCAL_TZ)

# ---- Last‑7 bars from YouTube Analytics (fallback to mock if needed) ----
yt_client_id     = st.secrets.get("YT_CLIENT_ID")
yt_client_secret = st.secrets.get("YT_CLIENT_SECRET")
yt_refresh_token = st.secrets.get("YT_REFRESH_TOKEN")
yt_channel_id    = st.secrets.get("YT_PRIMARY_CHANNEL_ID") or st.secrets.get("YOUTUBE_CHANNEL_ID")

last7_df = pd.DataFrame()
bars_err = ""

if yt_client_id and yt_client_secret and yt_refresh_token:
    try:
        last7_df = yt_analytics_daily_lastN(
            yt_client_id, yt_client_secret, yt_refresh_token,
            days=7
        )
        # If you use timezone normalization elsewhere, uncomment:
        # last7_df = normalize_daily_to_local(last7_df, LOCAL_TZ)
    except Exception as e:
        bars_err = str(e)

if not last7_df.empty:
    # Already ordered by 'day'; keep as-is for labels like "Aug 15"
    yt_last7_vals   = last7_df["views"].astype(int).tolist()
    yt_last7_labels = last7_df["date"].dt.strftime("%b %d").tolist()
else:
    # Fallback to your existing mock numbers & generated labels
    yt_last7_vals = MOCK["yt_last7"]
    base = (datetime.utcnow().date() - timedelta(days=1))
    yt_last7_labels = [(base - timedelta(days=i)).strftime("%b %d") for i in range(6, -1, -1)]
if bars_err:
    st.warning(f"YT Analytics (daily) error: {bars_err}")

# Country map dataframe for choropleth (no lat/lon needed)
if not cdf.empty:
    choro_df = cdf.copy()
else:
    choro_df = MOCK["yt_countries"].copy()

# Ensure we have ISO-3 codes
choro_df["iso3"] = choro_df["country"].apply(country_to_iso3)
choro_df = choro_df.dropna(subset=["iso3"])

analytics_ok = (not daily_df.empty) or (not cdf.empty)
if not analytics_ok and analytics_err:
    st.warning(f"YT Analytics error: {analytics_err}")

# =======================
# Header
# =======================
t1, t2 = st.columns([0.75, 0.25])
with t1:
    st.markdown("<div class='title'>LOUDVOICE</div>", unsafe_allow_html=True)
with t2:
    now = datetime.now().strftime('%B %d, %Y %I:%M %p')
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
    
    # ---- Country map dataframe (live from YouTube Analytics if available) ----
    yt_client_id     = st.secrets.get("YT_CLIENT_ID")
    yt_client_secret = st.secrets.get("YT_CLIENT_SECRET")
    yt_refresh_token = st.secrets.get("YT_REFRESH_TOKEN")
    yt_channel_id    = st.secrets.get("YT_PRIMARY_CHANNEL_ID") or st.secrets.get("YOUTUBE_CHANNEL_ID")
    
    cdf = pd.DataFrame()
    analytics_err = ""
    
    if yt_client_id and yt_client_secret and yt_refresh_token:
        try:
            cdf = yt_analytics_country_lastN(
                yt_client_id, yt_client_secret, yt_refresh_token,
                days=DAYS_FOR_MAP
            )
        except Exception as e:
            analytics_err = str(e)
    
    # Build the choropleth input. If API fails, we fall back to your mock.
    if not cdf.empty:
        # Use ALL countries present; missing ones will default to 0 inside build_choro_dataframe
        country_views = dict(zip(cdf["country"], cdf["views"]))
    else:
        # Fallback to your mock/sample until API is configured
        country_views = {c: int(v) for c, v in zip(MOCK["yt_countries"]["country"], MOCK["yt_countries"]["views"])}
    
    # This uses your existing helper from the previous iteration
    choro_df = build_choro_dataframe(country_views)
    
    if analytics_err:
        st.warning(f"YT Analytics (country) error: {analytics_err}")
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
    connected = f"<span class='small'>Connected: <b>{oauth_title}</b></span>" if oauth_title else ""
    st.markdown(f"<div class='card'><div class='section'>Channel Stats {connected}</div>", unsafe_allow_html=True)
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

    # YouTube Views (Last 7 Days) — with real daily dates
    st.markdown("<div class='card'><div class='section'>YouTube Views (Last 7 Days)</div>", unsafe_allow_html=True)
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

# Bottom: ClickUp tasks + Filming (unchanged)
b1, b2 = st.columns([1.2, 0.8])
with b1:
    st.markdown("<div class='card'><div class='section'>ClickUp Tasks (Upcoming)</div>", unsafe_allow_html=True)
    for name, status, due_str in tasks:
        small_line = f"{status}" + (f" · due {due_str}" if due_str else "")
        st.markdown(
            f"<div class='grid-tasks-2'>"
            f"<div>{name}<div class='small'>{small_line}</div></div>"
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

st.caption("Tips → ?zoom=115 for TV; ?compact=1 for phones. Provide YOUTUBE_API_KEY & YT_PRIMARY_CHANNEL_ID for KPIs, and YT_CLIENT_ID/SECRET/REFRESH for true 7‑day & country map.")
