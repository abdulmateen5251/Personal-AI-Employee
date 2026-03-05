from __future__ import annotations

import json

from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build

from src.core.config import get_env


DEFAULT_GMAIL_SCOPES = [
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


def _get_oauth_user_credentials() -> Credentials:
    token_json = get_env("GMAIL_TOKEN_JSON", required=False, default="")
    if token_json:
        return Credentials.from_authorized_user_info(json.loads(token_json))

    token_path = get_env("GMAIL_TOKEN_PATH")
    return Credentials.from_authorized_user_file(token_path)


def get_gmail_user_id() -> str:
    user_id = get_env("GMAIL_USER_ID", required=False, default="")
    delegated_user = (
        get_env("GMAIL_DELEGATE_EMAIL", required=False, default="")
        or get_env("GMAIL_SENDER", required=False, default="")
        or get_env("GMAIL_DELEGATED_USER", required=False, default="")
    )
    service_account_json = (
        get_env("GOOGLE_SERVICE_ACCOUNT_INFO", required=False, default="")
        or get_env("GMAIL_SERVICE_ACCOUNT_JSON", required=False, default="")
    )
    service_account_path = (
        get_env("GOOGLE_SERVICE_ACCOUNT_FILE", required=False, default="")
        or get_env("GMAIL_SERVICE_ACCOUNT_PATH", required=False, default="")
    )

    if user_id:
        return user_id

    if delegated_user:
        return delegated_user

    if service_account_json or service_account_path:
        raise RuntimeError(
            "Service-account Gmail auth requires GMAIL_DELEGATE_EMAIL, GMAIL_SENDER, or GMAIL_USER_ID."
        )

    return "me"


def build_gmail_service(scopes: list[str] | None = None):
    effective_scopes = scopes or DEFAULT_GMAIL_SCOPES
    creds = _get_service_account_credentials(effective_scopes) or _get_oauth_user_credentials()
    service = build("gmail", "v1", credentials=creds)
    return service, get_gmail_user_id()