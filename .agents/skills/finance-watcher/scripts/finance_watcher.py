from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.config import get_vault_path


def append_transaction(current_month: Path, row: dict) -> None:
    if not current_month.exists():
        current_month.write_text("# Current Month Transactions\n\n")
    with current_month.open("a", encoding="utf-8") as f:
        f.write(
            f"- {row.get('date','')} | {row.get('description','')} | {row.get('amount','')} | {row.get('category','uncategorized')}\n"
        )


def create_action_file(needs_action: Path, row: dict) -> None:
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    file_path = needs_action / f"FINANCE_{ts}.md"
    file_path.write_text(
        f"""---
type: finance
source: csv_drop
date: {row.get('date', '')}
description: {row.get('description', '')}
amount: {row.get('amount', '')}
status: pending
---

## Transaction Review
- [ ] Confirm categorization
- [ ] Validate amount
"""
    )


def process_csv_file(csv_path: Path, vault: Path) -> None:
    accounting = vault / "Accounting"
    done = vault / "Done"
    needs_action = vault / "Needs_Action"
    current_month = accounting / "Current_Month.md"

    needs_action.mkdir(parents=True, exist_ok=True)
    done.mkdir(parents=True, exist_ok=True)

    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            append_transaction(current_month, row)
            create_action_file(needs_action, row)

    shutil.move(str(csv_path), str(done / csv_path.name))


def main() -> None:
    vault = get_vault_path()
    drops = vault / "Accounting" / "Drops"
    drops.mkdir(parents=True, exist_ok=True)

    while True:
        for file in drops.glob("*.csv"):
            process_csv_file(file, vault)
        time.sleep(5)


if __name__ == "__main__":
    main()
