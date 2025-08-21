import streamlit as st
from google_auth_oauthlib.flow import Flow

st.set_page_config(page_title="Dashboard", layout="wide")

# --- iOS-friendly OAuth to mint a YouTube refresh token ---
SCOPES = ["https://www.googleapis.com/auth/yt-analytics.readonly"]

def mobile_oauth_setup_ui():
    if st.secrets.get("YT_REFRESH_TOKEN"):
        return

    client_id = st.secrets.get("YT_CLIENT_ID")
    client_secret = st.secrets.get("YT_CLIENT_SECRET")
    redirect_uri = st.secrets.get("YT_REDIRECT_URI")

    st.title("🔐 Connect YouTube Analytics")
    st.write("Sign in once to generate a **refresh token**. Paste it into Secrets → `YT_REFRESH_TOKEN` and rerun.")

    if not (client_id and client_secret and redirect_uri):
        st.warning("Add `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, and **`YT_REDIRECT_URI`** in Settings → Secrets.")
        st.stop()

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri],
            }
        },
        scopes=SCOPES,
    )
    flow.redirect_uri = redirect_uri

    code = st.query_params.get("code", [None])[0]
    if not code:
        auth_url, _state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent select_account",
        )
        st.link_button("🔐 Sign in with Google (YouTube Analytics)", auth_url, type="primary")
        st.info(
            "If Google shows redirect errors: make sure this exact URL is added as an **Authorized redirect URI** "
            "in your OAuth client: **" + redirect_uri + "**"
        )
        st.stop()

    try:
        flow.fetch_token(code=code)
        creds = flow.credentials
        refresh = getattr(creds, "refresh_token", None)

        st.experimental_set_query_params()

        if refresh:
            st.success("Copy this refresh token → paste into **Secrets → `YT_REFRESH_TOKEN`** and rerun the app.")
            st.code(refresh)
            st.info("You can now remove/hide this setup block.")
        else:
            st.error("No refresh token returned. Tap sign-in again (we forced consent & account chooser).")
    except Exception as e:
        st.error(
            "OAuth exchange failed. Check redirect URI matches."
            f"Error: {e}"
        )
    st.stop()

# If no refresh token, run setup UI
if not st.secrets.get("YT_REFRESH_TOKEN"):
    mobile_oauth_setup_ui()

# --- Your dashboard code goes here ---
st.title("📊 LoudVoice Dashboard")
st.write("Now integrated with YouTube OAuth flow (refresh token).")
