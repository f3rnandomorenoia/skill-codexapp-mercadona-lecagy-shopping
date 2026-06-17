#!/usr/bin/env python3
"""Manage a simple Mercadona shopping list JSON file."""

from __future__ import annotations

import argparse
import contextlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback
    fcntl = None


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def empty_list() -> dict[str, Any]:
    stamp = now_iso()
    return {"version": 1, "created_at": stamp, "updated_at": stamp, "items": []}


@contextlib.contextmanager
def locked_file(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")
    with lock_path.open("w", encoding="utf-8") as lock:
        if fcntl is not None:
            fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(lock, fcntl.LOCK_UN)


def load_list(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_list()
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise SystemExit(f"Invalid shopping-list file: {path}")
    data.setdefault("version", 1)
    data.setdefault("created_at", now_iso())
    data.setdefault("updated_at", now_iso())
    return data


def save_list(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = now_iso()
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def normalize_product(value: str) -> str:
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        raise SystemExit("Product name cannot be empty")
    return cleaned


def find_item(data: dict[str, Any], product: str) -> dict[str, Any] | None:
    key = product.casefold()
    for item in data["items"]:
        if str(item.get("product", "")).casefold() == key:
            return item
    return None


def cmd_init(args: argparse.Namespace) -> None:
    path = Path(args.file)
    with locked_file(path):
        if path.exists() and not args.force:
            raise SystemExit(f"File already exists: {path}. Use --force to replace it.")
        save_list(path, empty_list())
    print(f"Initialized {path}")


def cmd_add(args: argparse.Namespace) -> None:
    path = Path(args.file)
    product = normalize_product(args.product)
    with locked_file(path):
        data = load_list(path)
        item = find_item(data, product)
        if item is None:
            item = {
                "product": product,
                "qty": args.qty,
                "unit": args.unit,
                "notes": args.notes,
            }
            data["items"].append(item)
            action = "Added"
        else:
            item["qty"] = item.get("qty", 0) + args.qty if args.increment else args.qty
            if args.unit:
                item["unit"] = args.unit
            if args.notes:
                item["notes"] = args.notes
            action = "Updated"
        save_list(path, data)
    print(f"{action}: {item['product']} x {item['qty']} {item.get('unit') or ''}".rstrip())


def cmd_remove(args: argparse.Namespace) -> None:
    path = Path(args.file)
    product = normalize_product(args.product)
    with locked_file(path):
        data = load_list(path)
        original_len = len(data["items"])
        data["items"] = [
            item for item in data["items"]
            if str(item.get("product", "")).casefold() != product.casefold()
        ]
        if len(data["items"]) == original_len:
            raise SystemExit(f"Product not found: {product}")
        save_list(path, data)
    print(f"Removed: {product}")


def format_item(item: dict[str, Any]) -> str:
    qty = item.get("qty", 1)
    unit = item.get("unit") or ""
    notes = item.get("notes") or ""
    suffix = f" ({notes})" if notes else ""
    middle = f" {unit}" if unit else ""
    return f"- {item.get('product')} x {qty}{middle}{suffix}"


def cmd_list(args: argparse.Namespace) -> None:
    path = Path(args.file)
    with locked_file(path):
        data = load_list(path)
    if not data["items"]:
        print("Shopping list is empty")
        return
    for item in data["items"]:
        print(format_item(item))


def cmd_export_text(args: argparse.Namespace) -> None:
    path = Path(args.file)
    with locked_file(path):
        data = load_list(path)
    lines = [format_item(item) for item in data["items"]]
    text = "\n".join(lines)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + ("\n" if text else ""), encoding="utf-8")
        print(f"Exported {len(lines)} items to {output}")
    else:
        print(text)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage a Mercadona shopping list JSON file.")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create an empty shopping list")
    init.add_argument("--file", required=True)
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=cmd_init)

    add = sub.add_parser("add", help="Add or update a product")
    add.add_argument("--file", required=True)
    add.add_argument("--product", required=True)
    add.add_argument("--qty", type=float, default=1)
    add.add_argument("--unit", default="")
    add.add_argument("--notes", default="")
    add.add_argument("--increment", action="store_true", help="Increment existing quantity instead of replacing it")
    add.set_defaults(func=cmd_add)

    remove = sub.add_parser("remove", help="Remove a product")
    remove.add_argument("--file", required=True)
    remove.add_argument("--product", required=True)
    remove.set_defaults(func=cmd_remove)

    show = sub.add_parser("list", help="Print the shopping list")
    show.add_argument("--file", required=True)
    show.set_defaults(func=cmd_list)

    export = sub.add_parser("export-text", help="Export the list as plain text")
    export.add_argument("--file", required=True)
    export.add_argument("--output")
    export.set_defaults(func=cmd_export_text)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
