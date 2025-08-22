import streamlit as st
import json
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests

# ------------------------
# Load config & secrets
# ------------------------
DASHBOARD_JSON = st.secrets.get("DASHBOARD_JSON", "{}")
try:
    cfg = json.loads(DASHBOARD_JSON)
except:
    cfg = {}

# YouTube API keys
YOUTUBE_API_KEY   = st.secrets.get("YOUTUBE_API_KEY")
YT_PRIMARY_CHANNEL_ID = st.secrets.get("YT_PRIMARY_CHANNEL_ID")
YT_CLIENT_ID      = st.secrets.get("YT_CLIENT_ID")
YT_CLIENT_SECRET  = st.secrets.get("YT_CLIENT_SECRET")
YT_REFRESH_TOKEN  = st.secrets.get("YT_REFRESH_TOKEN")

# Google Sheets (service account)
SHEETS_DOC_ID     = st.secrets.get("google_sheets", {}).get("spreadsheet_id")

# ClickUp
CLICKUP_TOKEN     = st.secrets.get("CLICKUP_TOKEN")
CLICKUP_LIST_ID   = st.secrets.get("CLICKUP_LIST_ID")

# ------------------------
# Page Config
# ------------------------
st.set_page_config(page_title="LoudVoice Dashboard", layout="wide")
st.title("📊 LoudVoice Ministry Dashboard")

# ------------------------
# Utility Functions
# ------------------------
def yt_channel_stats(api_key, channel_id):
    try:
        url = "https://www.googleapis.com/youtube/v3/channels"
        params = {"part": "statistics", "id": channel_id, "key": api_key}
        r = requests.get(url, params=params).json()
        stats = r["items"][0]["statistics"]
        return {
            "subs": int(stats["subscriberCount"]),
            "views": int(stats["viewCount"]),
            "videos": int(stats["videoCount"])
        }
    except Exception as e:
        st.error(f"YouTube Data API error: {e}")
        return {"subs":0, "views":0, "videos":0}

def yt_analytics_last7_and_countries(client_id, client_secret, refresh_token):
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        import requests as rq

        creds = Credentials(
            None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/yt-analytics.readonly"]
        )
        creds.refresh(Request())
        analytics = build("youtubeAnalytics", "v2", credentials=creds)

        end = date.today()
        start = end - timedelta(days=6)

        resp = analytics.reports().query(
            ids="channel==MINE",
            startDate=start.isoformat(),
            endDate=end.isoformat(),
            metrics="views",
            dimensions="day",
            sort="day"
        ).execute()
        last7 = pd.DataFrame(resp.get("rows", []), columns=["date", "views"])

        resp2 = analytics.reports().query(
            ids="channel==MINE",
            startDate=start.isoformat(),
            endDate=end.isoformat(),
            metrics="views",
            dimensions="country",
            sort="-views",
            maxResults=10
        ).execute()
        country = pd.DataFrame(resp2.get("rows", []), columns=["country","views"])
        return last7, country
    except Exception as e:
        st.info("Using mock for YT 7-day & country (Analytics call failed).")
        last7 = pd.DataFrame({
            "date": pd.date_range(end=date.today(), periods=7).strftime("%Y-%m-%d"),
            "views": [100,150,120,130,170,200,250]
        })
        country = pd.DataFrame({"country":["US","MY","SG"],"views":[120,80,60]})
        return last7, country

def load_clickup_tasks(token, list_id):
    try:
        url = f"https://api.clickup.com/api/v2/list/{list_id}/task"
        headers = {"Authorization": token}
        r = requests.get(url, headers=headers).json()
        tasks = [t["name"] for t in r.get("tasks",[])]
        return tasks
    except Exception as e:
        st.warning("ClickUp fetch failed, using mock.")
        return ["Publish Bahasa caption pack","Update media kit","Plan outreach schedule"]

def load_google_sheet(spreadsheet_id):
    try:
        creds = service_account.Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]),
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        service = build("sheets","v4",credentials=creds)
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=spreadsheet_id, range="Sheet1!A1:C10").execute()
        values = result.get("values", [])
        df = pd.DataFrame(values[1:], columns=values[0])
        return df
    except Exception as e:
        st.warning("Sheets fetch failed, using mock.")
        return pd.DataFrame([
            {"When":"Thu 2–4pm","What":"Bahasa short — EP12"},
            {"When":"Sat 9:30–11am","What":"Choir session"},
            {"When":"Tue 3–5pm","What":"Testimony w/ Mary"}
        ])

# ------------------------
# Layout
# ------------------------
col1, col2 = st.columns([1,2])

with col1:
    st.subheader("🌍 Reach by Country")
    yt_last7, yt_country = yt_analytics_last7_and_countries(YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN)
    fig = px.bar(yt_country, x="country", y="views", text="views")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("📺 Channel KPIs")
    yt_stats = yt_channel_stats(YOUTUBE_API_KEY, YT_PRIMARY_CHANNEL_ID)
    c1, c2, c3 = st.columns(3)
    c1.metric("Subscribers", f"{yt_stats['subs']:,}")
    c2.metric("Total Views", f"{yt_stats['views']:,}")
    c3.metric("Videos", f"{yt_stats['videos']:,}")

    st.markdown("### 📈 Views (Last 7 Days)")
    fig2 = px.line(yt_last7, x="date", y="views", markers=True)
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

c1, c2 = st.columns(2)
with c1:
    st.subheader("✅ ClickUp Weekly Tasks")
    tasks = load_clickup_tasks(CLICKUP_TOKEN, CLICKUP_LIST_ID)
    for t in tasks:
        st.write("- ", t)

with c2:
    st.subheader("🎬 Filming Schedule (Google Sheets)")
    df = load_google_sheet(SHEETS_DOC_ID)
    st.table(df)
