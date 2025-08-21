import streamlit as st
import requests
import json

# --- Mobile OAuth Helper ---
def mobile_oauth_setup_ui():
    st.title("🔑 Connect Google Account")
    st.write("Sign in to allow YouTube data access. After login, paste your refresh token into Streamlit Secrets.")
    # Normally you'd use something like streamlit-oauth or a custom flow
    auth_url = (
        "https://accounts.google.com/o/oauth2/auth"
        "?client_id={}&redirect_uri=http://localhost&scope=https://www.googleapis.com/auth/yt.analytics.readonly"
        "&response_type=code&access_type=offline&prompt=consent"
    ).format(st.secrets.get("YT_CLIENT_ID", ""))
    st.markdown(f"[👉 Sign in with Google]({auth_url})")

def main():
    # If no refresh token stored, prompt sign in
    if not st.secrets.get("YT_REFRESH_TOKEN"):
        mobile_oauth_setup_ui()
        return

    st.title("📊 LoudVoice Ministry Dashboard")
    st.write("Dashboard placeholder — world map, ministry tracker, socials, etc. will render here.")

if __name__ == "__main__":
    main()
