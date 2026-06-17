# Mercadona Web Workflow

## Entry Points

Primary legacy Telecompra URL for this skill:

```text
https://www.telecompra.mercadona.es/ns/entrada.php?js=1&nidioma=1
```

Current Mercadona online URL:

```text
https://tienda.mercadona.es/
```

Use the legacy Telecompra URL when the user asks for Telecompra, saved web lists, or the classic list workflow. Use the current Mercadona site only when Telecompra blocks the browser session or the user asks for the newer site. The Telecompra host may return a Mercadona error page or HTTP 403 outside a normal browser session, so do not validate it with `curl` alone. Always operate on the visible site state, not on assumptions from this reference.

The authenticated Telecompra session normally lands on:

```text
https://www.telecompra.mercadona.es/ns/principal.php
```

## Browser Setup

1. Use the `Computer Use` plugin and target the `Google Chrome` app.
2. Call `get_app_state` once before interacting with Chrome in each assistant turn.
3. Open `https://www.telecompra.mercadona.es/ns/entrada.php?js=1&nidioma=1` in Chrome. Prefer a new tab unless the user is already on the Mercadona flow and asks to continue there.
4. Handle cookie or service popups with the user's preference. If the user did not specify, choose the least intrusive option that still allows shopping.
5. If login is needed, pause at the `Cliente registrado` form and ask the user to enter credentials and solve reCAPTCHA directly in the page. Continue only after the user says login is complete or the authenticated page is visible.
6. After login, claim or select the tab whose URL contains `/ns/principal.php` if the original login tab remains on `entrada.php`.

## Computer Use Interaction Notes

- Prefer accessibility element IDs from `get_app_state` for fields, links, and normal buttons.
- Use `set_value` for ordinary text fields such as product search, list names, and quantity fields when they expose a settable element.
- Use `click` by element ID for normal links and buttons.
- Use coordinate clicks only for legacy image buttons or controls whose element IDs become stale after page updates.
- Re-run `get_app_state` after navigation, saving, adding products, or any page update that may recycle element IDs.
- Do not use browser devtools, DOM inspection, network logs, cookie reads, or storage reads during login or shopping unless the user explicitly asks for debugging and no secrets are involved.

## Location and Account Boundaries

The current online store may ask for postal code or delivery area before showing products or login. Let the user provide address-specific information directly in the browser when needed. If Mercadona says online shopping is unavailable for that area, report the visible message and stop the web-cart workflow.

## Login and Account Boundaries

Telecompra exposes `E-mail / Usuario de acceso`, `Contraseña`, an `ENTRAR` button, and reCAPTCHA on the entry page. Do not read, store, repeat, type, paste, or infer password text. If the user is not registered or delivery is unavailable for the address, report the visible message and stop.

## Private Login Protocol

Use this protocol whenever a Mercadona session requires credentials:

1. Navigate to the login screen and stop before entering any secret.
2. Tell the user: "Introduce tu usuario y contrasena directamente en el navegador. Avisame cuando hayas iniciado sesion."
3. While the user enters credentials, do not inspect DOM input values, run JavaScript against credential fields, read browser password manager UI, read cookies, read local/session storage, inspect authentication network payloads, or request screenshots centered on password-manager popups.
4. If browser control requires checking progress, rely on non-secret visible state only, such as the page title, logged-in account area, cart page, product page, or generic error banners.
5. If login fails, report only the visible non-secret message. Do not ask the user to paste the password into chat.
6. If the user accidentally sends a password in chat, do not repeat it. Tell the user to change it if they believe it may be exposed, and continue only with direct browser entry.

## Creating or Loading a List

Prefer a local JSON list as the durable source of truth. In Telecompra, use the right-side panel for `Ticket actual` and `Mis listas`.

To save the current ticket as a list:

1. Add the intended products to `Ticket actual`.
2. Click `GUARDAR` in the right-side ticket panel.
3. Watch for the `Guardar lista` popup/new tab at `/ns/listaname.php`.
4. Enter a clear name, normally `Compra YYYY-MM-DD` unless the user provides one.
5. Click `ACEPTAR`; the popup usually closes automatically.
6. Open the `Mis listas` tab to confirm that the list appears.

To load a saved list:

1. Open `Mis listas`.
2. Click the list name, not the trash icon.
3. Confirm the center panel shows the list contents.
4. Keep desired products checked and use `Incluir al ticket selección` to add them to the current ticket.
5. Use `Cerrar lista` to return to normal product browsing.

Confirm before clicking any trash icon or replacing/removing existing saved lists.

## Product Search and Add Flow

For each local list item:

1. Search the local catalog first; `scripts/catalogo_productos.py search ...` downloads the CSV automatically if it is missing. Use product name, package size, and share URL as hints.
2. In Telecompra, use the left `Buscador` fields: put the product phrase in `Producto` and put brand terms such as `Hacendado` in `Marca` only when useful.
3. Search with the shortest meaningful product phrase first, for example `leche entera`; avoid putting brand and package details all in `Producto`, because it can return 0 results.
4. Inspect results for package size, unit, brand, fresh/frozen state, and dietary details.
5. Choose exact matches automatically only when the name and pack size clearly match the user intent.
6. Ask before choosing among materially different products, such as different sizes, fresh versus frozen, different brands, or major price differences.
7. Add the product using the basket icon in the `Incluir` column and adjust quantity using the plus/minus controls.
8. Re-check `Ticket actual` after each add.

## Quantity Mapping

- `qty` with `unit` `ud`, `unidad`, `pack`, `brik`, `botella`, `lata`, or blank usually maps to item count.
- Weight-based products may require approximate units. Ask before selecting cuts, weights, or substitutes.
- If the site only allows increments that do not match the request, choose the nearest lower amount and report it, unless the user approves a higher amount.

## Saving and Checkout

Saving a list or cart is allowed when requested. Checkout is a separate high-impact action:

1. Show or summarize the basket.
2. Ask the user to confirm address, delivery slot, substitutions, and estimated total.
3. Do not click final purchase/order confirmation without an explicit user confirmation in the current conversation.

## Popup Handling

- `GUARDAR` opens a small popup/new tab titled `Guardar lista`. Claim or switch to it, fill the list name, click `ACEPTAR`, then return to `/ns/principal.php`.
- Forgotten-password and some help/conditions links also open popups or new tabs. Do not use them unless requested.
- If a popup closes immediately after an action, return to the main Telecompra tab and verify the visible result in `Ticket actual` or `Mis listas`.
- If reCAPTCHA appears during login, hand control to the user.

## Reporting Template

Use this concise structure after a web run:

```text
Anadidos:
- producto x cantidad

Pendientes:
- producto: motivo

Sustituciones:
- solicitado -> anadido: motivo

Siguiente accion:
- confirmar cesta / elegir alternativas / guardar lista
```
