from __future__ import annotations

import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build

from src.core.config import get_env


DEFAULT_GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]


def _get_service_account_credentials(scopes: list[str]) -> ServiceAccountCredentials | None:
    # Support both naming conventions in .env
    service_account_json = (
        get_env("GOOGLE_SERVICE_ACCOUNT_INFO", required=False, default="")
        or get_env("GMAIL_SERVICE_ACCOUNT_JSON", required=False, default="")
    )
    service_account_path = (
        get_env("GOOGLE_SERVICE_ACCOUNT_FILE", required=False, default="")
        or get_env("GMAIL_SERVICE_ACCOUNT_PATH", required=False, default="")
    )
    delegated_user = (
        get_env("GMAIL_DELEGATE_EMAIL", required=False, default="")
        or get_env("GMAIL_SENDER", required=False, default="")
        or get_env("GMAIL_DELEGATED_USER", required=False, default="")
    )

    if not service_account_json and not service_account_path:
        return None

    if service_account_json:
        creds = ServiceAccountCredentials.from_service_account_info(
            json.loads(service_account_json), scopes=scopes
        )
    else:
        creds = ServiceAccountCredentials.from_service_account_file(
            service_account_path, scopes=scopes
        )

    if delegated_user:
        creds = creds.with_subject(delegated_user)

    return creds


def _get_oauth_user_credentials(scopes: list[str]) -> Credentials | None:
    """
    OAuth2 user credentials with automatic token refresh.
    Priority:
      1. GMAIL_TOKEN_JSON   (inline JSON in .env)
      2. GMAIL_TOKEN_PATH   (path to token file, default: token.json)
    Refreshes automatically when expired using GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET.
    """
    token_json_str = get_env("GMAIL_TOKEN_JSON", required=False, default="")
    token_path_str = get_env("GMAIL_TOKEN_PATH", required=False, default="token.json")
    token_path = Path(token_path_str) if token_path_str else Path("token.json")

    creds: Credentials | None = None

    if token_json_str:
        creds = Credentials.from_authorized_user_info(json.loads(token_json_str), scopes)
    elif token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)

    if creds is None:
        return None

    # Auto-refresh if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Persist refreshed token back to file
        if token_path:
            token_path.write_text(creds.to_json())

    return creds


def _run_oauth_flow(scopes: list[str]) -> Credentials:
    """Run interactive OAuth flow using credentials from .env or credentials.json."""
    from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore

    creds_json_str = get_env("GMAIL_CREDENTIALS_JSON", required=False, default="")
    creds_path = get_env("GMAIL_CREDENTIALS_PATH", required=False, default="credentials.json")

    if creds_json_str:
        flow = InstalledAppFlow.from_client_config(json.loads(creds_json_str), scopes)
    elif creds_path and Path(creds_path).exists():
        flow = InstalledAppFlow.from_client_secrets_file(creds_path, scopes)
    else:
        raise RuntimeError(
            "No OAuth credentials found. Provide GMAIL_CREDENTIALS_JSON or "
            "GMAIL_CREDENTIALS_PATH (credentials.json) in .env, then run:\n"
            "  python .agents/skills/gmail-watcher/scripts/gmail_oauth_setup.py"
        )

    # Fixed port — register http://localhost:8080 in Google Cloud Console
    creds = flow.run_local_server(port=8080)

    token_path_str = get_env("GMAIL_TOKEN_PATH", required=False, default="token.json")
    token_path = Path(token_path_str or "token.json")
    token_path.write_text(creds.to_json())
    print(f"✅ OAuth token saved to {token_path}")
    return creds


def get_gmail_user_id() -> str:
    user_id = get_env("GMAIL_USER_ID", required=False, default="")
    if user_id:
        return user_id

    # For OAuth user auth, 'me' is always correct
    token_json_str = get_env("GMAIL_TOKEN_JSON", required=False, default="")
    token_path = Path(get_env("GMAIL_TOKEN_PATH", required=False, default="token.json") or "token.json")
    if token_json_str or token_path.exists():
        return "me"

    # Service account needs explicit delegation target
    delegated_user = (
        get_env("GMAIL_DELEGATE_EMAIL", required=False, default="")
        or get_env("GMAIL_SENDER", required=False, default="")
        or get_env("GMAIL_DELEGATED_USER", required=False, default="")
    )
    if delegated_user:
        return delegated_user

    return "me"


def build_gmail_service(scopes: list[str] | None = None, interactive: bool = False):
    """
    Build Gmail API service.
    Auth priority:
      1. OAuth user token  (GMAIL_TOKEN_JSON / GMAIL_TOKEN_PATH / token.json)
      2. Service account   (GOOGLE_SERVICE_ACCOUNT_INFO / GOOGLE_SERVICE_ACCOUNT_FILE)
      3. Interactive OAuth flow (only if interactive=True)
    """
    effective_scopes = scopes or DEFAULT_GMAIL_SCOPES

    # 1. OAuth user credentials (preferred — works with personal Gmail)
    creds = _get_oauth_user_credentials(effective_scopes)

    # 2. Service account fallback
    if creds is None:
        creds = _get_service_account_credentials(effective_scopes)

    # 3. Interactive OAuth flow (setup mode only)
    if creds is None:
        if interactive:
            creds = _run_oauth_flow(effective_scopes)
        else:
            raise RuntimeError(
                "No Gmail credentials found.\n"
                "Run the OAuth setup first:\n"
                "  python .agents/skills/gmail-watcher/scripts/gmail_oauth_setup.py"
            )

    service = build("gmail", "v1", credentials=creds)
    return service, get_gmail_user_id()