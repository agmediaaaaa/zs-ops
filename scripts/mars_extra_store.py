#!/usr/bin/env python3
"""Store the extra MARS people (valid + catch-all) in Supabase using bulk calls."""
import csv
import json
import os
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import requests

URL = os.environ.get("SUPABASE_URL", "https://npkdhahdvilcctjwzdlf.supabase.co").strip()
KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"].strip()
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
LIST_ID = "ed9fbb72-4b84-42c2-8dc8-f20f6dbc734a"
BATCH = "mars-usa-20261018"
D = Path(__file__).parent.parent / "runs" / "mars-2026-10-18"
NOW = datetime.now(timezone.utc).isoformat()


def li(u):
    u = (u or "").strip().lower().rstrip("/").split("?")[0]
    return u.replace("https://www.", "").replace("https://", "")


def get(path):
    r = requests.get(f"{URL}/rest/v1/{path}", headers=H, timeout=60)
    r.raise_for_status()
    return r.json()


def post(table, rows, rep=False):
    h = H | {"Prefer": "return=representation" if rep else "return=minimal"}
    r = requests.post(f"{URL}/rest/v1/{urllib.parse.quote(table)}", headers=h, json=rows, timeout=120)
    if r.status_code >= 300:
        raise RuntimeError(f"{table}: {r.status_code} {r.text[:300]}")
    return r.json() if rep else None


def find_existing(leads):
    """Map normalized linkedin / lowercase email -> Lead Database id."""
    found = {}
    for key, col, vals in (("li", "Linkedin", [l["linkedin"] for l in leads]),
                           ("em", "Email", [l["email"] for l in leads])):
        for i in range(0, len(vals), 40):
            inl = ",".join('"%s"' % v.replace('"', "") for v in vals[i:i + 40])
            q = f"Lead%20Database?{col}=in.({urllib.parse.quote(inl)})&select=id,Linkedin,Email"
            for r in get(q):
                if key == "li":
                    found[("li", li(r["Linkedin"]))] = r["id"]
                if r.get("Email"):
                    found[("em", r["Email"].lower())] = r["id"]
    return found


def ldb_row(l):
    return {"First Name": l["first"], "Last Name": l["last"], "Email": l["email"], "Linkedin": l["linkedin"],
            "Company Name": l["company"], "Website": l["domain"], "company_size": l["size"],
            "email_source": l["email_source"], "email_status": l["mv_status"], "enrichment_updated_at": NOW}


def main():
    valid = list(csv.DictReader(open(D / "mars_usa_extra_valid.csv")))
    catch = list(csv.DictReader(open(D / "mars_usa_extra_catchall.csv")))
    leads = valid + catch
    existing = find_existing(leads)

    ids, new = {}, []
    for l in leads:
        i = existing.get(("li", li(l["linkedin"]))) or existing.get(("em", l["email"].lower()))
        if i:
            ids[l["email"]] = i
            requests.patch(f"{URL}/rest/v1/Lead%20Database?id=eq.{i}", headers=H | {"Prefer": "return=minimal"},
                           json=ldb_row(l), timeout=60).raise_for_status()
        else:
            new.append(l)
    for i in range(0, len(new), 100):
        chunk = new[i:i + 100]
        rows = post("Lead Database", [ldb_row(l) | {"created_at": NOW} for l in chunk], rep=True)
        for l, r in zip(chunk, rows):
            ids[l["email"]] = r["id"]
    print(f"Lead Database: {len(new)} inserted, {len(leads) - len(new)} updated")

    have = {r["lead_id"] for r in get(f"lead_list_members?list_id=eq.{LIST_ID}&select=lead_id&limit=5000")}
    members = [{"list_id": LIST_ID, "lead_id": ids[l["email"]], "added_at": NOW, "enrichment_status": "enriched",
                "enrichment_attempted_at": NOW, "enrichment_completed_at": NOW, "cost_micro": 1800}
               for l in leads if ids[l["email"]] not in have]
    for i in range(0, len(members), 200):
        post("lead_list_members", members[i:i + 200])
    print("lead_list_members added:", len(members))

    have_em = {r["email"].lower() for r in get(f"pipeline_leads?batch_id=eq.{BATCH}&select=email&limit=5000") if r["email"]}
    rows = []
    for l, is_catch in [(x, False) for x in valid] + [(x, True) for x in catch]:
        if l["email"].lower() in have_em:
            continue
        rows.append({
            "batch_id": BATCH, "source_run": "mars-2026-10-18", "client": "MARS", "campaign_id": "MARS_USA_MFG_OCT18",
            "first_name": l["first"], "last_name": l["last"], "title": l["title"], "email": l["email"],
            "linkedin": l["linkedin"], "company_name": l["company"], "website": l["domain"],
            "company_domain": l["domain"], "employees": l["size"], "country": "USA", "mv_status": l["mv_status"],
            "email_source": l["email_source"], "already_in_lead_db": False, "plusvibe_excluded": is_catch,
            "plusvibe_exclude_reason": "catch-all email" if is_catch else None, "plusvibe_ready": not is_catch,
            "handoff_status": "excluded" if is_catch else "ready",
            "raw": {"industry": l["industry"], "segment": l["segment"], "extra_person": True},
            "company_industry": l["industry"], "company_size": l["size"]})
    for i in range(0, len(rows), 100):
        post("pipeline_leads", rows[i:i + 100])
    print("pipeline_leads added:", len(rows))


if __name__ == "__main__":
    main()
