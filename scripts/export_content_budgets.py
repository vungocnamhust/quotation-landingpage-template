#!/usr/bin/env python3
"""Export unified content budgets from SSoT YAML to Frontend JSON."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from core.rules.content_budgets import get_content_budget_registry

TARGET_PATH = ROOT_DIR / "quote-generator" / "config" / "contentBudgets.json"


def export_content_budgets(check_only: bool = False) -> bool:
    registry = get_content_budget_registry("v1")
    data = registry.to_dict()
    rendered = json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    if check_only:
        if not TARGET_PATH.exists():
            print(f"ERROR: {TARGET_PATH} does not exist. Run export_content_budgets.py to generate it.")
            return False
        current = TARGET_PATH.read_text(encoding="utf-8")
        if current != rendered:
            print(f"ERROR: {TARGET_PATH} is out of sync with prompts/v1/content_budgets.yaml.")
            return False
        print(f"OK: {TARGET_PATH} is in sync with SSoT.")
        return True

    TARGET_PATH.parent.mkdir(parents=True, exist_ok=True)
    TARGET_PATH.write_text(rendered, encoding="utf-8")
    print(f"Successfully exported unified content budgets to {TARGET_PATH}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Export content budgets to frontend JSON config.")
    parser.add_argument("--check", action="store_true", help="Check if exported file is in sync without modifying.")
    args = parser.parse_args()

    success = export_content_budgets(check_only=args.check)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
