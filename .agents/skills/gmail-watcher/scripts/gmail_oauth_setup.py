from pathlib import Path
import importlib
import json
import sys

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.config import get_env


SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]


def main() -> None:
    creds_json = get_env("GMAIL_CREDENTIALS_JSON", required=False, default="")
    creds_path = get_env("GMAIL_CREDENTIALS_PATH", required=False, default="")
    token_path = get_env("GMAIL_TOKEN_PATH", required=False, default="")

    flow_module = importlib.import_module("google_auth_oauthlib.flow")
    installed_app_flow = getattr(flow_module, "InstalledAppFlow")

    if creds_json:
        flow = installed_app_flow.from_client_config(json.loads(creds_json), SCOPES)
    else:
        if not creds_path:
            raise RuntimeError("Set either GMAIL_CREDENTIALS_JSON or GMAIL_CREDENTIALS_PATH")
        flow = installed_app_flow.from_client_secrets_file(creds_path, SCOPES)

    creds = flow.run_local_server(port=0)
    token_json = creds.to_json()

    if token_path:
        Path(token_path).write_text(token_json)
        print(f"Saved Gmail token to {token_path}")
    else:
        print("No GMAIL_TOKEN_PATH set. Paste this into .env as GMAIL_TOKEN_JSON:")
        print(token_json)


if __name__ == "__main__":
    main()
