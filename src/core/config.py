import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def get_vault_path() -> Path:
    raw = os.getenv("VAULT_PATH")
    if not raw:
        raise RuntimeError("VAULT_PATH is not configured")
    return Path(raw)


def get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_env(name: str, required: bool = True, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value or ""


DRY_RUN = get_bool("DRY_RUN", True)
