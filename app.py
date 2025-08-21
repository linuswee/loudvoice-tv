from google_auth_oauthlib.flow import Flow
import streamlit as st
import urllib.parse

SCOPES = ["https://www.googleapis.com/auth/yt-analytics.readonly"]

def mobile_oauth_setup_ui():
    """Guides through Google sign-in and mints a refresh token (iOS-friendly)."""
    # If we already have a refresh token, do nothing
    if st.secrets.get("YT_REFRESH_TOKEN"):
        return

    client_id = st.secrets.get("YT_CLIENT_ID")
    client_secret = st.secrets.get("YT_CLIENT_SECRET")
    redirect_uri = st.secrets.get("YT_REDIRECT_URI")  # e.g. https://loudvoice-tv.streamlit.app/

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

    qp = st.query_params  # Mapping[str, List[str]]
    code = qp.get("code", [None])[0]
    state = qp.get("state", [None])[0]

    # First leg: build the consent URL and save `state`
    if not code:
        auth_url, state_generated = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent select_account",  # force account chooser + refresh token
        )
        st.session_state["oauth_state"] = state_generated
        st.link_button("🔐 Sign in with Google (YouTube Analytics)", auth_url, type="primary")
        st.info(
            "If Google shows a redirect error, ensure this exact URI is in your OAuth client's "
            "**Authorized redirect URIs**:  \n\n`" + redirect_uri + "`"
        )
        st.stop()

    # Second leg: we’re back from Google. Validate state and exchange using FULL URL.
    expected_state = st.session_state.get("oauth_state")
    if expected_state and state and expected_state != state:
        st.error("State mismatch. Please try signing in again.")
        st.stop()

    # Rebuild the full authorization_response URL exactly as Google sent it:
    # https://YOUR-REDIRECT-URI/?code=...&state=...
    # (We re-encode the current query params to avoid iOS/Safari '+' / space issues)
    qs = urllib.parse.urlencode(
        {k: v if isinstance(v, list) else [v] for k, v in qp.items()},
        doseq=True,
        safe=":/?=&"  # keep these as-is
    )
    authorization_response = redirect_uri.rstrip("/") + "/?" + qs

    try:
        flow.fetch_token(authorization_response=authorization_response)
        creds = flow.credentials
        refresh = getattr(creds, "refresh_token", None)

        # Clear params so the code can’t be re-used by accident
        st.experimental_set_query_params()

        if refresh:
            st.success("Copy this refresh token → paste into **Secrets → `YT_REFRESH_TOKEN`** and rerun the app.")
            st.code(refresh)
            st.info("Done! You can now remove/hide this setup block.")
        else:
            st.error("No refresh token returned. Tap sign-in again (we forced consent & account chooser).")
    except Exception as e:
        st.error(
            "OAuth exchange failed. Most common causes:\n"
            "• The `code` was already used (pressing back/refresh). Click the sign-in link again.\n"
            "• Redirect URI mismatch (must match **exactly**, including trailing slash).\n"
            "• Content blocker modified the URL.\n\n"
            f"Details: {e}"
        )
    st.stop()
