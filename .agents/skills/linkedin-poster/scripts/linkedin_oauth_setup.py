"""LinkedIn OAuth2 Setup — 3-legged flow for w_member_social scope."""

from __future__ import annotations

import http.server
import json
import threading
import urllib.parse
import webbrowser
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.config import get_env

REDIRECT_PORT = 8585
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"
SCOPES = "w_member_social"

# Will be set by the callback handler
_auth_code: str | None = None
_server_ready = threading.Event()


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    """Handle the OAuth2 redirect callback."""

    def do_GET(self):
        global _auth_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            _auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<h1>LinkedIn Authorization Successful!</h1>"
                b"<p>You can close this window and return to the terminal.</p>"
            )
        else:
            error = params.get("error", ["unknown"])[0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(f"<h1>Error: {error}</h1>".encode())

        # Signal the main thread
        _server_ready.set()

    def log_message(self, format, *args):
        pass  # Suppress HTTP logs


def _exchange_code_for_token(code: str, client_id: str, client_secret: str) -> dict:
    """Exchange authorization code for an access token."""
    import requests

    resp = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": REDIRECT_URI,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _get_profile_urn(access_token: str) -> str:
    """Fetch the authenticated user's LinkedIn person URN."""
    import requests

    resp = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    sub = data.get("sub", "")
    return f"urn:li:person:{sub}"


def main() -> None:
    client_id = get_env("LINKEDIN_CLIENT_ID")
    client_secret = get_env("LINKEDIN_CLIENT_SECRET")
    token_path = get_env("LINKEDIN_TOKEN_PATH")

    # Build authorization URL
    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization?"
        + urllib.parse.urlencode({
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
            "state": "personal-ai-employee",
        })
    )

    # Start local server to catch callback
    server = http.server.HTTPServer(("localhost", REDIRECT_PORT), _CallbackHandler)
    server_thread = threading.Thread(target=server.handle_request, daemon=True)
    server_thread.start()

    print("Opening browser for LinkedIn authorization...")
    print(f"If the browser doesn't open, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    # Wait for callback
    _server_ready.wait(timeout=120)
    server.server_close()

    if not _auth_code:
        print("ERROR: No authorization code received. Aborting.")
        sys.exit(1)

    print("Exchanging code for access token...")
    token_data = _exchange_code_for_token(_auth_code, client_id, client_secret)
    access_token = token_data["access_token"]

    # Fetch the user's person URN
    print("Fetching your LinkedIn profile URN...")
    person_urn = _get_profile_urn(access_token)
    token_data["person_urn"] = person_urn

    Path(token_path).write_text(json.dumps(token_data, indent=2))
    print(f"\nSaved LinkedIn token to {token_path}")
    print(f"Person URN: {person_urn}")
    print(f"Token expires in: {token_data.get('expires_in', 'unknown')} seconds")
    print("\nAdd this to your .env:")
    print(f"  LINKEDIN_PERSON_URN={person_urn}")


if __name__ == "__main__":
    main()
