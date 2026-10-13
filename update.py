#!/usr/bin/env python3
"""Re-check every deal's source page and print a change report (does NOT edit deals.json unless --mark-expired).
Each deal's "check" list holds strings (prices/dates) that must still appear on source_url.
Usage: python3 update.py [--mark-expired]   -> writes report to reports/YYYY-MM-DD.md and stdout."""
import json, re, sys, html, urllib.request, urllib.robotparser, datetime as dt
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
ROOT = Path(__file__).parent; UA = "Mozilla/5.0 (X11; Linux x86_64) Chrome/120 SnowCheapBC-checker"
today = dt.datetime.now(ZoneInfo("America/Vancouver")).date()
data = json.loads((ROOT / "deals.json").read_text()); cache, robots = {}, {}

def allowed(url):
    host = urlparse(url).scheme + "://" + urlparse(url).netloc
    if host not in robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            txt = urllib.request.urlopen(urllib.request.Request(host + "/robots.txt", headers={"User-Agent": UA}), timeout=20).read().decode("utf-8", "ignore")
            rp.parse(txt.splitlines())
        except Exception: rp = None  # unreachable robots.txt -> treat as allowed, but note it
        robots[host] = rp
    return robots[host] is None or robots[host].can_fetch("*", url)

def fetch(url):
    if url not in cache:
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=25).read().decode("utf-8", "ignore")
            t = re.sub(r"(?s)<(script|style).*?</\1>", " ", raw); t = html.unescape(re.sub(r"<[^>]+>", " ", t))
            cache[url] = (None, re.sub(r"\s+", " ", t))
        except Exception as ex: cache[url] = (str(ex), "")
    return cache[url]

ok, flags, expired, manual = [], [], [], []
for d in data["deals"]:
    exp = dt.date.fromisoformat(d["expiry_date"]) if d.get("expiry_date") else None
    if exp and exp < today:
        expired.append(d)
        if "--mark-expired" in sys.argv: d["status"] = "expired"
        continue
    if exp and (exp - today).days <= 2: flags.append((d, f"expires soon ({exp})"))
    if d.get("manual_check"): manual.append(d); continue
    if not allowed(d["source_url"]): flags.append((d, "robots.txt now disallows source - remove or verify manually")); continue
    err, text = fetch(d["source_url"])
    if err: flags.append((d, f"fetch failed: {err}")); continue
    norm = lambda s: s.lower().replace(",", "")
    missing = [c for c in d.get("check", []) if norm(c) not in norm(text)]
    if missing:
        found = sorted(set(re.findall(r"\$\d[\d,]*", text)))[:15]
        flags.append((d, f"no longer found on page: {missing}. Prices now on page: {found}"))
    else:
        ok.append(d)

lines = [f"# Change report {today}", f"- OK (all check strings present): {len(ok)}", f"- Flagged: {len(flags)}", f"- Expired (auto-moved to archive by build.py): {len(expired)}", f"- Needs browser check (manual_check): {len(manual)}", ""]
lines += ["## Flagged - review manually"] + [f"- **{d['id']}**: {why}  \n  {d['source_url']}" for d, why in flags] + [""]
lines += ["## Expired"] + [f"- {d['id']} (expired {d['expiry_date']})" for d in expired] + [""]
lines += ["## Needs browser check (JS pages; verify in a browser, then bump last_verified)"] + [f"- {d['id']} (last verified {d['last_verified']})  \n  {d['source_url']}" for d in manual] + [""]
lines += ["## OK"] + [f"- {d['id']}" for d in ok]
rep = "\n".join(lines); (ROOT / "reports").mkdir(exist_ok=True); (ROOT / "reports" / f"{today}.md").write_text(rep); print(rep)
if "--mark-expired" in sys.argv: (ROOT / "deals.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))
