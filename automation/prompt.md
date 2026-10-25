Use the @skills:i-want-an-iphone-right-now skill in unattended mode. Nobody is watching this session: don't ask questions or wait for confirmation; run once and stop.

Check iPhone Duo in-store pickup with these settings:
- Region: bay-area (all 17 Bay Area Apple Stores)
- Carrier: att
- Configs: 1tb-white,1tb-night,2tb-white,2tb-night
- Email the report to: mark@marklovestech.com

That is:
python3 apple_pickup.py --region bay-area --carrier att --configs 1tb-white,1tb-night,2tb-white,2tb-night --email mark@marklovestech.com

The script emails the report itself (subject "IN STOCK: ...", "No stock: ..." or "Check FAILED"), using the RESEND_API_KEY secret. If the run fails before the script could email (for example, playwright won't install or Chrome isn't reachable), send a "Check FAILED: iPhone Duo pickup" email to the same address yourself via the Resend API with RESEND_API_KEY, including the error. Never add anything to an Apple bag, sign in, or check out.
