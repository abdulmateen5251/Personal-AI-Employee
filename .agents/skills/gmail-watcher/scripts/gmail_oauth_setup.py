from pathlib import Path
import importlib
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
    creds_path = get_env("GMAIL_CREDENTIALS_PATH")
    token_path = get_env("GMAIL_TOKEN_PATH")

    flow_module = importlib.import_module("google_auth_oauthlib.flow")
    installed_app_flow = getattr(flow_module, "InstalledAppFlow")

    flow = installed_app_flow.from_client_secrets_file(creds_path, SCOPES)
    creds = flow.run_local_server(port=0)
    Path(token_path).write_text(creds.to_json())
    print(f"Saved Gmail token to {token_path}")


if __name__ == "__main__":
    main()
