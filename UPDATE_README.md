# SnowCheap BC – daily update procedure

Repo: https://github.com/Busseyboy01/snowcheap-bc · Live: https://busseyboy01.github.io/snowcheap-bc/
Site is built from `deals.json` by `build.py` into `docs/` (GitHub Pages serves `main:/docs`). No GitHub Actions.

## Rules
- Never invent prices or dates. Every value must be visible on the official `source_url` today.
- Respect robots.txt (`update.py` checks it). Do not use MEC (robots.txt disallows all).
- Keep `affiliate_url` empty until a real affiliate link exists; the template uses it automatically when filled.

- Deals with `manual_check: true` are on JavaScript-only pages. update.py lists them under **Needs browser check**: open each in a browser, then confirm the prices and bump `last_verified`.

## Steps (once a day)
1. `cd /workspace/skideals && git pull`
2. `python3 update.py` → prints and saves `reports/YYYY-MM-DD.md`.
3. For each **Flagged** item, open the `source_url` (curl/WebFetch) and decide:
   - Price/date changed → edit the deal's `price`, `regular_price`, `expiry_date`, `notes`, and update its `check` list to the new strings.
   - Offer gone → set `expiry_date` to yesterday (it moves to the archive) — do not delete it.
   - Fetch failed → retry once with curl; if still failing, leave as is and note it.
4. For every deal you confirmed, set `last_verified` to today (YYYY-MM-DD). Deals that passed update.py with all check strings present can be bumped too.
5. Optionally add new deals (search resort early-bird pages, ski swaps, retailer sale pages). Required fields: id (unique slug), title, category (one of: `lift tickets/passes`, `early-bird deadlines`, `swaps and events`, `gear sales`, `discounts for students/kids/seniors`), resort, price, regular_price (or null), url, source_url, start_date, expiry_date (or null), last_verified, notes, affiliate_url (""), check (list of exact strings on the source page).
6. `python3 -m json.tool deals.json >/dev/null && python3 build.py`
7. `git add -A && git commit -m "Daily update $(date +%F)" && git push`
8. Wait ~1 min, then `curl -s https://busseyboy01.github.io/snowcheap-bc/ | grep "Last updated"` to confirm the live site shows today.
9. Report: counts of OK/flagged/expired/new deals and any edits made.

Expired deals (expiry_date < today, Pacific time) are archived automatically on every build, so rebuild daily even if nothing changed.
