import os
import json
import requests
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# -------------------
# Secrets & Config
# -------------------
DASHBOARD_JSON = os.environ.get("DASHBOARD_JSON", "{}")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
YT_PRIMARY_CHANNEL_ID = os.environ.get("YT_PRIMARY_CHANNEL_ID")

YT_CLIENT_ID = os.environ.get("YT_CLIENT_ID")
YT_CLIENT_SECRET = os.environ.get("YT_CLIENT_SECRET")
YT_REDIRECT_URI = os.environ.get("YT_REDIRECT_URI")
YT_REFRESH_TOKEN = os.environ.get("YT_REFRESH_TOKEN")

CLICKUP_TOKEN = os.environ.get("CLICKUP_TOKEN", "")
CLICKUP_LIST_ID = os.environ.get("CLICKUP_LIST_ID", "")

GSHEET_ID = os.environ.get("GSHEET_ID", "")
GSHEET_RANGE = os.environ.get("GSHEET_RANGE", "A1:D20")
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")

# -------------------
# Utils
# -------------------
def format_number(num: int) -> str:
    if num >= 1_000_000_000:
        return f"{num/1_000_000_000:.1f}B"
    elif num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(num)

# -------------------
# YouTube Data API
# -------------------
def get_channel_stats():
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "part": "statistics",
        "id": YT_PRIMARY_CHANNEL_ID,
        "key": YOUTUBE_API_KEY,
    }
    r = requests.get(url, params=params)
    data = r.json()
    try:
        stats = data["items"][0]["statistics"]
        return {
            "subs": int(stats["subscriberCount"]),
            "views": int(stats["viewCount"]),
            "videos": int(stats["videoCount"]),
        }
    except Exception:
        return {"subs": 0, "views": 0, "videos": 0}

# -------------------
# YouTube Analytics API
# -------------------
def get_yt_service():
    creds = Credentials(
        None,
        refresh_token=YT_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YT_CLIENT_ID,
        client_secret=YT_CLIENT_SECRET,
    )
    return build("youtubeAnalytics", "v2", credentials=creds)

def get_7day_views():
    service = get_yt_service()
    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=6)
    resp = service.reports().query(
        ids=f"channel=={YT_PRIMARY_CHANNEL_ID}",
        startDate=str(start_date),
        endDate=str(end_date),
        metrics="views",
        dimensions="day"
    ).execute()
    rows = resp.get("rows", [])
    df = pd.DataFrame(rows, columns=["date","views"])
    df["date"] = pd.to_datetime(df["date"])
    return df

def get_country_views():
    service = get_yt_service()
    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=28)
    resp = service.reports().query(
        ids=f"channel=={YT_PRIMARY_CHANNEL_ID}",
        startDate=str(start_date),
        endDate=str(end_date),
        metrics="views",
        dimensions="country"
    ).execute()
    rows = resp.get("rows", [])
    df = pd.DataFrame(rows, columns=["country","views"])
    return df

# -------------------
# ClickUp Tasks
# -------------------
def get_clickup_tasks():
    if not CLICKUP_TOKEN or not CLICKUP_LIST_ID:
        return []
    url = f"https://api.clickup.com/api/v2/list/{CLICKUP_LIST_ID}/task"
    headers = {"Authorization": CLICKUP_TOKEN}
    r = requests.get(url, headers=headers)
    tasks = r.json().get("tasks", [])
    return [{"title": t["name"], "status": t["status"]["status"]} for t in tasks]

# -------------------
# Google Sheets (Filming Schedule)
# -------------------
def get_filming_schedule():
    try:
        from google.oauth2.service_account import Credentials as SACreds
        import gspread
        creds_dict = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        creds = SACreds.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(GSHEET_ID).worksheet("Sheet1")
        rows = sheet.get_all_values()
        df = pd.DataFrame(rows[1:], columns=rows[0])
        return df
    except Exception:
        return pd.DataFrame()

# -------------------
# Streamlit UI
# -------------------
st.set_page_config(page_title="LoudVoice Dashboard", layout="wide")

st.title("📊 LoudVoice Ministry Dashboard")
st.caption(f"Last updated {datetime.now().strftime('%Y-%m-%d %I:%M %p')}")

# Layout
col1, col2 = st.columns([2,3])

with col1:
    st.subheader("🌍 Audience Map")
    try:
        df_country = get_country_views()
        st.map(df_country.rename(columns={"country":"lat"}))  # placeholder map
    except Exception:
        st.info("No map data yet.")

with col2:
    stats = get_channel_stats()
    st.subheader("📺 Channel Stats")
    c1, c2, c3 = st.columns(3)
    c1.metric("Subscribers", format_number(stats["subs"]))
    c2.metric("Total Views", format_number(stats["views"]))
    c3.metric("Videos", format_number(stats["videos"]))

    st.subheader("📈 Last 7 Days Views")
    df = get_7day_views()
    st.line_chart(df.set_index("date"))

    st.subheader("✅ ClickUp Tasks")
    tasks = get_clickup_tasks()
    for t in tasks:
        st.write(f"- [{t['status']}] {t['title']}")

    st.subheader("🎥 Filming Schedule")
    df_sched = get_filming_schedule()
    if not df_sched.empty:
        st.dataframe(df_sched)
    else:
        st.info("No filming schedule found.")

