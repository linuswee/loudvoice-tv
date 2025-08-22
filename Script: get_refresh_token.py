import os
from google_auth_oauthlib.flow import InstalledAppFlow

# Make sure you pip install:
#   pip install google-auth google-auth-oauthlib google-auth-httplib2

# The scopes your app needs
SCOPES = ["https://www.googleapis.com/auth/yt-analytics.readonly"]

def main():
    # Load OAuth client secrets from environment variables or hardcode here
    client_config = {
        "installed": {
            "client_id": os.environ.get("YT_CLIENT_ID", "YOUR_CLIENT_ID"),
            "client_secret": os.environ.get("YT_CLIENT_SECRET", "YOUR_CLIENT_SECRET"),
            "redirect_uris": ["http://localhost"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    }

    # Run local server flow
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0)

    print("\n✅ Success! Here is your new refresh token:\n")
    print(creds.refresh_token)

if __name__ == "__main__":
    main()
