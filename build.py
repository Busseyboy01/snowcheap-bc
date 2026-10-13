#!/usr/bin/env python3
"""Render deals.json into a static site in docs/ (served by GitHub Pages)."""
import json, re, shutil, datetime as dt
from html import escape as e
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).parent; OUT = ROOT / "docs"
data = json.loads((ROOT / "deals.json").read_text())
S = data["site"]; BASE = S["base_url"].rstrip("/")
now = dt.datetime.now(ZoneInfo("America/Vancouver")); today = now.date()
D = lambda s: dt.date.fromisoformat(s) if s else None
slug = lambda s: re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

for d in data["deals"]:
    d["_exp"] = D(d.get("expiry_date")); d["_start"] = D(d.get("start_date"))
    d["_expired"] = bool(d["_exp"] and d["_exp"] < today)
    d["_days"] = (d["_exp"] - today).days if d["_exp"] else None
live = [d for d in data["deals"] if not d["_expired"]]
archive = sorted([d for d in data["deals"] if d["_expired"]], key=lambda d: d["_exp"], reverse=True)
urgency = lambda d: (d["_days"] if d["_days"] is not None else 9999)
live.sort(key=urgency)

CSS = """*{box-sizing:border-box}body{margin:0;font:16px/1.5 system-ui,sans-serif;color:#122;background:#f4f8fb}
header{background:#0b3d5c;color:#fff;padding:12px 16px}header a{color:#fff;text-decoration:none}nav{display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:6px;font-size:14px}
main{max-width:860px;margin:auto;padding:12px}h1{font-size:1.5rem}.card{background:#fff;border-radius:10px;padding:12px 14px;margin:10px 0;box-shadow:0 1px 3px #0002}
.card h3{margin:0 0 4px;font-size:1.05rem}.meta{font-size:13px;color:#456}.price{font-weight:700;color:#0a7a3d}.reg{text-decoration:line-through;color:#888;margin-left:6px}
.tag{display:inline-block;font-size:12px;background:#e3eef6;border-radius:4px;padding:1px 6px;margin-right:4px}.urgent{background:#ffe1e1;color:#a00}
.btn{display:inline-block;margin-top:6px;background:#0b6fa4;color:#fff;padding:6px 12px;border-radius:6px;text-decoration:none}footer{font-size:13px;color:#456;max-width:860px;margin:auto;padding:16px}
table{border-collapse:collapse;width:100%;background:#fff}td,th{padding:6px;border-bottom:1px solid #ddd;text-align:left}"""

NAV = [("index.html","Deals"),("deadlines.html","Deadlines"),("events.html","Swaps & events"),("gear.html","Gear"),("discounts.html","Discounts"),("resorts.html","Resorts"),("archive.html","Archive"),("advertise.html","Advertise")]

def page(path, title, desc, body, schema=None):
    ld = f'<script type="application/ld+json">{json.dumps(schema)}</script>' if schema else ""
    nav = "".join(f'<a href="{BASE}/{h}">{n}</a>' for h, n in NAV)
    html = f"""<!doctype html><html lang="en-CA"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}"><link rel="canonical" href="{BASE}/{path}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><style>{CSS}</style>{ld}</head><body>
<header><a href="{BASE}/index.html"><strong>❄ {e(S['name'])}</strong></a> <span style="font-size:13px">Cheap skiing in Vancouver &amp; BC</span><nav>{nav}</nav></header>
<main>{body}</main><footer><p>Last updated: {now:%B %-d, %Y %-I:%M %p} PT. Prices and dates are checked against official pages but can change — always confirm on the source before buying.</p>
<p><strong>Disclosure:</strong> some links may be affiliate links; we may earn a small commission at no extra cost to you. Listings are never paid placements unless marked “Sponsored”.</p></footer></body></html>"""
    p = OUT / path; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(html); PAGES.append(path)

def card(d):
    link = d.get("affiliate_url") or d["url"]; rel = "sponsored nofollow noopener" if d.get("affiliate_url") else "noopener"
    tags = f'<span class="tag">{e(d["category"])}</span>'
    if d["_expired"]: tags += '<span class="tag">expired</span>'
    elif d["_days"] is not None: tags += f'<span class="tag{" urgent" if d["_days"] <= 7 else ""}">{"ends today" if d["_days"]==0 else f"{d["_days"]} days left"}</span>'
    if d["_start"] and d["_start"] > today: tags += f'<span class="tag">starts {d["_start"]:%b %-d}</span>'
    reg = f'<span class="reg">{e(d["regular_price"])}</span>' if d.get("regular_price") else ""
    exp = f' · Expires {d["_exp"]:%a %b %-d, %Y}' if d["_exp"] else ""
    return f"""<div class="card"><h3>{e(d['title'])}</h3><div>{tags}</div><div><span class="price">{e(d['price'] or '')}</span>{reg}</div>
<div class="meta">{e(d['resort'])}{exp} · Verified {e(d['last_verified'])}</div><p>{e(d.get('notes') or '')}</p>
<a class="btn" href="{e(link)}" rel="{rel}" target="_blank">View deal</a></div>"""

def offer_schema(ds):
    return {"@context":"https://schema.org","@type":"ItemList","itemListElement":[{"@type":"ListItem","position":i+1,"item":{"@type":"Offer","name":d["title"],"url":d["url"],
        **({"priceCurrency":"CAD","price":re.sub(r"[^0-9.]","",d["price"])} if re.fullmatch(r"(from )?\$[0-9,]+(\.\d\d)?",d["price"] or "") else {}),
        **({"validThrough":d["expiry_date"]} if d["expiry_date"] else {}),"seller":{"@type":"Organization","name":d["resort"]}}} for i,d in enumerate(ds)]}

if OUT.exists(): shutil.rmtree(OUT)
OUT.mkdir(); PAGES = []
lst = lambda ds: "".join(map(card, ds)) or "<p>Nothing here right now — check back tomorrow.</p>"
cat = lambda c: [d for d in live if d["category"] == c]

page("index.html", f"{S['name']} – Vancouver & BC ski deals, early birds and swaps",
     "Daily-updated BC ski deals: season pass early-bird deadlines, lift ticket discounts, ski swaps and gear sales for Vancouver and BC.",
     f"<h1>BC ski & winter deals, most urgent first</h1><p>{len(live)} live deals, re-checked daily against official pages.</p>{lst(live)}", offer_schema(live))

dl = sorted([d for d in live if d["_exp"]], key=urgency)
rows = "".join(f'<tr><td><strong>{d["_days"]}</strong> days</td><td>{d["_exp"]:%a %b %-d}</td><td><a href="{e(d.get("affiliate_url") or d["url"])}">{e(d["title"])}</a></td></tr>' for d in dl)
page("deadlines.html", "BC ski pass deadline countdown – prices go up soon", "Countdown to every BC season pass early-bird and pre-season price deadline.",
     f"<h1>Deadline countdown</h1><table><tr><th>Left</th><th>Ends</th><th>Deal</th></tr>{rows}</table>", offer_schema(dl))

ev = sorted(cat("swaps and events"), key=lambda d: d["_start"] or d["_exp"] or today)
evs = {"@context":"https://schema.org","@graph":[{"@type":"Event","name":d["title"],"startDate":d["start_date"] or d["expiry_date"],"endDate":d["expiry_date"],"location":{"@type":"Place","name":d["resort"],"address":d["resort"]},"url":d["url"],"eventStatus":"https://schema.org/EventScheduled"} for d in ev if d["start_date"] or d["expiry_date"]]}
page("events.html", "Vancouver ski swaps & winter events calendar", "Upcoming ski and snowboard swaps and winter events in Vancouver and the Lower Mainland.", f"<h1>Swaps & events calendar</h1>{lst(ev)}", evs)
page("gear.html", "Ski & snowboard gear sales in BC", "Current ski and snowboard gear sales from BC and Canadian retailers.", f"<h1>Gear deals</h1>{lst(cat('gear sales'))}", offer_schema(cat('gear sales')))
page("discounts.html", "Student, kids & senior ski discounts in BC", "Cheaper skiing for students, kids and seniors at BC resorts.", f"<h1>Student, kids & senior discounts</h1>{lst(cat('discounts for students/kids/seniors'))}", offer_schema(cat('discounts for students/kids/seniors')))
page("archive.html", "Expired BC ski deals archive", "Past BC ski deals and early-bird prices, useful for planning next season.", f"<h1>Expired deals archive</h1><p>Handy for knowing what to expect next year.</p>{lst(archive)}")

resorts = sorted({d["resort"] for d in data["deals"] if d["category"] not in ("gear sales", "swaps and events")})
links = ""
for r in resorts:
    rl = [d for d in live if d["resort"] == r]; ra = [d for d in archive if d["resort"] == r]
    page(f"resort/{slug(r)}.html", f"Cheapest way to ski {r} this season (2026/27)", f"All current {r} deals: early-bird season passes, discount tickets and kids/student offers, checked daily.",
         f"<h1>Cheapest way to ski {e(r)} this season</h1><p>Live offers, most urgent first:</p>{lst(rl)}" + (f"<h2>Expired</h2>{lst(ra)}" if ra else ""), offer_schema(rl))
    links += f'<li><a href="{BASE}/resort/{slug(r)}.html">Cheapest way to ski {e(r)}</a> ({len(rl)} live)</li>'
page("resorts.html", "BC ski resorts – cheapest way to ski each one", "Resort-by-resort guide to the cheapest lift tickets and passes in BC.", f"<h1>Resorts</h1><ul>{links}</ul>")
page("advertise.html", f"Advertise / sponsor {S['name']}", "Reach Vancouver and BC skiers looking for deals. Sponsorship and advertising options.",
     f"<h1>Advertise or sponsor this site</h1><p>{e(S['name'])} reaches budget-minded skiers and snowboarders in Vancouver and across BC during the key buying window for passes and gear.</p><ul><li>Sponsored deal listing (clearly marked)</li><li>Site-wide sponsor banner</li><li>Swap / event promotion</li></ul><p>Contact: <strong>{e(S['contact_email'])}</strong></p>")

(OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
(OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(f"<url><loc>{BASE}/{p}</loc><lastmod>{today}</lastmod></url>" for p in PAGES) + "</urlset>")
(OUT / ".nojekyll").write_text("")
print(f"Built {len(PAGES)} pages: {len(live)} live, {len(archive)} archived")
