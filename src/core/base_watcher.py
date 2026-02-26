import json
import logging
import os
import time
from abc import ABC, abstractmethod
from pathlib import Path

from src.core.config import get_vault_path


class BaseWatcher(ABC):
    def __init__(self, watcher_name: str, check_interval: int = 60):
        self.watcher_name = watcher_name
        self.vault_path = get_vault_path()
        self.needs_action = self.vault_path / "Needs_Action"
        self.logs_path = self.vault_path / "Logs"
        self.check_interval = check_interval
        self.logger = logging.getLogger(self.__class__.__name__)
        self.state_file = self.logs_path / f".{self.watcher_name}_state.json"
        self.pid_file = Path(f"/tmp/{self.watcher_name}.pid")
        self._setup_logging()
        self.logs_path.mkdir(parents=True, exist_ok=True)
        self.needs_action.mkdir(parents=True, exist_ok=True)

    def _setup_logging(self) -> None:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(name)s %(levelname)s %(message)s",
        )

    def load_state(self) -> dict:
        if not self.state_file.exists():
            return {"processed_ids": []}
        return json.loads(self.state_file.read_text())

    def save_state(self, state: dict) -> None:
        self.state_file.write_text(json.dumps(state, indent=2))

    @abstractmethod
    def check_for_updates(self) -> list:
        pass

    @abstractmethod
    def create_action_file(self, item) -> Path:
        pass

    def run(self):
        self.pid_file.write_text(str(os.getpid()))
        self.logger.info("Starting %s", self.__class__.__name__)
        while True:
            try:
                items = self.check_for_updates()
                for item in items:
                    self.create_action_file(item)
            except Exception as exc:
                self.logger.exception("Error in watcher loop: %s", exc)
            time.sleep(self.check_interval)

