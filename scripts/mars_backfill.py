#!/usr/bin/env python3
"""
Backfill company_description, company_address and location for the MARS list in Supabase.

The first store scripts wrote empty strings for these fields because the parser dropped them.
This re-runs the same segment queries used for the extra-people run (about 1,260 rows) with the
fixed parser, then updates Lead Database and pipeline_leads by LinkedIn.
"""
import argparse
import json
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
import gws_icypeas_sheet2 as base
import mars_build as mb
import mars_extra as mx
import mars_extra_store as st

OUT = Path(__file__).parent.parent / "runs" / "mars-2026-10-18"
RUN_CAP_USD = 0.55


def li(u):
    return base.normalize_linkedin(u or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm-spend", type=float)
    args = ap.parse_args()
    if not args.confirm_spend or args.confirm_spend > RUN_CAP_USD:
        print(f"need --confirm-spend <= {RUN_CAP_USD}")
        return 1
    base.TOKEN = base.load_treg_token()
    bal = base.balance_usd()
    spent = mx.START_BALANCE - bal
    print(f"balance {bal:.4f}, spent {spent:.4f}; room under $5.00 cap: {5 - spent:.4f}")
    if 5 - spent < args.confirm_spend + 0.05:
        print("not enough room under the cap")
        return 1
    mb._cap_micro = int(args.confirm_spend * 1_000_000)

    filters = mb.load_filters()
    existing = mx.load_existing()
    domains = sorted({l["domain"] for l in existing})
    extra = [json.loads(l) for l in (OUT / "extra_pre_enrich.jsonl").read_text().split("\n") if l.strip()]
    jobs = mx.queries(filters, domains)

    info = {}
    with ThreadPoolExecutor(4) as pool:
        for res in pool.map(lambda j: mx.search(j[0], j[1], j[3]), jobs):
            for l in res:
                if l["li"] and l["li"] not in info:
                    info[l["li"]] = l
    cost = mb._spent_micro / 1_000_000
    print(f"pulled, search cost ${cost:.4f}, {len(info)} unique people")

    fallback = {l["li"]: l for l in existing + extra if l.get("li")}
    members = []
    off = 0
    while True:
        r = requests.get(
            f"{st.URL}/rest/v1/lead_list_members?list_id=eq.{st.LIST_ID}&select=lead_id&limit=1000&offset={off}", headers=st.H)
        r.raise_for_status()
        rows = r.json()
        members += [x["lead_id"] for x in rows]
        if len(rows) < 1000:
            break
        off += 1000
    ldb = {}
    for i in range(0, len(members), 100):
        ids = ",".join(str(x) for x in members[i:i + 100])
        for r in st.get(f"Lead%20Database?id=in.({ids})&select=id,Linkedin,Email"):
            ldb[r["id"]] = r

    def best(linkedin):
        k = li(linkedin)
        a, b = info.get(k), fallback.get(k)
        return {
            "location": (a or {}).get("location") or (b or {}).get("location") or "",
            "company_description": (a or {}).get("company_description") or "",
            "company_address": (a or {}).get("company_address") or "",
        }

    def upd_ldb(item):
        i, r = item
        v = best(r["Linkedin"])
        body = {k: v[k] for k in ("location", "company_description") if v[k]}
        if body:
            requests.patch(f"{st.URL}/rest/v1/Lead%20Database?id=eq.{i}",
                           headers=st.H | {"Prefer": "return=minimal"}, json=body, timeout=60).raise_for_status()
        return bool(body)

    def upd_pl(item):
        i, r = item
        v = best(r["Linkedin"])
        body = {k: v[k] for k in ("location", "company_description", "company_address") if v[k]}
        if body:
            q = urllib.parse.quote(r["Linkedin"], safe="")
            requests.patch(
                f"{st.URL}/rest/v1/pipeline_leads?batch_id=eq.{st.BATCH}&linkedin=eq.{q}",
                headers=st.H | {"Prefer": "return=minimal"}, json=body, timeout=60).raise_for_status()
        return bool(body)

    with ThreadPoolExecutor(12) as pool:
        a = sum(pool.map(upd_ldb, ldb.items()))
        b = sum(pool.map(upd_pl, ldb.items()))
    print(f"Lead Database rows updated: {a}; pipeline_leads rows updated: {b}; members: {len(ldb)}")
    (OUT / "backfill_stats.json").write_text(json.dumps(
        {"search_cost_usd": cost, "unique_people_pulled": len(info), "members": len(ldb),
         "lead_database_updated": a, "pipeline_leads_updated": b}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
