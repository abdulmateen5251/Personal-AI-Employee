"""
Gmail OAuth2 Setup Script
Generates token.json using OAuth2 user credentials.

Priority for credentials source:
  1. GMAIL_CREDENTIALS_JSON  (full JSON string in .env)
  2. GMAIL_CREDENTIALS_PATH  (path to credentials.json file)
  3. GMAIL_CLIENT_ID + GMAIL_CLIENT_SECRET  (inline in .env)
Token is saved to GMAIL_TOKEN_PATH (default: token.json)
"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv()

from src.core.config import get_env

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]


def main() -> None:
    from google_auth_oauthlib.flow import InstalledAppFlow

    # --- Resolve credentials source ---
    creds_json_str = get_env("GMAIL_CREDENTIALS_JSON", required=False, default="")
    creds_path     = get_env("GMAIL_CREDENTIALS_PATH", required=False, default="")
    client_id      = get_env("GMAIL_CLIENT_ID",        required=False, default="")
    client_secret  = get_env("GMAIL_CLIENT_SECRET",    required=False, default="")
    token_path     = get_env("GMAIL_TOKEN_PATH",        required=False, default="token.json") or "token.json"

    if creds_json_str:
        print("Using GMAIL_CREDENTIALS_JSON from .env")
        flow = InstalledAppFlow.from_client_config(json.loads(creds_json_str), SCOPES)

    elif creds_path and Path(creds_path).exists():
        print(f"Using credentials file: {creds_path}")
        flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)

    elif client_id and client_secret:
        print("Using GMAIL_CLIENT_ID + GMAIL_CLIENT_SECRET from .env")
        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
            }
        }
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)

    else:
        print("ERROR: No Gmail OAuth credentials found.")
        print("Add one of the following to .env:")
        print("  GMAIL_CREDENTIALS_JSON=<full JSON>")
        print("  GMAIL_CREDENTIALS_PATH=credentials.json")
        print("  GMAIL_CLIENT_ID=... + GMAIL_CLIENT_SECRET=...")
        sys.exit(1)

    print("\nOpening browser for Gmail login...")
    # Fixed port so redirect_uri is predictable — register http://localhost:8080 in Google Cloud Console
    creds = flow.run_local_server(port=8080)

    token_file = Path(token_path)
    token_file.write_text(creds.to_json())
    print(f"\n✅ Token saved to: {token_file.resolve()}")
    print(f"\nOptionally paste this into .env as GMAIL_TOKEN_JSON (single line):")
    print(creds.to_json())


if __name__ == "__main__":
    main()

