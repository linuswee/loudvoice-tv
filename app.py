
import streamlit as st
import requests
import os

# --- Utility ---
def format_number(n):
    try:
        n = int(n)
    except:
        return n
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.1f}B"
    elif n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)

# --- YouTube Stats ---
def fetch_youtube_stats():
    api_key = os.getenv("YOUTUBE_API_KEY")
    channel_id = os.getenv("YT_PRIMARY_CHANNEL_ID")
    if not api_key or not channel_id:
        return {"subs": "N/A", "views": "N/A"}

    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "part": "statistics",
        "id": channel_id,
        "key": api_key
    }
    r = requests.get(url, params=params)
    if r.status_code != 200:
        return {"subs": "Error", "views": "Error"}
    data = r.json()
    try:
        stats = data["items"][0]["statistics"]
        return {
            "subs": format_number(stats["subscriberCount"]),
            "views": format_number(stats["viewCount"])
        }
    except Exception as e:
        return {"subs": "Err", "views": "Err"}

# --- Mock IG/TikTok + Views ---
def fetch_instagram_stats():
    return {"followers": "12.5K", "views": "102K"}

def fetch_tiktok_stats():
    return {"followers": "8.3K", "views": "88K"}

def fetch_7day_views():
    return {"YouTube": "1.2M", "Instagram": "650K", "TikTok": "720K"}

# --- UI ---
st.set_page_config(page_title="LoudVoice Dashboard", layout="wide")
st.title("LoudVoice Ministry Dashboard")

col1, col2 = st.columns([2, 3])

# Ministry tracker (left col1)
with col1:
    st.subheader("Ministry Tracker")
    studies = 8
    baptisms = 1
    colA, colB = st.columns(2)
    colA.metric("Studies", studies)
    colB.metric("Baptisms", baptisms)

# Channel stats & 7-day (col2)
with col2:
    st.subheader("Channel Stats")

    yt_stats = fetch_youtube_stats()
    ig_stats = fetch_instagram_stats()
    tt_stats = fetch_tiktok_stats()

    colY, colI, colT = st.columns(3)
    with colY:
        st.markdown("### YouTube")
        st.metric("Subscribers", yt_stats["subs"])
        st.metric("Total Views", yt_stats["views"])
    with colI:
        st.markdown("### Instagram")
        st.metric("Followers", ig_stats["followers"])
        st.metric("Total Views", ig_stats["views"])
    with colT:
        st.markdown("### TikTok")
        st.metric("Followers", tt_stats["followers"])
        st.metric("Total Views", tt_stats["views"])

    st.subheader("True 7-Day Views")
    views = fetch_7day_views()
    colV1, colV2, colV3 = st.columns(3)
    colV1.metric("YouTube", views["YouTube"])
    colV2.metric("Instagram", views["Instagram"])
    colV3.metric("TikTok", views["TikTok"])

# Placeholder for ClickUp + Filming
st.subheader("ClickUp Integration (Coming Soon)")
st.info("Tasks and project management will be displayed here.")

st.subheader("Filming Schedule (Coming Soon)")
st.info("Google Calendar integration planned.")
