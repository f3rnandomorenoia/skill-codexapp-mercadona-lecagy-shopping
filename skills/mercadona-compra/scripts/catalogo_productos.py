#!/usr/bin/env python3
"""Download and search a Mercadona product catalog reference CSV."""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://tienda.mercadona.es/api"
CATEGORIES_URL = f"{BASE_URL}/categories/"
DEFAULT_OUTPUT = Path("data/mercadona_productos.csv")
DEFAULT_METADATA = Path("data/mercadona_productos.metadata.json")

CSV_FIELDS = [
    "product_id",
    "display_name",
    "slug",
    "packaging",
    "unit_size",
    "size_format",
    "unit_price_eur",
    "bulk_price_eur",
    "reference_price_eur",
    "reference_format",
    "tax_percentage",
    "iva",
    "is_new",
    "is_pack",
    "approx_size",
    "selling_method",
    "unit_selector",
    "bunch_selector",
    "min_bunch_amount",
    "increment_bunch_amount",
    "total_units",
    "pack_size",
    "drained_weight",
    "limit",
    "published",
    "status",
    "unavailable_from",
    "unavailable_weekdays",
    "requires_age_check",
    "is_water",
    "thumbnail",
    "share_url",
    "department_id",
    "department_name",
    "category_id",
    "category_name",
    "subcategory_id",
    "subcategory_name",
    "source_url",
    "fetched_at",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def normalize_search(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return without_accents.casefold()


def search_tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", normalize_search(value)))


def request_json(url: str, timeout: int, retries: int) -> dict[str, Any]:
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; mercadona-catalog-reference/1.0)",
    }
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            request = Request(url, headers=headers)
            with urlopen(request, timeout=timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return json.loads(response.read().decode(charset))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt == retries:
                break
            time.sleep(1.5 * (attempt + 1))
    raise SystemExit(f"Could not download {url}: {last_error}")


def iter_catalog_categories(index: dict[str, Any]):
    for department in index.get("results", []):
        for category in department.get("categories", []):
            if category.get("published") is False:
                continue
            yield department, category


def scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value)


def build_row(
    product: dict[str, Any],
    department: dict[str, Any],
    category: dict[str, Any],
    subcategory: dict[str, Any],
    source_url: str,
    fetched_at: str,
) -> dict[str, str]:
    price = product.get("price_instructions") or {}
    badges = product.get("badges") or {}
    unavailable_weekdays = product.get("unavailable_weekdays") or []

    row = {
        "product_id": clean_text(product.get("id")),
        "display_name": clean_text(product.get("display_name")),
        "slug": clean_text(product.get("slug")),
        "packaging": clean_text(product.get("packaging")),
        "unit_size": scalar(price.get("unit_size")),
        "size_format": clean_text(price.get("size_format")),
        "unit_price_eur": scalar(price.get("unit_price")),
        "bulk_price_eur": scalar(price.get("bulk_price")),
        "reference_price_eur": scalar(price.get("reference_price")),
        "reference_format": clean_text(price.get("reference_format")),
        "tax_percentage": scalar(price.get("tax_percentage")),
        "iva": scalar(price.get("iva")),
        "is_new": scalar(price.get("is_new")),
        "is_pack": scalar(price.get("is_pack")),
        "approx_size": scalar(price.get("approx_size")),
        "selling_method": scalar(price.get("selling_method")),
        "unit_selector": scalar(price.get("unit_selector")),
        "bunch_selector": scalar(price.get("bunch_selector")),
        "min_bunch_amount": scalar(price.get("min_bunch_amount")),
        "increment_bunch_amount": scalar(price.get("increment_bunch_amount")),
        "total_units": scalar(price.get("total_units")),
        "pack_size": scalar(price.get("pack_size")),
        "drained_weight": scalar(price.get("drained_weight")),
        "limit": scalar(product.get("limit")),
        "published": scalar(product.get("published")),
        "status": clean_text(product.get("status")),
        "unavailable_from": clean_text(product.get("unavailable_from")),
        "unavailable_weekdays": "|".join(str(day) for day in unavailable_weekdays),
        "requires_age_check": scalar(badges.get("requires_age_check")),
        "is_water": scalar(badges.get("is_water")),
        "thumbnail": clean_text(product.get("thumbnail")),
        "share_url": clean_text(product.get("share_url")),
        "department_id": scalar(department.get("id")),
        "department_name": clean_text(department.get("name")),
        "category_id": scalar(category.get("id")),
        "category_name": clean_text(category.get("name")),
        "subcategory_id": scalar(subcategory.get("id")),
        "subcategory_name": clean_text(subcategory.get("name")),
        "source_url": source_url,
        "fetched_at": fetched_at,
    }
    return {field: row.get(field, "") for field in CSV_FIELDS}


def download_catalog_to(
    output: Path,
    metadata_path: Path,
    timeout: int,
    retries: int,
    keep_duplicates: bool,
) -> tuple[int, int]:
    fetched_at = utc_now()

    index = request_json(CATEGORIES_URL, timeout, retries)
    rows: list[dict[str, str]] = []
    seen_product_ids: set[str] = set()
    category_count = 0

    for department, category in iter_catalog_categories(index):
        category_count += 1
        category_id = category.get("id")
        source_url = f"{CATEGORIES_URL}{category_id}/"
        detail = request_json(source_url, timeout, retries)
        for subcategory in detail.get("categories", []):
            for product in subcategory.get("products", []):
                product_id = clean_text(product.get("id"))
                if not keep_duplicates and product_id in seen_product_ids:
                    continue
                seen_product_ids.add(product_id)
                rows.append(build_row(product, department, category, subcategory, source_url, fetched_at))

    rows.sort(key=lambda item: (item["department_name"], item["category_name"], item["subcategory_name"], item["display_name"]))

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    metadata = {
        "source": "Mercadona online store API",
        "source_url": CATEGORIES_URL,
        "fetched_at": fetched_at,
        "category_count": category_count,
        "product_count": len(rows),
        "deduplicated_by_product_id": not keep_duplicates,
        "csv": str(output),
        "note": "Catalog availability and prices can vary by date, location, and Mercadona online changes.",
    }
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return len(rows), category_count


def download_catalog(args: argparse.Namespace) -> None:
    output = Path(args.output)
    metadata_path = Path(args.metadata)
    product_count, category_count = download_catalog_to(
        output=output,
        metadata_path=metadata_path,
        timeout=args.timeout,
        retries=args.retries,
        keep_duplicates=args.keep_duplicates,
    )

    print(f"Downloaded {product_count} products from {category_count} categories to {output}")
    print(f"Metadata written to {metadata_path}")


def search_catalog(args: argparse.Namespace) -> None:
    catalog = Path(args.file)
    if not catalog.exists():
        if args.no_auto_download:
            raise SystemExit(f"Catalog file not found: {catalog}")
        print(f"Catalog file not found: {catalog}. Downloading it now...")
        metadata_path = Path(args.metadata)
        product_count, category_count = download_catalog_to(
            output=catalog,
            metadata_path=metadata_path,
            timeout=args.timeout,
            retries=args.retries,
            keep_duplicates=args.keep_duplicates,
        )
        print(f"Downloaded {product_count} products from {category_count} categories to {catalog}")

    query = normalize_search(args.query)
    terms = [term for term in query.split() if term]
    matches: list[tuple[int, str, dict[str, str]]] = []
    with catalog.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            name = row.get("display_name", "")
            normalized_name = normalize_search(name)
            name_tokens = search_tokens(name)
            searchable = normalize_search(
                " ".join(
                    [
                        row.get("display_name", ""),
                        row.get("packaging", ""),
                        row.get("category_name", ""),
                        row.get("subcategory_name", ""),
                    ]
                )
            )
            full_tokens = search_tokens(searchable)
            if normalized_name.startswith(query):
                score = 0
            elif query in normalized_name:
                score = 1
            elif all(term in name_tokens for term in terms):
                score = 2
            elif all(term in full_tokens for term in terms):
                score = 3
            elif all(term in searchable for term in terms):
                score = 4
            else:
                continue
            matches.append((score, normalized_name, row))

    matches.sort(key=lambda item: (item[0], item[1]))
    for _, _, row in matches[: args.limit]:
        size = " ".join(part for part in [row.get("unit_size", ""), row.get("size_format", "")] if part)
        price = row.get("unit_price_eur", "")
        suffix = f" | {price} EUR" if price else ""
        print(
            f"{row.get('product_id')} | {row.get('display_name')} | "
            f"{row.get('packaging')} {size}".strip()
            + suffix
        )
    print(f"Matches: {len(matches)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download and search Mercadona product catalog CSV.")
    sub = parser.add_subparsers(dest="command", required=True)

    download = sub.add_parser("download", help="Download the current Mercadona catalog as CSV")
    download.add_argument("--output", default=str(DEFAULT_OUTPUT))
    download.add_argument("--metadata", default=str(DEFAULT_METADATA))
    download.add_argument("--timeout", type=int, default=20)
    download.add_argument("--retries", type=int, default=2)
    download.add_argument("--keep-duplicates", action="store_true", help="Keep repeated products if Mercadona returns them in more than one category")
    download.set_defaults(func=download_catalog)

    search = sub.add_parser("search", help="Search an existing catalog CSV")
    search.add_argument("query")
    search.add_argument("--file", default=str(DEFAULT_OUTPUT))
    search.add_argument("--metadata", default=str(DEFAULT_METADATA))
    search.add_argument("--limit", type=int, default=20)
    search.add_argument("--timeout", type=int, default=20)
    search.add_argument("--retries", type=int, default=2)
    search.add_argument("--keep-duplicates", action="store_true", help="Keep repeated products if auto-downloading the catalog")
    search.add_argument("--no-auto-download", action="store_true", help="Fail instead of downloading when the catalog CSV is missing")
    search.set_defaults(func=search_catalog)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
