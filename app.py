
import streamlit as st
import requests
import datetime
import plotly.express as px

# ==============================
# Load API key safely
# ==============================
YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]
YT_CHANNEL_ID = "UCQG6u_udp_Hnjq7iTq-X4rw"  # LoudVoice channel

# ==============================
# Helper: format big numbers
# ==============================
def human_format(num):
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(num)

# ==============================
# YouTube API fetch
# ==============================
def get_channel_stats(api_key, channel_id):
    url = f"https://www.googleapis.com/youtube/v3/channels?part=statistics&id={channel_id}&key={api_key}"
    r = requests.get(url)
    if r.status_code != 200:
        return None
    data = r.json()
    stats = data["items"][0]["statistics"]
    return {
        "subs": int(stats["subscriberCount"]),
        "views": int(stats["viewCount"]),
        "videos": int(stats["videoCount"]),
    }

# ==============================
# Mock last 7-day YouTube views
# ==============================
def get_last_7_days_views():
    # Replace this mock with real YouTube Analytics API if needed
    return {
        "Thu": 786,
        "Fri": 657,
        "Sat": 385,
        "Sun": 276,
        "Mon": 276,
        "Tue": 276,
        "YTD": 276,
    }

# ==============================
# Main dashboard
# ==============================
def main():
    st.set_page_config(page_title="LoudVoice Dashboard", layout="wide")

    st.title("📊 LoudVoice Ministry Dashboard")
    st.caption(f"As of {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # ---- Channel Stats ----
    yt_stats = get_channel_stats(YOUTUBE_API_KEY, YT_CHANNEL_ID)
    if yt_stats:
        col1, col2, col3 = st.columns(3)
        col1.metric("YouTube Subs", human_format(yt_stats["subs"]))
        col2.metric("Total Views", human_format(yt_stats["views"]))
        col3.metric("Videos", yt_stats["videos"])
    else:
        st.error("Failed to fetch YouTube stats. Check API key.")

    st.markdown("---")

    # ---- 7-Day Views ----
    st.subheader("📈 YouTube Views (Last 7 Days)")
    daily_views = get_last_7_days_views()

    # Bar chart
    fig = px.bar(
        x=list(daily_views.keys()),
        y=list(daily_views.values()),
        labels={"x": "Day", "y": "Views"},
        text=list(daily_views.values()),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Horizontal bar chart
    st.bar_chart(daily_views)

# ==============================
# Run
# ==============================
if __name__ == "__main__":
    main()
