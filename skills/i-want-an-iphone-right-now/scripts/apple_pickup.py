#!/usr/bin/env python3
"""Check Apple Store in-store pickup availability for iPhone Duo configurations.

Apple's availability API only answers fetch() calls made from an apple.com page
in a real browser, so this drives Chrome over the DevTools protocol (CDP).
It only reads availability; it never adds to the bag or checks out.
"""
import argparse
import asyncio
import json
import os
import sys
import urllib.request
from urllib.parse import urlparse

PRODUCT_URL = "https://www.apple.com/shop/buy-iphone/iphone-duo"
CONFIGS = {
    "256gb-white": ("MK1E4LL/A", "256GB Star White"), "256gb-night": ("MK1F4LL/A", "256GB Night Sky"),
    "512gb-white": ("MK1G4LL/A", "512GB Star White"), "512gb-night": ("MK1H4LL/A", "512GB Night Sky"),
    "1tb-white": ("MK1J4LL/A", "1TB Star White"), "1tb-night": ("MK1L4LL/A", "1TB Night Sky"),
    "2tb-white": ("MK1Q4LL/A", "2TB Star White"), "2tb-night": ("MK1R4LL/A", "2TB Night Sky"),
}
CARRIERS = {"att": "ATT_IPHONEDUO", "tmobile": "TMOBILE_IPHONEDUO",
            "verizon": "VERIZON_IPHONEDUO", "unlocked": "UNLOCKED/US"}
# Each region is a set of search zips (each returns the ~12 nearest stores) plus
# the stores that count as "in the region"; other stores returned are ignored.
REGIONS = {
    "bay-area": {
        "zips": ["94108", "95128", "94596", "95401", "94538"],
        "stores": {
            "R075": "Union Square", "R217": "Chestnut Street", "R033": "Stonestown",
            "R057": "Bay Street", "R414": "4th Street", "R071": "Corte Madera",
            "R029": "Burlingame", "R231": "Hillsdale", "R014": "Broadway Plaza",
            "R101": "Stoneridge Mall", "R099": "Stanford Shopping Center", "R002": "Palo Alto",
            "R824": "Apple Park Visitor Center", "R240": "Los Gatos", "R105": "Oakridge",
            "R039": "Valley Fair", "R044": "Montgomery Village",
        },
    },
}
API = ("/shop/fulfillment-messages?fae=true&little=false&parts.0={part}&cppart={cp}"
       "&purchaseOption=fullPrice&mts.0=regular&mts.1=sticky&fts=true&pl=true"
       "&searchNearby=true&location={zip}")


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    where = ap.add_mutually_exclusive_group(required=True)
    where.add_argument("--zip", help="comma-separated zip codes; checks the ~12 stores nearest each")
    where.add_argument("--region", choices=REGIONS, help="check every store in a predefined region")
    ap.add_argument("--carrier", default="unlocked", choices=CARRIERS)
    ap.add_argument("--configs", default=",".join(CONFIGS),
                    help="comma-separated config keys (default: all): " + ", ".join(CONFIGS))
    ap.add_argument("--list-stores", action="store_true",
                    help="only list the stores that would be checked; don't check availability")
    ap.add_argument("--email", help="also email the report to this address via Resend (needs RESEND_API_KEY)")
    ap.add_argument("--cdp", default="http://localhost:29229", help="Chrome DevTools endpoint")
    args = ap.parse_args(argv)
    bad = [c for c in args.configs.split(",") if c.strip() not in CONFIGS]
    if bad:
        ap.error(f"unknown config(s) {bad}; choose from {list(CONFIGS)}")
    if args.zip is not None and not [z for z in args.zip.split(",") if z.strip()]:
        ap.error("--zip needs at least one zip code")
    if args.email and not args.list_stores and not os.environ.get("RESEND_API_KEY"):
        ap.error("--email needs the RESEND_API_KEY environment variable")
    return args


def plan(args):
    """Return (configs, search zips, expected stores or None, area description)."""
    configs = [CONFIGS[c.strip()] for c in args.configs.split(",")]
    if args.region:
        r = REGIONS[args.region]
        return configs, r["zips"], r["stores"], f"{args.region} stores"
    zips = [z.strip() for z in args.zip.split(",") if z.strip()]
    return configs, zips, None, "stores nearest " + ", ".join(zips)


def merge(responses, configs):
    """Combine API store lists into ({store: (name, city, distance)}, {(store, part): available})."""
    stores, avail = {}, {}
    for part, store_list in responses:
        for s in store_list:
            stores.setdefault(s["storeNumber"], (s["storeName"], s["city"], s.get("storeDistanceWithUnit", "")))
            pickup = s.get("partsAvailability", {}).get(part, {}).get("pickupDisplay")
            avail[(s["storeNumber"], part)] = pickup == "available"
    return stores, avail


def store_order(stores, expected):
    return list(expected) if expected else list(stores)


def label(num, stores, expected):
    if num not in stores:
        return f"{num} {expected[num]}"
    name, city, dist = stores[num]
    return f"{num} {name}, {city}" + (f" ({dist})" if not expected and dist else "")


def store_list_report(stores, expected, area):
    order = store_order(stores, expected)
    lines = [f"{len(order)} {area}:"]
    for num in order:
        lines.append("  " + label(num, stores, expected) +
                     ("" if num in stores else " (MISSING: not returned by Apple)"))
    return "\n".join(lines)


def availability_report(stores, avail, expected, configs, carrier, area):
    """Return (hits, report text)."""
    order = store_order(stores, expected)
    lines = [f"Carrier: {carrier} ({CARRIERS[carrier]}), full price, no AppleCare, no trade-in",
             f"Area: {area}", "",
             f"{'Store':52} | " + " | ".join(f"{l:16}" for _, l in configs)]
    hits, checked = [], 0
    for num in order:
        if num not in stores:
            lines.append(f"{label(num, stores, expected):52} | MISSING: not returned by Apple")
            continue
        checked += 1
        row = []
        for part, l in configs:
            ok = avail.get((num, part), False)
            row.append(f"{'AVAILABLE' if ok else '-':16}")
            if ok:
                hits.append(f"{l} at {stores[num][0]}, {stores[num][1]}")
        lines.append(f"{label(num, stores, expected):52} | " + " | ".join(row))
    lines += ["", f"Checked {checked} of {len(order)} {area} x {len(configs)} configs.",
              "Available: " + ("; ".join(hits) if hits else "none")]
    return hits, "\n".join(lines)


def subject(hits, n_stores, n_configs):
    if hits:
        return f"IN STOCK: iPhone Duo pickup - {'; '.join(hits)}"[:200]
    return f"No stock: iPhone Duo pickup ({n_stores} stores x {n_configs} configs)"


def send_email(to, subj, text):
    body = json.dumps({"from": os.environ.get("RESEND_FROM") or "onboarding@resend.dev",
                       "to": [to], "subject": subj, "text": text}).encode()
    req = urllib.request.Request("https://api.resend.com/emails", data=body, headers={
        "Authorization": f"Bearer {os.environ['RESEND_API_KEY']}",
        "Content-Type": "application/json", "User-Agent": "i-want-an-iphone-right-now"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["id"]


async def apple_page(browser):
    for ctx in browser.contexts:
        for pg in ctx.pages:
            if urlparse(pg.url).hostname == "www.apple.com":
                return pg
    ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
    pg = await ctx.new_page()
    await pg.goto(PRODUCT_URL, wait_until="domcontentloaded")
    return pg


async def fetch_all(args, configs, zips):
    from playwright.async_api import async_playwright
    cp = CARRIERS[args.carrier]
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(args.cdp)
        page = await apple_page(browser)
        responses = []
        for part, _ in (configs[:1] if args.list_stores else configs):
            for z in zips:
                text = await page.evaluate("u => fetch(u).then(r => r.text())",
                                           API.format(part=part, cp=cp, zip=z))
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    raise RuntimeError(f"Apple returned non-JSON for {part} near {z}; reload the apple.com tab and retry")
                responses.append((part, data["body"]["content"]["pickupMessage"]["stores"]))
        return responses


def main(argv=None):
    args = parse_args(argv)
    configs, zips, expected, area = plan(args)
    try:
        stores, avail = merge(asyncio.run(fetch_all(args, configs, zips)), configs)
    except Exception as e:
        if args.email and not args.list_stores:
            send_email(args.email, "Check FAILED: iPhone Duo pickup", f"The availability check failed:\n{e}")
        raise
    if args.list_stores:
        print(store_list_report(stores, expected, area))
        return
    hits, report = availability_report(stores, avail, expected, configs, args.carrier, area)
    print(report)
    if args.email:
        msg_id = send_email(args.email, subject(hits, len(store_order(stores, expected)), len(configs)), report)
        print(f"\nEmailed report to {args.email} (Resend id {msg_id})")


if __name__ == "__main__":
    sys.exit(main())
