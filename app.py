import urllib.parse
from google_auth_oauthlib.flow import Flow
import streamlit as st

SCOPES = ["https://www.googleapis.com/auth/yt-analytics.readonly"]

def mobile_oauth_setup_ui():
    """
    iOS‑friendly OAuth that mints a refresh token for YouTube Analytics.
    Shows UI at every step; never leaves a blank screen.
    """
    if st.secrets.get("YT_REFRESH_TOKEN"):
        return  # already connected

    client_id = st.secrets.get("YT_CLIENT_ID")
    client_secret = st.secrets.get("YT_CLIENT_SECRET")
    redirect_uri = st.secrets.get("YT_REDIRECT_URI")  # e.g. https://loudvoice-tv.streamlit.app/

    st.title("🔐 Connect YouTube Analytics")
    st.write(
        "Sign in once to generate a **refresh token**. Paste it into Settings → Secrets as "
        "`YT_REFRESH_TOKEN` and rerun."
    )

    if not (client_id and client_secret and redirect_uri):
        st.warning("Add `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, and **`YT_REDIRECT_URI`** in Settings → Secrets.")
        return

    # Build flow
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

    # Read query params robustly
    qp = st.experimental_get_query_params()
    code = (qp.get("code") or [None])[0]
    state = (qp.get("state") or [None])[0]

    # Helper to reset the URL (clears ?code & ?state)
    def _reset_url():
        st.experimental_set_query_params()

    # First leg — no code yet: show the Sign‑in link
    if not code:
        auth_url, state_generated = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent select_account",  # force refresh token & account picker
        )
        st.session_state["oauth_state"] = state_generated
        st.link_button("🔐 Sign in with Google (YouTube Analytics)", auth_url, type="primary")
        st.caption(
            "If Google shows a redirect error, ensure this exact URI is in your OAuth client's "
            "**Authorized redirect URIs**:  `" + redirect_uri + "`"
        )
        if st.button("Reset / Try again"):
            _reset_url()
        return

    # Back from Google — validate state
    expected_state = st.session_state.get("oauth_state")
    if expected_state and state and expected_state != state:
        st.error("State mismatch. Tap **Reset** and sign in again.")
        if st.button("Reset"):
            _reset_url()
        return

    # Rebuild the full authorization_response URL exactly as received
    qs = urllib.parse.urlencode(qp, doseq=True, safe=":/?=&")
    authorization_response = redirect_uri.rstrip("/") + "/?" + qs

    # Exchange the code
    try:
        flow.fetch_token(authorization_response=authorization_response)
        creds = flow.credentials
        refresh = getattr(creds, "refresh_token", None)

        _reset_url()  # clear params so the code can't be reused

        if refresh:
            st.success("✅ Refresh token minted! Copy this into **Secrets → `YT_REFRESH_TOKEN`**:")
            st.code(refresh)
            st.info("After saving, rerun the app. This setup block will disappear.")
        else:
            st.error("No refresh token returned. Click **Reset** and sign in again.")
            if st.button("Reset"):
                _reset_url()
    except Exception as e:
        st.error(
            "OAuth exchange failed.\n\n"
            "Common causes:\n"
            "• Redirect URI mismatch (must match exactly, trailing slash matters).\n"
            "• The code was already used (back/refresh). Click **Reset** and sign in again.\n"
            "• Content blocker modified the URL.\n\n"
            f"Details: {e}"
        )
        if st.button("Reset / Try again"):
            _reset_url()
