#!/usr/bin/env python3
"""
Store MARS USA Mfg Oct 18 lead list in Supabase.
"""
import os
import sys
import csv
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any
import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://npkdhahdvilcctjwzdlf.supabase.co")
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"].strip()

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def normalize_linkedin(url: str) -> str:
    """Normalize LinkedIn URL for matching."""
    if not url:
        return ""
    url = url.lower().strip()
    if "/in/" in url:
        parts = url.split("/in/")
        if len(parts) > 1:
            slug = parts[1].rstrip("/").split("/")[0].split("?")[0]
            return f"https://www.linkedin.com/in/{slug}"
    return url

def read_valid_csv() -> List[Dict[str, Any]]:
    """Read the valid leads CSV."""
    leads = []
    with open("/workspace/zs-ops2/runs/mars-2026-10-18/mars_usa_valid.csv", "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            leads.append(row)
    return leads

def read_catchall_csv() -> List[Dict[str, Any]]:
    """Read the catch-all leads CSV."""
    leads = []
    with open("/workspace/zs-ops2/runs/mars-2026-10-18/mars_usa_catchall.csv", "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            leads.append(row)
    return leads

def read_stats() -> Dict[str, Any]:
    """Read the enrichment stats."""
    with open("/workspace/zs-ops2/runs/mars-2026-10-18/enrichment_stats.json", "r") as f:
        return json.load(f)

def read_report() -> Dict[str, Any]:
    """Read the build report."""
    with open("/workspace/zs-ops2/runs/mars-2026-10-18/report.json", "r") as f:
        return json.load(f)

def create_list_record(stats: Dict, report: Dict, list_id: str) -> Dict[str, Any]:
    """Create the lead_lists record."""
    total_cost = report["cost_by_provider"].get("icypeas", 0) + stats["total_spent_usd"]
    
    # Calculate segment breakdown
    seg_counts = {}
    for seg, data in report["segments"].items():
        seg_counts[seg] = {"clean": data["clean"]}
    
    return {
        "list_id": list_id,
        "client": "MARS",
        "list_name": "MARS USA Mfg Oct 18",
        "source": "Icypeas via treg.to",
        "status": "enriched",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_leads": stats["total_leads"],
        "enriched_count": stats["mv_valid"] + stats["mv_catchall"],
        "ready_count": stats["mv_valid"],
        "failed_count": stats["mv_invalid"],
        "skipped_count": 0,
        "estimated_cost_usd": 3.65,
        "actual_cost_usd": round(total_cost, 2),
        "cost_cap_usd": 5.00,
        "enrichment_started_at": datetime.now(timezone.utc).isoformat(),
        "enrichment_completed_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "segments": seg_counts,
            "emails_by_source": {
                "cache": stats["cache_hits"],
                "pattern": stats["pattern_found"],
                "contactout": stats["contactout_found"],
                "blitz": stats["blitz_found"],
                "quickenrich": stats["quickenrich_found"],
                "trykitt": stats["trykitt_found"]
            },
            "mv_status": {
                "valid": stats["mv_valid"],
                "catchall": stats["mv_catchall"],
                "invalid": stats["mv_invalid"]
            },
            "cost_by_provider": {
                "icypeas": report["cost_by_provider"].get("icypeas", 0),
                **stats["cost_by_provider"]
            }
        },
        "run_report": report
    }

def upsert_to_lead_db(lead: Dict[str, Any]) -> int:
    """Upsert a lead to the Lead Database table and return the lead_id."""
    linkedin_norm = normalize_linkedin(lead["linkedin"])
    
    # First try to find existing lead by LinkedIn
    if linkedin_norm:
        search_url = f"{SUPABASE_URL}/rest/v1/Lead%20Database?Linkedin=eq.{linkedin_norm}&select=id"
        resp = requests.get(search_url, headers=HEADERS)
        if resp.status_code == 200 and resp.json():
            lead_id = resp.json()[0]["id"]
            # Update the lead
            update_url = f"{SUPABASE_URL}/rest/v1/Lead%20Database?id=eq.{lead_id}"
            update_data = {
                "First Name": lead["first"],
                "Last Name": lead["last"],
                "Email": lead["email"],
                "Linkedin": lead["linkedin"],
                "Company Name": lead["company"],
                "Website": lead["domain"],
                "company_size": lead["size"],
                "company_description": "",
                "location": "",
                "email_source": lead["email_source"],
                "email_status": lead["mv_status"],
                "enrichment_updated_at": datetime.now(timezone.utc).isoformat()
            }
            resp = requests.patch(update_url, headers=HEADERS, json=update_data)
            if resp.status_code in [200, 204]:
                return lead_id
    
    # If not found by LinkedIn, try email
    if lead["email"]:
        search_url = f"{SUPABASE_URL}/rest/v1/Lead%20Database?Email=eq.{lead['email']}&select=id"
        resp = requests.get(search_url, headers=HEADERS)
        if resp.status_code == 200 and resp.json():
            lead_id = resp.json()[0]["id"]
            # Update the lead
            update_url = f"{SUPABASE_URL}/rest/v1/Lead%20Database?id=eq.{lead_id}"
            update_data = {
                "First Name": lead["first"],
                "Last Name": lead["last"],
                "Email": lead["email"],
                "Linkedin": lead["linkedin"],
                "Company Name": lead["company"],
                "Website": lead["domain"],
                "company_size": lead["size"],
                "company_description": "",
                "location": "",
                "email_source": lead["email_source"],
                "email_status": lead["mv_status"],
                "enrichment_updated_at": datetime.now(timezone.utc).isoformat()
            }
            resp = requests.patch(update_url, headers=HEADERS, json=update_data)
            if resp.status_code in [200, 204]:
                return lead_id
    
    # Insert new lead
    insert_url = f"{SUPABASE_URL}/rest/v1/Lead%20Database"
    insert_data = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "First Name": lead["first"],
        "Last Name": lead["last"],
        "Email": lead["email"],
        "Linkedin": lead["linkedin"],
        "Company Name": lead["company"],
        "Website": lead["domain"],
        "company_size": lead["size"],
        "company_description": "",
        "location": "",
        "email_source": lead["email_source"],
        "email_status": lead["mv_status"],
        "enrichment_updated_at": datetime.now(timezone.utc).isoformat()
    }
    resp = requests.post(insert_url, headers=HEADERS, json=insert_data)
    if resp.status_code in [200, 201]:
        return resp.json()[0]["id"]
    else:
        print(f"Error inserting lead {lead['email']}: {resp.status_code} {resp.text}")
        return None

def upsert_to_pipeline_leads(lead: Dict[str, Any], is_catchall: bool = False):
    """Upsert a lead to pipeline_leads."""
    linkedin_norm = normalize_linkedin(lead["linkedin"])
    
    # Check if already exists by batch_id + linkedin
    if linkedin_norm:
        search_url = f"{SUPABASE_URL}/rest/v1/pipeline_leads?batch_id=eq.mars-usa-20261018&linkedin=eq.{linkedin_norm}&select=id"
        resp = requests.get(search_url, headers=HEADERS)
        if resp.status_code == 200 and resp.json():
            # Already exists, skip
            return
    
    # Check by batch_id + email
    if lead["email"]:
        search_url = f"{SUPABASE_URL}/rest/v1/pipeline_leads?batch_id=eq.mars-usa-20261018&email=eq.{lead['email']}&select=id"
        resp = requests.get(search_url, headers=HEADERS)
        if resp.status_code == 200 and resp.json():
            # Already exists, skip
            return
    
    # Insert new
    insert_url = f"{SUPABASE_URL}/rest/v1/pipeline_leads"
    insert_data = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "batch_id": "mars-usa-20261018",
        "source_run": "mars-2026-10-18",
        "client": "MARS",
        "campaign_id": "MARS_USA_MFG_OCT18",
        "offer": "",
        "first_name": lead["first"],
        "last_name": lead["last"],
        "title": lead.get("title", ""),
        "email": lead["email"],
        "linkedin": lead["linkedin"],
        "company_name": lead["company"],
        "website": lead["domain"],
        "company_domain": lead["domain"],
        "employees": lead["size"],
        "country": "USA",
        "mv_status": lead["mv_status"],
        "email_source": lead["email_source"],
        "already_in_lead_db": False,
        "plusvibe_excluded": is_catchall,
        "plusvibe_exclude_reason": "catch-all email" if is_catchall else None,
        "plusvibe_ready": not is_catchall,
        "handoff_status": "ready" if not is_catchall else "excluded",
        "raw": {
            "industry": lead.get("industry", ""),
            "segment": lead.get("segment", "")
        },
        "company_description": "",
        "company_industry": lead.get("industry", ""),
        "company_keywords": "",
        "company_address": "",
        "location": "",
        "company_size": lead["size"]
    }
    resp = requests.post(insert_url, headers=HEADERS, json=insert_data)
    if resp.status_code not in [200, 201]:
        print(f"Error inserting to pipeline_leads {lead['email']}: {resp.status_code} {resp.text}")

def insert_list_member(list_id: str, lead_id: int, cost_micro: int):
    """Insert a lead_list_members record."""
    # Check if already exists
    search_url = f"{SUPABASE_URL}/rest/v1/lead_list_members?list_id=eq.{list_id}&lead_id=eq.{lead_id}&select=list_id"
    resp = requests.get(search_url, headers=HEADERS)
    if resp.status_code == 200 and resp.json():
        # Already exists
        return
    
    insert_url = f"{SUPABASE_URL}/rest/v1/lead_list_members"
    insert_data = {
        "list_id": list_id,
        "lead_id": lead_id,
        "added_at": datetime.now(timezone.utc).isoformat(),
        "enrichment_status": "enriched",
        "enrichment_attempted_at": datetime.now(timezone.utc).isoformat(),
        "enrichment_completed_at": datetime.now(timezone.utc).isoformat(),
        "cost_micro": cost_micro
    }
    resp = requests.post(insert_url, headers=HEADERS, json=insert_data)
    if resp.status_code not in [200, 201]:
        print(f"Error inserting list member {lead_id}: {resp.status_code} {resp.text}")

def main():
    print("Starting Supabase storage...")
    
    # Generate list_id
    list_id = str(uuid.uuid4())
    print(f"Generated list_id: {list_id}")
    
    # Read data
    stats = read_stats()
    report = read_report()
    valid_leads = read_valid_csv()
    catchall_leads = read_catchall_csv()
    
    print(f"Read {len(valid_leads)} valid leads and {len(catchall_leads)} catch-all leads")
    
    # Step 1: Insert list record
    print("\n1. Inserting lead_lists record...")
    list_record = create_list_record(stats, report, list_id)
    list_url = f"{SUPABASE_URL}/rest/v1/lead_lists"
    resp = requests.post(list_url, headers=HEADERS, json=list_record)
    if resp.status_code in [200, 201]:
        print(f"✓ Created list record: {list_id}")
    else:
        print(f"✗ Error creating list: {resp.status_code} {resp.text}")
        sys.exit(1)
    
    # Step 2 & 3: Upsert to Lead Database and link members
    print("\n2. Upserting valid leads to Lead Database and linking members...")
    for i, lead in enumerate(valid_leads, 1):
        if i % 50 == 0:
            print(f"  Processed {i}/{len(valid_leads)} valid leads...")
        lead_id = upsert_to_lead_db(lead)
        if lead_id:
            # Cost estimate: ~$0.0018 per MV call
            cost_micro = 1800
            insert_list_member(list_id, lead_id, cost_micro)
    
    print(f"✓ Processed all {len(valid_leads)} valid leads")
    
    print("\n3. Upserting catch-all leads to Lead Database and linking members...")
    for i, lead in enumerate(catchall_leads, 1):
        if i % 50 == 0:
            print(f"  Processed {i}/{len(catchall_leads)} catch-all leads...")
        lead_id = upsert_to_lead_db(lead)
        if lead_id:
            cost_micro = 1800
            insert_list_member(list_id, lead_id, cost_micro)
    
    print(f"✓ Processed all {len(catchall_leads)} catch-all leads")
    
    # Step 4: Upsert to pipeline_leads
    print("\n4. Upserting to pipeline_leads...")
    for i, lead in enumerate(valid_leads, 1):
        if i % 50 == 0:
            print(f"  Processed {i}/{len(valid_leads)} valid pipeline leads...")
        upsert_to_pipeline_leads(lead, is_catchall=False)
    
    for i, lead in enumerate(catchall_leads, 1):
        if i % 50 == 0:
            print(f"  Processed {i}/{len(catchall_leads)} catch-all pipeline leads...")
        upsert_to_pipeline_leads(lead, is_catchall=True)
    
    print(f"✓ Processed all {len(valid_leads) + len(catchall_leads)} pipeline leads")
    
    print(f"\n✓ All done! List ID: {list_id}")
    
    # Write list_id to file for reference
    with open("/workspace/zs-ops2/runs/mars-2026-10-18/list_id.txt", "w") as f:
        f.write(list_id)

if __name__ == "__main__":
    main()
