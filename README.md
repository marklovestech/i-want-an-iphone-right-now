# i-want-an-iphone-right-now

Simple Devin skill (also Claude compatible) that tries to find an iPhone in stock for pickup near you. Run it on demand, or as a scheduled Devin automation that emails you a report after every check. Your mileage with your agent may vary.

It checks Apple's own pickup availability (the same data behind "Check availability" on apple.com) for every storage/color combination you care about, at every store near your zip code, and prints a store-by-config table (illustrative example):

```
Carrier: att (ATT_IPHONEDUO), full price, no AppleCare, no trade-in
Area: stores nearest 94108

Store                                                | 1TB Night Sky    | 2TB Night Sky
R075 Union Square, San Francisco (0.1 mi)            | -                | -
R217 Chestnut Street, San Francisco (2.4 mi)         | AVAILABLE        | -
...
Checked 12 of 12 stores nearest 94108 x 2 configs.
Available: 1TB Night Sky at Chestnut Street, San Francisco
```

It only **reads** availability. It never adds anything to your bag, signs in to Apple, or checks out.

Right now it knows the iPhone Duo (256GB to 2TB, Star White and Night Sky) on AT&T, T-Mobile, Verizon or unlocked. Other models need their part numbers added (see [the skill](skills/i-want-an-iphone-right-now/SKILL.md#gotchas)).

## How it works

Apple's availability API (`/shop/fulfillment-messages`) refuses plain HTTP clients like curl, but answers requests made from an apple.com page in a real browser. The script ([`apple_pickup.py`](skills/i-want-an-iphone-right-now/scripts/apple_pickup.py)) attaches to a running Chrome over the DevTools protocol, opens an apple.com tab, and calls the API from there for each config and zip. Devin sessions already have that Chrome. Because this depends on Apple's website, it can break whenever Apple changes it.

The [skill](skills/i-want-an-iphone-right-now/SKILL.md) tells the agent how to run the script in two modes:

- **Interactive** (you ask for a check): it tells you the configs, carrier, area, the exact list of stores and the email address (if any), and waits for your OK before checking.
- **Unattended** (an automation runs it): it skips the confirmation, runs once, and emails the report.

## Set it up in Devin

### 1. Create a Devin account and log in

1. Go to [app.devin.ai](https://app.devin.ai) and sign up. Pick a plan: the individual plan is enough for this. See [Getting access](https://docs.devin.ai/get-started/devin-intro#getting-access).
2. After that, log in at [app.devin.ai](https://app.devin.ai) whenever you want to use Devin. If your company already has Devin, use your company's Devin URL and log in through its sign-in instead.

### 2. Connect GitHub (optional)

Installing the skill from this public repo doesn't need GitHub. Connect GitHub if you want to fork the repo and change it (for example, to add another region or iPhone model) and have Devin install your fork or open pull requests on it:

1. In Devin, open **Settings → Connections → GitHub** and click **Add Connection**.
2. Authorize the Devin GitHub app for your account (or organization) and pick which repositories it can access. Include your fork.

See [GitHub integration](https://docs.devin.ai/integrations/gh). Creating the connection for a GitHub organization needs an admin of that organization; a personal account works too.

If you use Devin through a company or enterprise account, each Devin organization also has its own repository list. Check that your fork appears under **Settings → (your organization) → Repositories**. If it doesn't, an admin adds it with **repositories permissions** on that page.

### 3. Set up email (for automations)

The report is emailed through [Resend](https://resend.com), which has a free tier.

1. Create a Resend account and an API key at [resend.com/api-keys](https://resend.com/api-keys).
2. In Devin, open the **Secrets** page and add a secret named `RESEND_API_KEY` with that key. See [Secrets](https://docs.devin.ai/product-guides/secrets).
3. Optional: to send to an address other than the one you signed up to Resend with, [verify a domain in Resend](https://resend.com/domains) and add a second secret, `RESEND_FROM`, such as `iphone-check@yourdomain.com`. Without it, mail is sent from `onboarding@resend.dev`, which Resend only delivers to your own Resend account's email address.

### 4. Install the skill

1. In Devin, open **Customize → Plugins → Add plugin → From repository**.
2. Enter `marklovestech/i-want-an-iphone-right-now` (or your fork) and install it. Install it for yourself, or for your whole Devin organization if others should get it too.

New sessions now have the `i-want-an-iphone-right-now` skill. See [Installing plugins](https://docs.devin.ai/product-guides/plugins#from-a-repository-a-zip-or-the-editor).

Automation sessions may not load a plugin installed from a repository, even when normal sessions do (see [Troubleshooting](#troubleshooting)). The automation prompt below links the skill's instructions on GitHub, so the run still works when that happens.

### 5. Run a check

Start a new Devin session and ask, for example:

> Check iPhone Duo pickup near 94108 on AT&T, 1TB and 2TB in both colors.

Devin replies with the stores and configs it's about to check. Say OK, and it sends back the table. You can name:

- **Where:** one or more zip codes, or "the Bay Area" (17 stores from San Francisco to San Jose and Santa Rosa).
- **What:** storage (256GB, 512GB, 1TB, 2TB) and color (Star White, Night Sky). Default: all 8 configs.
- **Carrier:** AT&T, T-Mobile, Verizon or unlocked. Default: unlocked.
- **Email:** "and email me at you@example.com".

### 6. Run it on a schedule

1. In Devin, open **Automations** in the sidebar and click **Create automation → Create**. See [Automations](https://docs.devin.ai/product-guides/automations#from-the-automations-page).
2. **Trigger:** choose **Schedule → Custom schedule** and set the time zone to the one your stores are in. To check hourly while stores are open (roughly 10am to 9pm) and every 4 hours overnight, enter this RRULE:
   ```
   FREQ=DAILY;BYHOUR=0,4,8,10,11,12,13,14,15,16,17,18,19,20,21;BYMINUTE=0
   ```
   Adjust the hours to your stores' hours; Apple lists them on each store's page.
3. **Action:** start a Devin session with a prompt like this, using your own settings:
   ```
   Use the i-want-an-iphone-right-now skill (if it is not loaded, follow
   https://github.com/marklovestech/i-want-an-iphone-right-now/blob/main/skills/i-want-an-iphone-right-now/SKILL.md)
   in unattended mode. Nobody is watching this session: don't ask questions or wait
   for confirmation; run once and stop.

   Check iPhone Duo pickup: zip 94108 (or: the bay-area region), carrier att,
   configs 1tb-white,1tb-night,2tb-white,2tb-night.
   Email the report to you@example.com.
   Never add anything to an Apple bag, sign in, or check out.
   ```
   Name the skill in plain text as above. Devin rejects an `@skills:` reference to a plugin skill in an automation prompt.
4. **Secrets:** the automation's sessions need `RESEND_API_KEY` (step 3). If the automation runs as you, your personal secrets are available to it.
5. **Network (optional):** if you turn on the automation's network policy, allow at least these hosts: `*.apple.com`, `*.cdn-apple.com` (Apple's site), `pypi.org`, `files.pythonhosted.org` (to install playwright), `api.resend.com` (email), and `github.com`, `raw.githubusercontent.com`, `git-manager.devin.ai` (to fetch the skill from GitHub).
6. Click **Create automation**. To try it right away, use **Run now** on the automation's page.

The maintainer's own live automation is mirrored in [`automation/`](automation/): [`automation.json`](automation/automation.json) holds its full settings (schedule, prompt, network allowlist, limits) and [`prompt.md`](automation/prompt.md) the same prompt as plain text. Copy them and change the region, carrier, configs and email to yours.

You get an email after every run: `IN STOCK: ...` when something is available, `No stock: ...` when not, and `Check FAILED` if Apple's site couldn't be read. To change the address, area or configs later, edit the automation's prompt.

**Cost:** each run is a separate Devin session, so the schedule above is about 15 sessions a day. Check your plan's usage, and pause or delete the automation once you have your iPhone.

## Troubleshooting

- **The automation's session says the plugin couldn't be loaded** (for example, "repository doesn't exist or authentication failed"), while normal sessions have the skill. We've seen this on Devin automation runs even with the repo granted to the organization and no network policy. The prompt above makes the run fall back to the skill's instructions on GitHub, and the check still completes.
- **A `Check FAILED` email followed by a normal report from the same run.** In a freshly started browser, Apple's first availability reply is often not the stock data. The script emails a failure, then the agent reloads the apple.com tab and retries once, and that retry sends the real report.
- **`Check FAILED` with nothing after it.** Apple's site couldn't be read even after the retry. The next scheduled run tries again. If it keeps failing, Apple may have changed the site and the script needs updating.

## Use it with Claude Code

```
/plugin marketplace add marklovestech/i-want-an-iphone-right-now
/plugin install i-want-an-iphone-right-now@i-want-an-iphone-right-now
```

Claude Code doesn't come with a browser, so start Chrome with a DevTools port and tell Claude to use it:

```
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/iphone-check-chrome
```

Then ask, for example: "Check iPhone Duo pickup near 94108, use --cdp http://localhost:9222". For email, set `RESEND_API_KEY` (and optionally `RESEND_FROM`) in your environment. Your mileage may vary.

## Run the script directly

```
pip install playwright
python3 skills/i-want-an-iphone-right-now/scripts/apple_pickup.py --zip 94108 --carrier att --configs 1tb-night,2tb-night
```

| Flag | Meaning |
|---|---|
| `--zip 94108,95014` | Check the ~12 stores nearest each zip (required unless `--region` is used) |
| `--region bay-area` | Check every store in a predefined region |
| `--carrier` | `att`, `tmobile`, `verizon` or `unlocked` (default) |
| `--configs` | Comma-separated: `256gb-white`, `256gb-night`, `512gb-white`, `512gb-night`, `1tb-white`, `1tb-night`, `2tb-white`, `2tb-night` (default: all) |
| `--list-stores` | Only list the stores that would be checked |
| `--email` | Email the report via Resend (needs `RESEND_API_KEY`) |
| `--cdp` | Chrome DevTools endpoint (default `http://localhost:29229`, Devin's browser) |

Tests: `python3 -m unittest discover -s tests`
