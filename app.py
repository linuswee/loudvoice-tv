# app.py
import os, json, time, base64, hashlib, requests, secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
import streamlit as st

# ──────────────────────────────────────────────────────────────────────────────
# Page / theme
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="LoudVoice Dashboard", page_icon="🎛️", layout="wide")

YELLOW = "#ffd54a"
TEXT   = "#e8ecff"
MUTED  = "#8b93b5"
BG     = "#0b0e14"
CARD   = "#121725"
BORDER = "#23283b"

st.markdown(f"""
<style>
header[data-testid="stHeader"]{{display:none;}}
#MainMenu, footer {{visibility:hidden;}}
html, body, [class^="css"] {{ background:{BG}; color:{TEXT}!important; }}
.block-container {{ max-width: 1800px; padding-top: 10px; }}
.card{{background:{CARD};border:1px solid {BORDER};border-radius:16px;padding:18px 18px 14px 18px;box-shadow:0 8px 24px rgba(0,0,0,.35);}}
.h1{{font-weight:900; letter-spacing:2px; color:{YELLOW}; font-size:34px; margin:0 0 6px 0;}}
.h2{{font-weight:800; color:{YELLOW}; font-size:18px; margin:0 0 12px 0;}}
.lbl{{font-weight:700; letter-spacing:.3px; font-size:12px; color:{MUTED};}}
.small{{color:{MUTED};font-size:12px;}}
.hbar{{height:10px;border-radius:6px;background:#212638;overflow:hidden}}
.hbar>span{{display:block;height:100%}}
.row{{display:flex;gap:12px;align-items:center;justify-content:space-between;padding:6px 0;border-bottom:1px dashed #27304a}}
.row:last-child{{border-bottom:none}}
.grid3{{display:grid;grid-template-columns:1fr 1fr 1fr; gap:10px}}
.kpi .big{{font-size:36px;font-weight:900;margin:0}}
/* Mobile tweaks */
@media (max-width:900px){{
  .h1{{font-size:26px}}
  .grid3{{grid-template-columns:1fr; gap:8px}}
  .card{{padding:14px}}
}}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="h1">LOUDVOICE</div>', unsafe_allow_html=True)
st.caption(datetime.now().strftime("%b %d, %Y %I:%M %p"))

# ──────────────────────────────────────────────────────────────────────────────
# Secrets / config
# ──────────────────────────────────────────────────────────────────────────────
YOUTUBE_API_KEY    = st.secrets.get("YOUTUBE_API_KEY", "")
YOUTUBE_CHANNEL_ID = st.secrets.get("YOUTUBE_CHANNEL_ID", "")

# Google OAuth (Web client)
YT_CLIENT_ID     = st.secrets.get("YT_CLIENT_ID", "")
YT_CLIENT_SECRET = st.secrets.get("YT_CLIENT_SECRET", "")
YT_REDIRECT_URI  = st.secrets.get("YT_REDIRECT_URI", "")   # e.g. https://yourapp.streamlit.app/
YT_REFRESH_TOKEN = st.secrets.get("YT_REFRESH_TOKEN", "")  # fill after first sign-in

AUTH_URI  = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPES = [
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/youtube.readonly",
]

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def compact(n: int) -> str:
    try: n = float(n)
    except: return str(n)
    for div, suf in [(1_000_000_000,'B'),(1_000_000,'M'),(1_000,'K')]:
        if n >= div:
            v = n/div
            return f"{v:.1f}{suf}".replace(".0","")
    return f"{int(n):,}"

def pkce_pair():
    verifier = base64.urlsafe_b64encode(os.urandom(40)).rstrip(b'=').decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b'=').decode()
    return verifier, challenge

def auth_url(code_challenge: str) -> str:
    q = {
        "client_id": YT_CLIENT_ID,
        "redirect_uri": YT_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{AUTH_URI}?{urlencode(q)}"

def token_exchange(data: dict) -> dict:
    r = requests.post(TOKEN_URI, data=data, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"Token error {r.status_code}: {r.text}")
    return r.json()

def refresh_access_token(refresh_token: str) -> dict:
    return token_exchange({
        "client_id": YT_CLIENT_ID,
        "client_secret": YT_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    })

def youtube_public_kpis():
    if not (YOUTUBE_API_KEY and YOUTUBE_CHANNEL_ID):
        return {"subs": 15890, "total": 145_000_000}  # mock
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {"part": "statistics", "id": YOUTUBE_CHANNEL_ID, "key": YOUTUBE_API_KEY}
    r = requests.get(url, params=params, timeout=30).json()
    try:
        s = r["items"][0]["statistics"]
        return {"subs": int(s["subscriberCount"]), "total": int(s["viewCount"])}
    except:
        return {"subs": 15890, "total": 145_000_000}

def yt_last7(access_token: str | None):
    if not access_token:
        return [23500,27100,24800,30100,28900,33000,35120]
    cid = requests.get(
        "https://www.googleapis.com/youtube/v3/channels?part=id&mine=true",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    ).json()["items"][0]["id"]
    today = datetime.now(timezone.utc).date()
    start = (today - timedelta(days=6)).isoformat()
    body = {
        "ids": f"channel=={cid}",
        "startDate": start, "endDate": today.isoformat(),
        "metrics": "views", "dimensions": "day", "sort": "day"
    }
    r = requests.post(
        "https://youtubeanalytics.googleapis.com/v2/reports",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type":"application/json"},
        data=json.dumps(body), timeout=30
    ).json()
    return [int(row[1]) for row in r.get("rows", [])] or [23500,27100,24800,30100,28900,33000,35120]

# ──────────────────────────────────────────────────────────────────────────────
# NEW: Mobile‑friendly OAuth setup UI (PKCE, auto/paste code support)
# ──────────────────────────────────────────────────────────────────────────────
def mobile_oauth_setup_ui():
    st.markdown("### 🔐 Connect YouTube Analytics")
    if not (YT_CLIENT_ID and YT_CLIENT_SECRET and YT_REDIRECT_URI):
        st.error("Add **YT_CLIENT_ID**, **YT_CLIENT_SECRET**, and **YT_REDIRECT_URI** in *Settings → Secrets*.")
        st.info("Redirect URI should be your Streamlit app URL, e.g. `https://yourapp.streamlit.app/` and must be added in Google Cloud → OAuth Client as an **Authorized redirect URI**.")
        return None

    # Keep a PKCE pair while user navigates away to Google and back
    if "pkce" not in st.session_state:
        st.session_state.pkce = pkce_pair()
    verifier, challenge = st.session_state.pkce

    signin = auth_url(challenge)
    st.link_button("Sign in with Google", signin)

    # If Google sent you back with ?code=... capture it automatically
    qs = st.query_params
    code_from_url = qs.get("code", [None])[0] if isinstance(qs.get("code", None), list) else qs.get("code", None)

    with st.expander("Or paste the code manually (if auto-capture didn't work)", expanded=not bool(code_from_url)):
        manual_code = st.text_input("Paste the `code` value here", value=code_from_url or "")
        do_exchange = st.button("Exchange code for tokens")
    if code_from_url and not st.session_state.get("did_auto_exchange"):
        manual_code = code_from_url
        do_exchange = True

    if not (do_exchange and manual_code):
        return None

    try:
        tokens = token_exchange({
            "client_id": YT_CLIENT_ID,
            "client_secret": YT_CLIENT_SECRET,
            "redirect_uri": YT_REDIRECT_URI,
            "grant_type": "authorization_code",
            "code": manual_code.strip(),
            "code_verifier": verifier,
        })
        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            st.error("No refresh_token returned. Make sure the consent screen appeared and you selected your channel.")
            return None
        st.session_state.did_auto_exchange = True
        st.success("✅ Got your refresh token! Copy it into *Settings → Secrets* as **YT_REFRESH_TOKEN**, then rerun.")
        st.code(refresh_token, language="bash")
        return None
    except Exception as e:
        st.error(f"OAuth exchange failed. {e}")
        return None

# ──────────────────────────────────────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────────────────────────────────────
def bar_row(day, value, maxv):
    pct = 0 if maxv==0 else int(100*value/maxv)
    return f"""
    <div class='row' style='gap:14px'>
      <div style='min-width:42px'>{day}</div>
      <div class='hbar' style='flex:1'><span style='width:{pct}%; background:#4aa3ff'></span></div>
      <div style='min-width:90px; text-align:right'>{value:,}</div>
    </div>
    """

def render_dashboard(access_token: str | None):
    left, right = st.columns([0.62, 0.38], gap="small")

    with left:
        st.markdown('<div class="card"><div class="h2">World Map — YouTube Viewers</div>', unsafe_allow_html=True)
        # Placeholder world map image (swap later with real)
        st.image("https://raw.githubusercontent.com/napthedev/public-assets/main/simple_dark_world.png", use_column_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        # Row 1: Ministry KPIs
        st.markdown('<div class="grid3">', unsafe_allow_html=True)
        for k, v in [("Prayer", 15), ("Studies", 8), ("Baptisms", 1)]:
            st.markdown(f"""
            <div class="card" style="text-align:center">
              <div class="lbl">{k}</div>
              <div class="kpi"><p class="big">{v}</p></div>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Row 2: Social stats (YT/IG/TT)
        yt = youtube_public_kpis()
        socials = [
            ("YT",       ("Subscribers", compact(yt["subs"])), ("Total Views", compact(yt["total"]))),
            ("IG",       ("Followers",   "6,050"),             ("Total Views",  "2.34M")),
            ("TT",       ("Followers",   "11,032"),            ("Total Views",  "9.45M")),
        ]
        st.markdown('<div class="grid3" style="margin-top:10px">', unsafe_allow_html=True)
        for label, a, b in socials:
            st.markdown(f"""
            <div class="card">
              <div class="h2">{label}</div>
              <div class="lbl">{a[0]}</div>
              <div class="kpi"><p class="big">{a[1]}</p></div>
              <div class="lbl" style="margin-top:8px">{b[0]}</div>
              <div class="kpi"><p class="big">{b[1]}</p></div>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Row 3: Last 7 days views (bars aligned)
        daily = yt_last7(access_token)
        days  = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
        m     = max(daily) if daily else 1
        st.markdown('<div class="card" style="margin-top:10px"><div class="h2">YouTube Views (Last 7 Days)</div>', unsafe_allow_html=True)
        st.markdown("".join(bar_row(d, v, m) for d, v in zip(days, daily)), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────
if not YT_REFRESH_TOKEN:
    # No refresh token yet → show mobile OAuth setup
    mobile_oauth_setup_ui()
else:
    # Use refresh token silently
    try:
        token = refresh_access_token(YT_REFRESH_TOKEN)
        access_token = token.get("access_token")
    except Exception as e:
        st.error(f"Could not refresh token: {e}")
        access_token = None
    render_dashboard(access_token)
