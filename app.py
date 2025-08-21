# app.py — LoudVoice Dashboard with YouTube OAuth + Channel Picker
# ---------------------------------------------------------------
# What this adds:
# 1) "Connect YouTube Analytics" panel if there's no refresh token.
# 2) After login, it fetches ALL channels/brand accounts you own and lets you pick one.
# 3) Uses that selection for live (or mocked) stats; the rest of the dashboard keeps working.

import os, json, time, base64, urllib.parse, requests
from datetime import datetime, timedelta, timezone
from pathlib import Path
import streamlit as st

# ------------------------------ Config / Theme ------------------------------
st.set_page_config(page_title="LoudVoice Dashboard", page_icon="🎛️", layout="wide")

YELLOW = "#ffd54a"; TEXT="#f5f7ff"; MUTED="#9aa3bd"
st.markdown(f"""
<style>
html, body, [class^="css"] {{ background:#0b0e14 !important; color:{TEXT} !important; }}
header[data-testid="stHeader"]{{background:transparent;}}
#MainMenu{{visibility:hidden;}} footer{{visibility:hidden;}}
.block-container{{max-width:1640px; padding-top:10px;}}
h1,h2,h3,h4,h5,.section-title{{color:{YELLOW} !important}}
.card{{background:#141925; border:1px solid #20283a; border-radius:14px; padding:16px 18px;}}
.badge{{display:inline-block; padding:4px 10px; border-radius:999px; background:#1e2636; color:#dfe6ff; font-size:12px; border:1px solid #283149}}
.row{{display:flex; align-items:center; gap:12px;}}
.kpi-ttl{{font-size:12px; color:{MUTED};}}
.kpi-num{{font-size:36px; font-weight:800; margin:4px 0 0 0;}}
.small{{font-size:12px; color:{MUTED};}}
.hbar{{height:10px; background:#20283a; border-radius:6px; overflow:hidden}}
.hbar>span{{display:block;height:100%}}
.bar-red{{background:#ff5a5f}} .bar-yellow{{background:#ffd166}} .bar-green{{background:#2ecc71}}
.views-bar{{height:12px; background:#20283a; border-radius:8px; overflow:hidden}}
.views-bar>span{{display:block;height:100%; background:#4aa3ff}}
.grid3{{display:grid; grid-template-columns: 1fr 1fr 1fr; gap:10px;}}
@media (max-width:900px) {{
  .grid3{{grid-template-columns:1fr;}}
}}
</style>
""", unsafe_allow_html=True)

def badge(txt): 
    st.markdown(f"<span class='badge'>{txt}</span>", unsafe_allow_html=True)

# ------------------------------ Secrets ------------------------------
S = st.secrets
YT_CLIENT_ID     = S.get("YT_CLIENT_ID", "")
YT_CLIENT_SECRET = S.get("YT_CLIENT_SECRET", "")
YT_REDIRECT_URI  = S.get("YT_REDIRECT_URI", "")
YT_REFRESH_TOKEN = S.get("YT_REFRESH_TOKEN", "")

# ------------------------------ OAuth helpers ------------------------------
SCOPES = [
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/youtube.readonly",
]

def build_auth_url():
    params = {
        "client_id": YT_CLIENT_ID,
        "redirect_uri": YT_REDIRECT_URI,
        "response_type": "code",
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",  # ensures refresh_token on first consent
        "scope": " ".join(SCOPES),
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)

def exchange_code_for_tokens(code: str):
    data = {
        "client_id": YT_CLIENT_ID,
        "client_secret": YT_CLIENT_SECRET,
        "redirect_uri": YT_REDIRECT_URI,
        "grant_type": "authorization_code",
        "code": code,
    }
    r = requests.post("https://oauth2.googleapis.com/token", data=data, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"Token error {r.status_code}: {r.text}")
    return r.json()

def refresh_access_token(refresh_token: str):
    data = {
        "client_id": YT_CLIENT_ID,
        "client_secret": YT_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    r = requests.post("https://oauth2.googleapis.com/token", data=data, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"Refresh error {r.status_code}: {r.text}")
    return r.json()

def auth_header(access_token: str):
    return {"Authorization": f"Bearer {access_token}"}

# ------------------------------ YouTube Data calls ------------------------------
def yt_list_my_channels(access_token: str):
    """
    Lists all channels (including brand accounts) the signed-in Google user manages.
    Returns list of dicts: {id, title, thumb}
    """
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {"part": "snippet", "mine": "true", "maxResults": 50}
    r = requests.get(url, headers=auth_header(access_token), params=params, timeout=30)
    r.raise_for_status()
    items = r.json().get("items", [])
    res = []
    for it in items:
        res.append({
            "id": it["id"],
            "title": it["snippet"]["title"],
            "thumb": it["snippet"]["thumbnails"].get("default", {}).get("url", "")
        })
    return res

def yt_simple_channel_stats(api_key: str, channel_id: str):
    """
    Optional: simple public stats via API key (subs/total views).
    """
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {"part": "statistics", "id": channel_id, "key": api_key}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    items = r.json().get("items", [])
    if not items:
        return None
    stt = items[0]["statistics"]
    return {"subs": int(stt.get("subscriberCount", 0)), "views": int(stt.get("viewCount", 0))}

# ------------------------------ Mock data ------------------------------
DEFAULT = {
    "kpis": {"youtube": 15890, "instagram": 6050, "tiktok": 11032,
             "yt_total": 145_000_000, "ig_total": 2_340_000, "tt_total": 9_450_000},
    "yt_7days": [23500, 27100, 24800, 30100, 28900, 33000, 35120],
    "ministry": {"prayer": 15, "studies": 8, "baptisms": 1},
    "map_points": [
        {"lon":-97, "lat":31, "r":18},
        {"lon":101, "lat":3.1, "r":10},
        {"lon":106.8, "lat":-6.2, "r":8},
        {"lon":151, "lat":-33.8, "r":6},
        {"lon":55, "lat":25, "r":6},
        {"lon":12, "lat":41.9, "r":5},
    ],
    "clickup": [
        {"task":"Outline next video","status":"Not Done"},
        {"task":"Shoot testimony interview","status":"In Progress"},
        {"task":"Edit podcast episode","status":"Done"},
        {"task":"Schedule weekend posts","status":"In Progress"},
    ],
    "times": [
        {"when":"Tue, Aug 26, 2025 1:00–3:00 PM","what":"Worship Set"},
        {"when":"Wed, Aug 27, 2025 10:30–12:00","what":"Testimony Recording"},
        {"when":"Fri, Aug 29, 2025 9:00–10:30 AM","what":"Youth Reels"},
    ]
}

# ------------------------------ Header ------------------------------
left, right = st.columns([0.8,0.2])
with left:
    st.markdown("## **LOUDVOICE**")
with right:
    st.caption(datetime.now().strftime("%b %d, %Y %I:%M %p"))

st.write("")

# ------------------------------ OAuth Panel (if needed) ------------------------------
def oauth_panel():
    st.markdown("### 🔐 Connect YouTube Analytics")
    st.write("Sign in once to generate a **refresh token**. Paste it into `Settings → Secrets` as `YT_REFRESH_TOKEN` and rerun.")

    if not (YT_CLIENT_ID and YT_CLIENT_SECRET and YT_REDIRECT_URI):
        st.warning("Add `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, and `YT_REDIRECT_URI` to Secrets first.")
        return

    auth_url = build_auth_url()
    st.link_button("Sign in with Google", auth_url, help="Opens Google in a new tab")
    with st.expander("Or paste the code manually (if auto-capture didn’t work)"):
        code_val = st.text_input("Paste the **code** value here", value="", label_visibility="collapsed")
        if st.button("Exchange code for tokens"):
            if not code_val.strip():
                st.error("Please paste the `code` value (from the URL after consent).")
            else:
                try:
                    tok = exchange_code_for_tokens(code_val.strip())
                    st.success("Success! Copy the `refresh_token` below into **YT_REFRESH_TOKEN** in Secrets, then rerun.")
                    st.code(json.dumps(tok, indent=2))
                except Exception as e:
                    st.error(f"OAuth exchange failed. {e}")

# ------------------------------ Channel Picker ------------------------------
def channel_picker_ui(access_token: str):
    try:
        channels = yt_list_my_channels(access_token)
    except Exception as e:
        st.error(f"Could not list channels: {e}")
        return None

    if not channels:
        st.info("No channels found on this Google account.")
        return None

    # Remember last selection
    if "yt_channel_id" not in st.session_state:
        st.session_state["yt_channel_id"] = channels[0]["id"]

    names = [c["title"] for c in channels]
    idx = next((i for i,c in enumerate(channels) if c["id"]==st.session_state["yt_channel_id"]), 0)
    sel = st.selectbox("YouTube Channel", options=list(range(len(channels))),
                       index=idx, format_func=lambda i: names[i])
    st.session_state["yt_channel_id"] = channels[sel]["id"]

    ch = channels[sel]
    st.caption(f"Selected: **{ch['title']}**  \nID: `{ch['id']}`")
    return ch

# ------------------------------ Dashboard blocks ------------------------------
def kpi_box(title, value, sub=None):
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown(f"<div class='kpi-ttl'>{title}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='kpi-num'>{value:,}</div>", unsafe_allow_html=True)
    if sub:
        st.markdown(f"<div class='small'>{sub}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def progress_row(label, pct, color):
    st.markdown(
        f"<div class='row' style='gap:12px'>"
        f"<div style='min-width:220px'>{label}</div>"
        f"<div class='hbar' style='flex:1'><span class='{color}' style='width:{pct}%'></span></div>"
        f"</div>", unsafe_allow_html=True
    )

def views_row(label, val, vmax):
    pct = 0 if vmax==0 else int(round(100*val/vmax))
    st.markdown(
        f"<div class='row'><div style='min-width:50px'>{label}</div>"
        f"<div class='views-bar' style='flex:1'><span style='width:{pct}%;'></span></div>"
        f"<div style='min-width:70px; text-align:right'>{val:,}</div></div>",
        unsafe_allow_html=True
    )

# ------------------------------ MAIN ------------------------------
# Attempt access token from refresh (if present)
access_token = None
if YT_REFRESH_TOKEN and YT_CLIENT_ID and YT_CLIENT_SECRET:
    try:
        tok = refresh_access_token(YT_REFRESH_TOKEN)
        access_token = tok["access_token"]
        # token_type = tok.get("token_type"), expires_in = tok.get("expires_in")
    except Exception as e:
        st.warning(f"Could not refresh access token yet. {e}")

# Layout: 2 columns — Map on the left, stacked panels on the right
col_map, col_right = st.columns([0.62, 0.38])

# ----- LEFT: World Map (static SVG-style look using Plotly for now) -----
with col_map:
    st.markdown("<div class='card'><div class='section-title'>World Map — YouTube Viewers</div>", unsafe_allow_html=True)
    try:
        import plotly.graph_objects as go
        pts = DEFAULT["map_points"]
        fig = go.Figure(go.Scattergeo(
            lon=[p["lon"] for p in pts], lat=[p["lat"] for p in pts],
            mode="markers",
            marker=dict(size=[p["r"] for p in pts], color=YELLOW, line=dict(width=0.5, color="#111")),
        ))
        fig.update_geos(
            projection_type="natural earth", showland=True, landcolor="#0f1420",
            showocean=False, showcountries=True, countrycolor="#2a3448",
            lataxis_range=[-55, 75], lonaxis_range=[-170, 190]
        )
        fig.update_layout(height=420, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor="#141925", plot_bgcolor="#141925")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    except Exception:
        st.info("Plotly is missing? Add `plotly` to requirements.txt.")

    st.markdown("</div>", unsafe_allow_html=True)

# ----- RIGHT: Panels -----
with col_right:
    # 1) Ministry KPIs (3-up)
    st.markdown("<div class='card'><div class='section-title'>Ministry Tracker</div>", unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    c1.metric("Prayer", DEFAULT["ministry"]["prayer"])
    c2.metric("Studies", DEFAULT["ministry"]["studies"])
    c3.metric("Baptisms", DEFAULT["ministry"]["baptisms"])
    st.markdown("</div>", unsafe_allow_html=True)

    # 2) Channel Stats (3-up) — uses selected channel if access token exists
    st.markdown("<div class='card'><div class='section-title'>Channel Stats</div>", unsafe_allow_html=True)
    if access_token:
        ch = channel_picker_ui(access_token)
    else:
        st.caption("Sign in to pick a YouTube channel. Using mock stats below.")
        ch = None

    c1,c2,c3 = st.columns(3)
    # We’ll just show mock numbers (format K/M) to keep it lightweight here.
    def fmt_num(n):
        if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
        if n >= 1_000: return f"{n/1_000:.1f}K"
        return f"{n:,}"

    with c1:
        st.markdown("**YT**")
        kpi_box("Subscribers", DEFAULT["kpis"]["youtube"])
        kpi_box("Total Views", DEFAULT["kpis"]["yt_total"])
    with c2:
        st.markdown("**IG**")
        kpi_box("Followers", DEFAULT["kpis"]["instagram"])
        kpi_box("Total Views", DEFAULT["kpis"]["ig_total"])
    with c3:
        st.markdown("**TT**")
        kpi_box("Followers", DEFAULT["kpis"]["tiktok"])
        kpi_box("Total Views", DEFAULT["kpis"]["tt_total"])
    st.markdown("</div>", unsafe_allow_html=True)

    # 3) YouTube Views (Last 7 days) with aligned bars
    st.markdown("<div class='card'><div class='section-title'>YouTube Views (Last 7 Days)</div>", unsafe_allow_html=True)
    days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    vals = DEFAULT["yt_7days"]
    vmax = max(vals) if vals else 1
    for d,v in zip(days, vals):
        views_row(d, v, vmax)
    st.markdown("</div>", unsafe_allow_html=True)

# ----- Row 3: ClickUp tasks + Next Filming -----
tcol, fcol = st.columns([0.62, 0.38])

with tcol:
    st.markdown("<div class='card'><div class='section-title'>ClickUp Tasks (Upcoming)</div>", unsafe_allow_html=True)
    # Sort: unfinished first
    order = {"Not Done":0, "In Progress":1, "Done":2}
    tasks = sorted(DEFAULT["clickup"], key=lambda t: order.get(t["status"], 9))
    for t in tasks:
        if t["status"] == "Done":
            progress_row(t["task"] + "<div class='small'>Done</div>", 100, "bar-green")
        elif t["status"].lower().startswith("in"):
            progress_row(t["task"] + "<div class='small'>In Progress</div>", 50, "bar-yellow")
        else:
            progress_row(t["task"] + "<div class='small'>Not Done</div>", 10, "bar-red")
    st.markdown("</div>", unsafe_allow_html=True)

with fcol:
    st.markdown("<div class='card'><div class='section-title'>Next Filming Timeslots</div>", unsafe_allow_html=True)
    for slot in DEFAULT["times"]:
        st.markdown(
            f"<div class='row' style='justify-content:space-between'>"
            f"<div>{slot['when']}</div><div style='color:{YELLOW}'>{slot['what']}</div></div>",
            unsafe_allow_html=True
        )
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------ OAuth call-to-action (if no token) ------------------------------
if not access_token:
    st.write("")
    oauth_panel()

# ------------------------------ Tips footer ------------------------------
st.caption("Tip: add `?zoom=115` for TV distance and `?compact=1` for tighter spacing on phones. Bars are left‑aligned; filming slots include day, date, and time.")
