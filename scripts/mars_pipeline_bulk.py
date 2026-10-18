#!/usr/bin/env python3
"""Bulk-insert remaining MARS leads into pipeline_leads (idempotent per batch_id+email)."""
import os, csv
from datetime import datetime, timezone
import requests

URL = os.environ.get("SUPABASE_URL", "https://npkdhahdvilcctjwzdlf.supabase.co").strip()
KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"].strip()
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "Prefer": "return=minimal"}
BATCH = "mars-usa-20261018"
D = "/workspace/zs-ops2/runs/mars-2026-10-18/"

existing, off = set(), 0
while True:
    r = requests.get(f"{URL}/rest/v1/pipeline_leads?batch_id=eq.{BATCH}&select=email&limit=1000&offset={off}", headers=H)
    r.raise_for_status()
    rows = r.json()
    existing |= {x["email"].lower() for x in rows if x["email"]}
    if len(rows) < 1000:
        break
    off += 1000

now = datetime.now(timezone.utc).isoformat()
out = []
for fn, catch in (("mars_usa_valid.csv", False), ("mars_usa_catchall.csv", True)):
    for l in csv.DictReader(open(D + fn)):
        if l["email"].lower() in existing:
            continue
        existing.add(l["email"].lower())
        out.append({
            "batch_id": BATCH, "source_run": "mars-2026-10-18", "client": "MARS",
            "campaign_id": "MARS_USA_MFG_OCT18", "first_name": l["first"], "last_name": l["last"],
            "title": l.get("title", ""), "email": l["email"], "linkedin": l["linkedin"],
            "company_name": l["company"], "website": l["domain"], "company_domain": l["domain"],
            "employees": l["size"], "country": "USA", "mv_status": l["mv_status"],
            "email_source": l["email_source"], "already_in_lead_db": False,
            "plusvibe_excluded": catch, "plusvibe_exclude_reason": "catch-all email" if catch else None,
            "plusvibe_ready": not catch, "handoff_status": "excluded" if catch else "ready",
            "raw": {"industry": l.get("industry", ""), "segment": l.get("segment", "")},
            "company_industry": l.get("industry", ""), "company_size": l["size"],
        })
print("to insert:", len(out))
for i in range(0, len(out), 100):
    r = requests.post(f"{URL}/rest/v1/pipeline_leads", headers=H, json=out[i:i+100])
    print(i, r.status_code, r.text[:200] if r.status_code >= 300 else "")
