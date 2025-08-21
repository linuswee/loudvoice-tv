
import os
import json
import datetime as dt
import pytz
import requests
import streamlit as st
import pandas as pd

# ===========================
# Helpers
# ===========================

def human_format(value):
    """Format numbers as K / M / B with trimmed decimals."""
    if value is None:
        return "0"
    try:
        num = float(value)
    except Exception:
        return str(value)

    units = ["", "K", "M", "B", "T"]
    for u in units:
        if abs(num) < 1000 or u == units[-1]:
            s = f"{num:.1f}".rstrip("0").rstrip(".")
            return f"{s}{u}"
        num /= 1000.0

def load_secrets():
    return {
        "DASHBOARD_JSON": os.getenv("DASHBOARD_JSON", ""),
        "YOUTUBE_API_KEY": os.getenv("YOUTUBE_API_KEY", ""),
        "YOUTUBE_CHANNEL_ID": os.getenv("YOUTUBE_CHANNEL_ID", ""),
        "YT_PRIMARY_CHANNEL_ID": os.getenv("YT_PRIMARY_CHANNEL_ID", ""),
        "YT_CLIENT_ID": os.getenv("YT_CLIENT_ID", ""),
        "YT_CLIENT_SECRET": os.getenv("YT_CLIENT_SECRET", ""),
        "YT_REFRESH_TOKEN": os.getenv("YT_REFRESH_TOKEN", ""),
        "YT_REDIRECT_URI": os.getenv("YT_REDIRECT_URI", ""),
        "TIMEZONE": os.getenv("TIMEZONE", "Asia/Kuala_Lumpur"),
    }

def youtube_channel_stats(api_key, channel_id):
    url = f"https://www.googleapis.com/youtube/v3/channels?part=statistics&id={channel_id}&key={api_key}"
    r = requests.get(url)
    data = r.json()
    if "items" in data and len(data["items"]) > 0:
        stats = data["items"][0]["statistics"]
        return {
            "subs": int(stats.get("subscriberCount", 0)),
            "views": int(stats.get("viewCount", 0))
        }
    return {"subs": 0, "views": 0}

def get_youtube_7day_views():
    # Mock for now, replace with Analytics API call if refresh_token available
    today = dt.date.today()
    days = ["YTD", "TUE", "MON", "SUN", "SAT", "FRI", "THU"]
    values = [12000, 10500, 9800, 11200, 13400, 12800, 14000]
    return pd.DataFrame({"Day": days, "Views": values})

# ===========================
# Main app
# ===========================

def main():
    secrets = load_secrets()
    tz = pytz.timezone(secrets["TIMEZONE"])	
    now = dt.datetime.now(tz)
    
    st.set_page_config(layout="wide")
    st.title("LoudVoice Dashboard")
    st.caption(f"As of {now.strftime('%Y-%m-%d %H:%M %Z')}")

    # Layout: Left column world map, right column everything else
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("World Map")
        st.map(pd.DataFrame({
            "lat": [3.1390, 13.7563],
            "lon": [101.6869, 100.5018]
        }))

    with col2:
        # Ministry Tracker
        st.subheader("Ministry Tracker")
        st.write("3-column tracker layout (mock)")
        tracker_cols = st.columns(3)
        tracker_cols[0].metric("Videos", "45")
        tracker_cols[1].metric("Bible Studies", "12")
        tracker_cols[2].metric("Prayers", "78")

        # Channel Stats
        st.subheader("Channel Stats")
        yt_channel_id = secrets["YT_PRIMARY_CHANNEL_ID"] or secrets["YOUTUBE_CHANNEL_ID"]
        yt_stats = youtube_channel_stats(secrets["YOUTUBE_API_KEY"], yt_channel_id)
        stats_cols = st.columns(3)
        stats_cols[0].metric("YT Subs", human_format(yt_stats["subs"]))
        stats_cols[1].metric("YT Views", human_format(yt_stats["views"]))
        stats_cols[2].metric("IG Followers", "6.0K")  # mock

        # 7-day views
        st.subheader("7-Day Views")
        df = get_youtube_7day_views()
        st.bar_chart(df.set_index("Day"))

        # ClickUp Tasks (mock)
        st.subheader("ClickUp Tasks")
        tasks = [
            {"title": "Outline next video", "status": "Not Ready"},
            {"title": "Shoot testimony interview", "status": "In Progress"},
            {"title": "Schedule weekend posts", "status": "Done"}
        ]
        not_done = [t for t in tasks if t["status"] != "Done"]
        done = [t for t in tasks if t["status"] == "Done"]
        for t in not_done + done:
            st.write(f"- [{t['status']}] {t['title']}")

        # Filming Schedule (mock)
        st.subheader("Upcoming Filming")
        filming = [
            {"when": "Thu 2:00–4:00 PM", "what": "Bahasa short — EP12"},
            {"when": "Sat 9:30–11:00 AM", "what": "Choir session"},
            {"when": "Tue 3:00–5:00 PM", "what": "Testimony w/ Mary"}
        ]
        for f in filming:
            st.write(f"{f['when']} — {f['what']}")

if __name__ == "__main__":
    main()
