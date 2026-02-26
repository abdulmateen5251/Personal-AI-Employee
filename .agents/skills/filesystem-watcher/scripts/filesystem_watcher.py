from pathlib import Path
import shutil
import sys
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.config import get_vault_path


class DropFolderHandler(FileSystemEventHandler):
    def __init__(self, vault_path: Path):
        self.needs_action = vault_path / "Needs_Action"
        self.needs_action.mkdir(parents=True, exist_ok=True)

    def on_created(self, event):
        if event.is_directory:
            return
        source = Path(event.src_path)
        dest = self.needs_action / f"FILE_{source.name}"
        shutil.copy2(source, dest)
        self.create_metadata(source, dest)

    def create_metadata(self, source: Path, dest: Path):
        meta_path = dest.with_suffix(".md")
        meta_path.write_text(
            f"""---
type: file_drop
original_name: {source.name}
size: {source.stat().st_size}
status: pending
---

New file dropped for processing.
"""
        )


def main() -> None:
    vault = get_vault_path()
    inbox = vault / "Inbox"
    inbox.mkdir(parents=True, exist_ok=True)

    observer = Observer()
    observer.schedule(DropFolderHandler(vault), str(inbox), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
