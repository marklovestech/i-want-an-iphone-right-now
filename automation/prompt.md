Use the i-want-an-iphone-right-now skill (from the org plugin of the same name; if it is not loaded, follow https://github.com/marklovestech/i-want-an-iphone-right-now/blob/main/skills/i-want-an-iphone-right-now/SKILL.md) in unattended mode. Nobody is watching this session: don't ask questions or wait for confirmation; run once and stop.

Pick the stores by the current time (run `TZ=America/New_York date` to check):
- Before 2026-11-04 18:00 America/New_York: 9 New York stores (Manhattan and Brooklyn) near the Bowery: `--zip 10002 --stores R032,R594,R654,R250,R715,R415,R095,R582,R251`
- From 2026-11-04 18:00 America/New_York on: `--region bay-area` (all 17 Bay Area Apple Stores)

Other settings:
- Carrier: att
- Configs: 1tb-white,1tb-night,2tb-white,2tb-night
- Email the report to: mark@marklovestech.com

That is, until Nov 4 at 6pm Eastern:
python3 apple_pickup.py --zip 10002 --stores R032,R594,R654,R250,R715,R415,R095,R582,R251 --carrier att --configs 1tb-white,1tb-night,2tb-white,2tb-night --email mark@marklovestech.com

and after that:
python3 apple_pickup.py --region bay-area --carrier att --configs 1tb-white,1tb-night,2tb-white,2tb-night --email mark@marklovestech.com

The script emails the report itself (subject "IN STOCK: ...", "No stock: ..." or "Check FAILED"), using the RESEND_API_KEY secret. If the run fails before the script could email (for example, playwright won't install or Chrome isn't reachable), send a "Check FAILED: iPhone Duo pickup" email to the same address yourself via the Resend API with RESEND_API_KEY, including the error. Never add anything to an Apple bag, sign in, or check out.
