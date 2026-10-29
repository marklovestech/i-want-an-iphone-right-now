---
name: i-want-an-iphone-right-now
description: Check Apple Store in-store pickup availability for iPhone Duo configurations (storage, color, carrier) at the stores near a zip code or in a region such as the Bay Area, and optionally email the report. Use when asked whether an iPhone Duo is in stock for pickup, or when an automation asks for an unattended pickup check.
---

# I want an iPhone right now

Checks whether iPhone Duo configurations can be picked up today at nearby Apple Stores. It **only reads availability**: never add anything to the bag, sign in to Apple, or check out.

The checker is `scripts/apple_pickup.py`, next to this file. If you can't find it on disk, download it:
`curl -fsSLo apple_pickup.py https://raw.githubusercontent.com/marklovestech/i-want-an-iphone-right-now/main/skills/i-want-an-iphone-right-now/scripts/apple_pickup.py`

## Inputs

Take these from the user's request or the automation prompt:

| Input | Flag | Default |
|---|---|---|
| Where | `--zip 94108` (comma-separated zips; ~12 nearest stores each) or `--region bay-area` | none: ask if not given |
| Only these stores | `--stores R032,R654,...` (with `--zip`; store numbers from `--list-stores`) | every store returned |
| Configs | `--configs 1tb-white,2tb-night,...` | all 8 |
| Carrier | `--carrier att\|tmobile\|verizon\|unlocked` | `unlocked` |
| Email | `--email you@example.com` | no email |

Config keys: `256gb-white`, `256gb-night`, `512gb-white`, `512gb-night`, `1tb-white`, `1tb-night`, `2tb-white`, `2tb-night`. White is Apple's "Star White" and night is "Night Sky". There is no "Midnight Sky": map any dark/black/midnight request to Night Sky. Purchase terms are always full price, no trade-in and no AppleCare.

## Setup

1. Make sure Chrome is running with a DevTools endpoint. Devin's browser is already at `http://localhost:29229`. Elsewhere, start Chrome with `--remote-debugging-port=9222` and pass `--cdp http://localhost:9222`.
2. `pip install -q playwright` (only the Python package; it attaches to the running Chrome, no browser download needed).
3. The script opens `https://www.apple.com/shop/buy-iphone/iphone-duo` in a tab if no apple.com tab is open. Apple's availability API only answers requests from an apple.com page.

## Mode 1: interactive (a person asked for it)

1. Run the script with `--list-stores` plus the flags you plan to use. This looks up store names only, not stock.
2. Before checking availability, tell the user what you're going to do and wait for their OK:
   - Configs (storage and color), carrier, purchase terms.
   - Search area (zips or region) and the exact store list from step 1.
   - The email address, if one will get the report.
   - That it only reads availability and buys nothing.
3. Apply any changes they ask for. If the stores or configs change, confirm again.
4. Run the same command without `--list-stores`. Reply with what is available where (or "none available"), followed by the full store-by-config table so they see every store checked. Call out any store marked MISSING.

## Mode 2: unattended (an automation, or the prompt says "unattended")

Nobody is there to confirm, so skip the confirmation. Run once with the settings from the prompt, including `--email`, and exit. The script emails the report on every run:
- `IN STOCK: ...` if any config is available
- `No stock: ...` otherwise
- `Check FAILED` if Apple's API couldn't be read

If the run fails before the script could send the email (for example, playwright won't install), send the failure email yourself with the same Resend call if `RESEND_API_KEY` is set. Don't retry more than once; the next scheduled run will try again.

Email uses Resend: `RESEND_API_KEY` is required and `RESEND_FROM` is optional (it needs a domain verified in Resend). Without `RESEND_FROM` it sends from `onboarding@resend.dev`, which Resend only delivers to the Resend account owner's address.

## Gotchas

- Apple's API (`/shop/fulfillment-messages`) returns a 404 HTML page to curl or plain HTTP clients, which is why the script drives a real browser. Even in the browser, Apple's bot shield answers HTTP 541 (HTML "Page Not Found") for the first few seconds after the page loads, until its JS sets the `shld_bt_ck` cookie. The script retries for ~30s (reloading the tab once), so a non-JSON failure means something else is wrong; don't just rerun.
- A store counts as available when the API's `pickupDisplay` is `"available"`. Unavailable stores show "Currently unavailable" on the site.
- The product page's own store picker may default to a zip far from the user. Ignore it; the script passes its own zips.
- To check only some of the stores near a zip (for example, those within a short trip), run `--zip ... --list-stores` first, then pass the store numbers you want with `--stores`. A listed store Apple doesn't return is reported as MISSING.
- `--region bay-area` checks 17 stores from San Francisco to San Jose and Santa Rosa. Sacramento (Arden Fair) is not included.
- Other iPhone models: open the product page, find the `"partNumber"` values near `dimensionCapacity` / `dimensionColor` / `carrierModel` in its HTML, and add them to `CONFIGS` / `CARRIERS` in the script.
