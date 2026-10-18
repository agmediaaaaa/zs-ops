#!/usr/bin/env python3
"""Retry MV verification on enriched leads with correct endpoint."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import csv
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import gws_icypeas_sheet2 as base

OUT_DIR = Path(__file__).parent.parent / "runs" / "mars-2026-10-18"
LEADS_FILE = OUT_DIR / "leads_pre_enrich.jsonl"

# Remaining budget
_spent_micro = 0
_cap_micro = int(2.86 * 1_000_000)  # $5.00 - $1.05 - $1.09 = $2.86
_stop_spend = False
_lock = threading.Lock()

stats = {
    "mv_calls": 0,
    "mv_valid": 0,
    "mv_catchall": 0,
    "mv_invalid": 0,
    "cost_usd": 0.0,
}


def under_cap(need_micro: int = 0) -> bool:
    with _lock:
        if _stop_spend:
            return False
        ok = _spent_micro + need_micro < _cap_micro
        if not ok:
            print(f"\n⚠️  SPEND CAP: ${_spent_micro/1_000_000:.2f}")
        return ok


def charge(cost_micro: int):
    global _spent_micro
    if cost_micro <= 0:
        return
    with _lock:
        _spent_micro += cost_micro


def mv_verify(email: str) -> str:
    if not under_cap(1800):
        return "unknown"
    
    try:
        data, meta = base.treg("GET", "/call/millionverifier.people.email.verify",
                              query={"email": email}, timeout=20, retries=2)
        charge(meta.get("cost_micro", 0))
        
        if isinstance(data, dict):
            return data.get("result", "unknown").lower()
    except Exception as e:
        if "429" not in str(e):
            print(f"MV error for {email}: {str(e)[:100]}")
    return "unknown"


def main():
    base.TOKEN = base.load_treg_token()
    
    print("Loading enriched leads...")
    leads = [json.loads(line) for line in LEADS_FILE.read_text().strip().split("\n")]
    
    # Filter to only leads with emails
    with_emails = [l for l in leads if l.get("email") and "@" in l["email"]]
    print(f"Found {len(with_emails)} leads with emails")
    
    print(f"Starting MV verification (budget: ${_cap_micro/1_000_000:.2f})...")
    
    verified = []
    with ThreadPoolExecutor(30) as pool:
        def verify_one(lead):
            email = lead["email"]
            result = mv_verify(email)
            lead["mv_status"] = result
            
            stats["mv_calls"] += 1
            if result in {"ok", "valid", "deliverable"}:
                stats["mv_valid"] += 1
            elif result in {"accept_all", "catch_all", "catchall"}:
                stats["mv_catchall"] += 1
            else:
                stats["mv_invalid"] += 1
            
            return lead
        
        futures = {pool.submit(verify_one, lead): lead for lead in with_emails}
        
        for i, future in enumerate(as_completed(futures)):
            try:
                result = future.result()
                verified.append(result)
                
                if (i + 1) % 50 == 0:
                    print(f"  Progress: {i + 1}/{len(with_emails)} | Valid: {stats['mv_valid']} | Catch-all: {stats['mv_catchall']} | Invalid: {stats['mv_invalid']}")
                    
                    if _stop_spend:
                        print("  Cancelling (cap reached)")
                        for f in futures:
                            f.cancel()
                        break
            except Exception as e:
                print(f"  Error: {e}")
                verified.append(futures[future])
    
    # Add back leads without emails
    no_emails = [l for l in leads if not l.get("email") or "@" not in l["email"]]
    for lead in no_emails:
        lead["mv_status"] = "no_email"
        verified.append(lead)
    
    # Write CSVs
    valid = [l for l in verified if l.get("mv_status") in {"ok", "valid", "deliverable"}]
    catchall = [l for l in verified if l.get("mv_status") in {"accept_all", "catch_all", "catchall"}]
    
    def write_csv(leads, filename):
        if not leads:
            return
        path = OUT_DIR / filename
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "first", "last", "title", "company", "domain", "linkedin",
                "email", "email_source", "mv_status", "size", "industry", "segment"
            ])
            writer.writeheader()
            for lead in leads:
                writer.writerow({
                    "first": lead.get("first", ""),
                    "last": lead.get("last", ""),
                    "title": lead.get("title", ""),
                    "company": lead.get("company", ""),
                    "domain": lead.get("domain", ""),
                    "linkedin": lead.get("linkedin", ""),
                    "email": lead.get("email", ""),
                    "email_source": lead.get("email_source", ""),
                    "mv_status": lead.get("mv_status", ""),
                    "size": lead.get("size", ""),
                    "industry": lead.get("industry", ""),
                    "segment": lead.get("segment", ""),
                })
        print(f"Wrote {len(leads)} leads to {path}")
    
    write_csv(valid, "mars_usa_valid.csv")
    write_csv(catchall, "mars_usa_catchall.csv")
    
    stats["cost_usd"] = _spent_micro / 1_000_000
    
    print(f"\n{'=' * 80}")
    print("MV VERIFICATION COMPLETE")
    print('=' * 80)
    print(f"MV calls: {stats['mv_calls']}")
    print(f"Valid: {stats['mv_valid']}")
    print(f"Catch-all: {stats['mv_catchall']}")
    print(f"Invalid: {stats['mv_invalid']}")
    print(f"Cost: ${stats['cost_usd']:.2f}")
    
    # Save updated stats
    stats_file = OUT_DIR / "mv_retry_stats.json"
    stats_file.write_text(json.dumps(stats, indent=2))
    print(f"Stats: {stats_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
