import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


class ZoneViolationError(RuntimeError):
    pass


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


def get_agent_zone() -> str:
    zone = os.getenv("AGENT_ZONE", "local").strip().lower()
    if zone not in {"local", "cloud"}:
        raise RuntimeError("AGENT_ZONE must be either 'local' or 'cloud'")
    return zone


def is_local() -> bool:
    return get_agent_zone() == "local"


def is_cloud() -> bool:
    return get_agent_zone() == "cloud"


def require_local_execution(action_name: str) -> None:
    if not is_local():
        raise ZoneViolationError(
            f"Action '{action_name}' is restricted to local zone (AGENT_ZONE=local)"
        )


DRY_RUN = get_bool("DRY_RUN", True)
