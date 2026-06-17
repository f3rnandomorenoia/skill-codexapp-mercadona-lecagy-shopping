---
name: mercadona-compra
description: Manage Mercadona online shopping workflows and reusable shopping lists. Use when Codex needs to create, update, save, import, export, or apply a shopping list for Mercadona Telecompra or Mercadona online, add products to the cart, search products, adjust quantities, preserve a local shopping-list file, or assist a user through login and checkout without storing credentials.
---

# Mercadona Compra

## Overview

Use this skill to manage a Mercadona shopping list locally and, when requested, apply it to the Mercadona online shopping site. Treat the live website as assisted browsing: the user must handle password entry, second-factor checks, address choice, payment, and final order confirmation.

## Quick Workflow

1. Clarify the target action only if needed: create a list, add products, remove products, save/export the list, load an existing list, or apply the list to the web cart.
2. For local list operations, use `scripts/lista_compra.py` and store JSON files in the user's project or requested folder.
3. For product matching, consult the local catalog CSV first. `scripts/catalogo_productos.py search ...` automatically downloads the catalog if the CSV is missing. Treat it as a dated reference, not as guaranteed live availability.
4. For live website operations, read `references/mercadona-web-workflow.md` before opening the site.
5. Use the `Computer Use` plugin with Google Chrome for live website operations. Fall back to another interactive browser only if Computer Use or Chrome is unavailable.
6. Pause at credential entry. Ask the user to type the password directly into the browser and resume only after the user says it is complete or the authenticated page is visible.
7. Never inspect password input values, authentication payloads, cookies, local/session storage, saved passwords, payment data, or card data.
8. Never store passwords, payment data, card data, or cookies in skill files.
9. Never submit the final order unless the user explicitly asks and confirms the final basket, delivery slot, address, and total.

## Local Shopping Lists

Use `scripts/lista_compra.py` for deterministic list handling:

```bash
python3 skills/mercadona-compra/scripts/lista_compra.py init --file compra.json
python3 skills/mercadona-compra/scripts/lista_compra.py add --file compra.json --product "leche entera" --qty 6 --unit "brik"
python3 skills/mercadona-compra/scripts/lista_compra.py list --file compra.json
python3 skills/mercadona-compra/scripts/lista_compra.py export-text --file compra.json
```

Represent products as plain user intent, not as assumed exact SKUs. Preserve notes like brand, size, dietary restrictions, substitutes, and maximum price when provided.

## Product Catalog Reference

Use `scripts/catalogo_productos.py` to download and search a dated CSV reference from Mercadona's online store API. `search` downloads the catalog automatically when the CSV is missing:

```bash
python3 skills/mercadona-compra/scripts/catalogo_productos.py download
python3 skills/mercadona-compra/scripts/catalogo_productos.py search "leche entera"
```

Default generated files:

- `data/mercadona_productos.csv`
- `data/mercadona_productos.metadata.json`

The catalog is useful for first-pass product matching and SKU hints. It is not a guarantee that an item is currently available for the user's address, delivery slot, or live session. Confirm ambiguous matches on the website before adding them to a cart.

## Applying a List to Mercadona

Before using the web, load `references/mercadona-web-workflow.md`. Use the local JSON list as the source of truth, then search each item on the site and choose the closest match. If multiple plausible matches exist, ask the user before choosing.

For live web work, operate Chrome through `Computer Use`: call the app-state tool first, use visible accessibility elements when available, and use coordinates only for old image buttons or controls that do not expose stable element IDs.

Track results as you work:

- `added`: product found and added with intended quantity.
- `needs_choice`: multiple plausible products or unclear package size.
- `not_found`: no adequate match found.
- `changed`: requested product added with a substitution or adjusted quantity after user approval.

After applying the list, report a concise summary with missing products, substitutions, and anything that needs user confirmation.

## Safety Rules

- Ask the user to enter login credentials directly in the browser.
- During login, do not use DOM inspection, JavaScript evaluation, network logs, screenshots focused on password managers, or browser storage reads to learn secrets.
- Do not type or paste a password on behalf of the user, even if the user provides one in chat. Ask the user to enter it directly in the browser instead.
- Do not bypass captchas, security checks, age checks, or delivery restrictions.
- Confirm before deleting a saved web list or replacing an existing cart.
- If the site shows a service-area, address, or delivery limitation, report it exactly and stop that part of the workflow.
- If the site layout differs from the reference, inspect the visible UI and continue conservatively.
