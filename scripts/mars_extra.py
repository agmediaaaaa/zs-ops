#!/usr/bin/env python3
"""
MARS USA Mfg Oct 18 - additional people at companies already in the list.

Also adds the 200-499 band (operations titles), which the first run dropped
because the founder/owner title check was applied to it.

Removes the one-person-per-company rule: re-runs the approved segment/band
queries restricted to the 799 company domains already in the list, keeps every
matching person (dedupe by LinkedIn only), drops people already in the list,
applies the same hygiene/suppression, enriches and MV-verifies them.

Cap: this run may spend at most RUN_CAP_USD, which keeps the grand total
(3.20 already spent + this run) under the $5.00 hard cap.
"""
import argparse
import csv
import json
import re
import sys
import threading
import urllib.parse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import gws_icypeas_sheet2 as base
import mars_build as mb
import mars_enrich as me

OUT = Path(__file__).parent.parent / "runs" / "mars-2026-10-18"
START_BALANCE = 10.08418
ALREADY_SPENT = 3.1996
GRAND_CAP = 5.00
RUN_CAP_USD = 1.70
COST_PER_ROW = 0.00038
OPS_TITLE_RE = re.compile(
    r"plant\s+manager|director\s+of\s+operations|operations\s+director|general\s+manager|\bgm\b", re.I)
FIELDS = ["first", "last", "title", "company", "domain", "linkedin", "email",
          "email_source", "mv_status", "size", "industry", "segment"]


def load_existing():
    rows = [json.loads(l) for l in (OUT / "leads_pre_enrich.jsonl").read_text().split("\n") if l.strip()]
    return rows


def queries(filters, domains):
    batches = [domains[i:i + 200] for i in range(0, len(domains), 200)]
    jobs = []
    for seg in ["Seg1", "Seg2", "Seg3_A", "Seg4"]:
        for band in ["10-199", "200-499"]:
            q = mb.get_query(seg, band, filters)
            if band == "200-499":
                jobs.append((seg, band, 0, q))
                continue
            for i, b in enumerate(batches):
                jobs.append((seg, band, i, q | {"currentCompanyWebsite": {"include": b}}))
    return jobs


def free_count(q):
    data, _ = base.treg("POST", "/call/icypeas.people.search.count", {"query": q})
    if isinstance(data, dict):
        return int(data.get("total") or data.get("count") or 0)
    return 0


def search(seg, band, q):
    out, token, pages = [], None, 0
    while pages < 30:
        if not mb.under_cap(50_000):
            break
        body = {"query": q, "pagination": {"size": 100}}
        if token:
            body["pagination"]["token"] = token
        data, meta = base.treg("POST", "/call/icypeas.people.search", body=body, timeout=90)
        mb.charge(meta.get("cost_micro", 0), "icypeas")
        page = data.get("leads", []) if data else []
        if not page:
            break
        out.extend(page)
        pages += 1
        token = (data.get("pagination") or {}).get("token")
        if not token or len(page) < 100:
            break
    return [mb.parse_lead(r, seg, band) for r in out]


def hygiene_multi(leads, existing_li, existing_em):
    """Same as mars_build.hygiene minus the per-company dedupe; LinkedIn dedupe only."""
    clean, skips, seen = [], defaultdict(int), set(existing_li)
    for l in leads:
        if not l["first"] or not l["last"]:
            skips["no_name"] += 1; continue
        if not l["domain"] or "linkedin.com" in l["domain"]:
            skips["no_domain"] += 1; continue
        if l["band"] == "200-499":
            if not OPS_TITLE_RE.search(l["title"] or ""):
                skips["title"] += 1; continue
        elif not base.title_ok(l["title"], l["company"]):
            skips["title"] += 1; continue
        c = l["company"].lower()
        if "division of" in c or "subsidiary of" in c:
            skips["division_subsidiary"] += 1; continue
        r = mb.is_suppressed(l)
        if r:
            skips[f"suppressed_{r}"] += 1; continue
        if l["li"] and l["li"] in existing_li:
            skips["already_in_list"] += 1; continue
        if l["li"] and l["li"] in seen:
            skips["dupe_linkedin"] += 1; continue
        if l["li"]:
            seen.add(l["li"])
        clean.append(l)
    return clean, dict(skips)


def sb_cache(leads):
    """Lead Database lookup by LinkedIn, chunked; emails updated within 30 days are reused."""
    from datetime import datetime, timezone
    cached = {}
    urls = [l["linkedin"] for l in leads if l.get("linkedin")]
    for i in range(0, len(urls), 40):
        chunk = urls[i:i + 40]
        inlist = ",".join('"%s"' % u.replace('"', "") for u in chunk)
        try:
            rows = me.sb_request("GET", "Lead Database", query={
                "Linkedin": f"in.({inlist})", "select": "Linkedin,Email,email_status,enrichment_updated_at"}) or []
        except Exception as e:
            print("cache error:", str(e)[:120]); continue
        for r in rows:
            em = (r.get("Email") or "").strip().lower()
            ts = r.get("enrichment_updated_at")
            if em and "@" in em and ts:
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(ts.replace("Z", "+00:00"))).days
                if age <= 30:
                    cached[base.normalize_linkedin(r["Linkedin"])] = em
    print(f"Cache hits: {len(cached)} / {len(leads)}")
    return cached


def write(path, rows):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count-only", action="store_true")
    ap.add_argument("--confirm-spend", type=float)
    args = ap.parse_args()
    base.TOKEN = base.load_treg_token()
    mb.load_suppressions()
    filters = mb.load_filters()
    existing = load_existing()
    domains = sorted({l["domain"] for l in existing})
    existing_li = {l["li"] for l in existing if l.get("li")}
    jobs = queries(filters, domains)
    print(f"{len(existing)} existing leads, {len(domains)} domains, {len(jobs)} queries")

    bal = base.balance_usd()
    spent_so_far = START_BALANCE - bal
    print(f"treg balance ${bal:.4f}  (spent so far ${spent_so_far:.4f} of ${GRAND_CAP:.2f})")
    room = GRAND_CAP - spent_so_far
    run_cap = min(RUN_CAP_USD, room - 0.10)

    counts = {}
    with ThreadPoolExecutor(6) as pool:
        for j, c in zip(jobs, pool.map(lambda j: free_count(j[3]), jobs)):
            counts[(j[0], j[1], j[2])] = c
    total = sum(counts.values())
    est = total * COST_PER_ROW
    print(f"free count: {total} rows -> search est ${est:.3f}; run cap ${run_cap:.3f}")
    for k, v in sorted(counts.items()):
        if v:
            print("  ", k, v)
    if args.count_only:
        return 0
    if not args.confirm_spend or args.confirm_spend > run_cap + 1e-9:
        print(f"need --confirm-spend <= {run_cap:.2f}")
        return 1
    if est > run_cap * 0.6:
        print("search estimate too large relative to cap; aborting")
        return 1

    mb._cap_micro = int(args.confirm_spend * 1_000_000)
    me._cap_micro = mb._cap_micro
    me.sb_headers = lambda: {
        "apikey": base.os.environ["SUPABASE_SERVICE_ROLE_KEY"].strip(),
        "Authorization": "Bearer " + base.os.environ["SUPABASE_SERVICE_ROLE_KEY"].strip(),
        "Content-Type": "application/json"}
    me.check_cache = sb_cache

    raw = []
    todo = [j for j in jobs if counts[(j[0], j[1], j[2])] > 0]
    with ThreadPoolExecutor(4) as pool:
        for res in pool.map(lambda j: search(j[0], j[1], j[3]), todo):
            raw.extend(res)
    search_cost = mb._spent_micro / 1_000_000
    print(f"pulled {len(raw)} rows, search cost ${search_cost:.4f}")

    # segment priority for people who match several segments (LinkedIn dedupe only)
    raw.sort(key=lambda l: mb.SEG_PRIORITY[l["segment"]])
    clean, skips = hygiene_multi(raw, existing_li, set())
    print(f"after hygiene: {len(clean)} extra people; skips {skips}")
    (OUT / "extra_pre_enrich.jsonl").write_text("\n".join(json.dumps(l) for l in clean) + "\n")

    me._spent_micro = mb._spent_micro
    me.stats["cost_by_provider"]["icypeas"] += search_cost
    enriched = me.enrich_batch(clean, workers=20)
    verified = me.mv_batch(enriched, workers=30)

    ok = {"ok", "valid", "deliverable", "cached_valid"}
    ca = {"accept_all", "catch_all", "catchall"}
    valid = [l for l in verified if l.get("mv_status") in ok]
    catch = [l for l in verified if l.get("mv_status") in ca]
    write(OUT / "mars_usa_extra_valid.csv", valid)
    write(OUT / "mars_usa_extra_catchall.csv", catch)

    report = {
        "queries": len(todo), "rows_pulled": len(raw), "after_hygiene": len(clean), "skips": skips,
        "emails_found": sum(1 for l in verified if l.get("email")),
        "stats": me.stats, "valid": len(valid), "catchall": len(catch),
        "valid_by_segment": {s: sum(1 for l in valid if l["segment"] == s) for s in mb.SEG_PRIORITY},
        "valid_by_source": {s: sum(1 for l in valid if l.get("email_source") == s)
                            for s in {l.get("email_source") for l in valid}},
        "run_spent_usd": mb._spent_micro / 1_000_000 if mb._spent_micro > me._spent_micro else me._spent_micro / 1_000_000,
    }
    (OUT / "extra_report.json").write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
