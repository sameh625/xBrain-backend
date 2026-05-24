"""
One-time setup script to obtain a Google OAuth refresh token for the xBrain backend.

Run this ONCE on your local machine. It will:
  1. Open a browser tab where you sign in with the meeting-host Gmail account
  2. Ask you to grant the app access to your Google Calendar
  3. Receive a refresh token from Google
  4. Print the four env-var values you need to add to Azure App Service

Prerequisites:
  - Python 3.8+
  - pip install google-auth-oauthlib
  - The OAuth client JSON file you downloaded from Google Cloud Console
    (rename it to "client_secret.json" and place it in the same folder as this script)

Usage:
  cd path/to/this/script
  python get_google_refresh_token.py

After it runs, copy the printed env vars and add them to Azure App Service Configuration.
"""

import json
import os
import sys
from pathlib import Path

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("ERROR: google-auth-oauthlib is not installed.")
    print()
    print("Install it with:")
    print("    pip install google-auth-oauthlib")
    print()
    sys.exit(1)

# Scope we need: ability to create and read calendar events on the user's primary calendar
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

# Path to the OAuth client JSON you downloaded from Google Cloud Console
SCRIPT_DIR = Path(__file__).resolve().parent
CLIENT_SECRET_FILE = SCRIPT_DIR / "client_secret.json"


def main():
    if not CLIENT_SECRET_FILE.exists():
        print(f"ERROR: {CLIENT_SECRET_FILE} not found.")
        print()
        print("Steps to fix:")
        print(f"  1. Find the JSON file you downloaded from Google Cloud Console")
        print(f"     (it has a name like 'client_secret_XXXXX-XXXXX.apps.googleusercontent.com.json')")
        print(f"  2. Rename it to 'client_secret.json'")
        print(f"  3. Place it at: {CLIENT_SECRET_FILE}")
        print(f"  4. Re-run this script")
        sys.exit(1)

    print("=" * 70)
    print("  xBrain — Google OAuth refresh token setup")
    print("=" * 70)
    print()
    print("A browser will open. Sign in with the Gmail account that will host")
    print("all the xBrain meetings (e.g., xbrain@gmail.com).")
    print()
    print("You may see a warning 'Google hasn't verified this app' — that's")
    print("normal for apps in Testing status. Click 'Advanced' → 'Go to xBrain (unsafe)'.")
    print()
    input("Press Enter to continue...")

    # Build the OAuth flow from the downloaded client secret
    flow = InstalledAppFlow.from_client_secrets_file(
        str(CLIENT_SECRET_FILE),
        scopes=SCOPES,
    )

    # Run the local-server flow. This opens a browser, listens on a local port
    # for Google's redirect, and exchanges the code for tokens.
    creds = flow.run_local_server(
        port=0,                                     # 0 = pick any free port
        access_type="offline",                      # required to get refresh_token
        prompt="consent",                           # forces refresh_token even on re-auth
        authorization_prompt_message=(
            "Your browser should open. If it doesn't, paste this URL:\n  {url}"
        ),
        success_message=(
            "Authorization complete. You can close this browser tab."
        ),
    )

    if not creds.refresh_token:
        print()
        print("ERROR: Google did not return a refresh token.")
        print("This usually happens if you've previously authorized this app.")
        print("Fix: Go to https://myaccount.google.com/permissions, find your")
        print("     xBrain app, click 'Remove access', then re-run this script.")
        sys.exit(1)

    # Load the client_id and client_secret from the JSON (we'll need them in env vars too)
    with open(CLIENT_SECRET_FILE) as f:
        client_config = json.load(f)
    client_data = client_config.get("installed") or client_config.get("web")
    client_id = client_data["client_id"]
    client_secret = client_data["client_secret"]

    print()
    print("=" * 70)
    print("  SUCCESS — refresh token obtained.")
    print("=" * 70)
    print()
    print("Add these FOUR environment variables to Azure App Service:")
    print("  (App Service → Configuration → Application settings → + New)")
    print()
    print("-" * 70)
    print(f"GOOGLE_CLIENT_ID       = {client_id}")
    print(f"GOOGLE_CLIENT_SECRET   = {client_secret}")
    print(f"GOOGLE_REFRESH_TOKEN   = {creds.refresh_token}")
    print(f"GOOGLE_CALENDAR_ID     = primary")
    print("-" * 70)
    print()
    print("Also add these to your LOCAL .env file (for local dev):")
    print()

    env_text = (
        f"GOOGLE_CLIENT_ID={client_id}\n"
        f"GOOGLE_CLIENT_SECRET={client_secret}\n"
        f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}\n"
        f"GOOGLE_CALENDAR_ID=primary\n"
    )
    out_file = SCRIPT_DIR / "google_credentials.env"
    out_file.write_text(env_text, encoding="utf-8")
    print(f"  Saved to: {out_file}")
    print()
    print("IMPORTANT: do NOT commit this file to git. It's a secret.")
    print("Add 'scripts/google_credentials.env' to your .gitignore if it isn't already.")
    print()


if __name__ == "__main__":
    main()
