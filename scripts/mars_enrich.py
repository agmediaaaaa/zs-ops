#!/usr/bin/env python3
"""
MARS enrichment pipeline: cache -> pattern -> ContactOut -> Blitz -> QE/TK -> MV

Takes leads_pre_enrich.jsonl and produces:
- mars_usa_valid.csv (MV-valid emails)
- mars_usa_catchall.csv (catch-all emails)
- Updated leads in Supabase
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import argparse
import csv
import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

import gws_icypeas_sheet2 as base

OUT_DIR = Path(__file__).parent.parent / "runs" / "mars-2026-10-18"
SUPABASE_URL = "https://npkdhahdvilcctjwzdlf.supabase.co"

# Remaining budget from search phase
REMAINING_CAP_USD = 3.95
_spent_micro = 0
_cap_micro = int(REMAINING_CAP_USD * 1_000_000)
_stop_spend = False
_lock = threading.Lock()

stats = {
    "total_leads": 0,
    "cache_hits": 0,
    "pattern_found": 0,
    "contactout_found": 0,
    "blitz_found": 0,
    "quickenrich_found": 0,
    "trykitt_found": 0,
    "mv_calls": 0,
    "mv_valid": 0,
    "mv_catchall": 0,
    "mv_invalid": 0,
    "cost_by_provider": defaultdict(float),
    "total_spent_usd": 0.0,
}


def under_cap(need_micro: int = 0) -> bool:
    """Check if under cap."""
    global _stop_spend
    with _lock:
        if _stop_spend:
            return False
        ok = _spent_micro + need_micro < _cap_micro
        if not ok:
            _stop_spend = True
            print(f"\n⚠️  SPEND CAP REACHED: ${_spent_micro/1_000_000:.2f}")
        return ok


def charge(cost_micro: int, provider: str):
    """Record cost."""
    global _spent_micro
    if cost_micro <= 0:
        return
    with _lock:
        _spent_micro += cost_micro
        stats["cost_by_provider"][provider] += cost_micro / 1_000_000


def sb_headers() -> dict:
    """Supabase headers."""
    key = base.os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def sb_request(method: str, table: str, body: Any | None = None, query: dict | None = None) -> Any:
    """Make Supabase request."""
    encoded = urllib.parse.quote(table, safe='')
    url = f"{SUPABASE_URL}/rest/v1/{encoded}"
    if query:
        url += "?" + urllib.parse.urlencode(query)
    
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=sb_headers(), method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        err = e.read().decode(errors="replace")
        raise RuntimeError(f"Supabase {method} {table}: {err[:200]}")


def check_cache(leads: list[dict]) -> dict:
    """Check Supabase cache for existing emails."""
    # Query Lead Database for emails by LinkedIn
    linkedin_urls = [lead["li"] for lead in leads if lead.get("li")]
    
    cached = {}
    if linkedin_urls:
        # Batch query (simplified - in production, handle large batches)
        try:
            results = sb_request("GET", "Lead Database", query={
                "Linkedin": f"in.({','.join(linkedin_urls[:100])})",
                "select": "Linkedin,Email,enrichment_updated_at"
            })
            
            if results:
                for row in results:
                    li = base.normalize_linkedin(row.get("Linkedin", ""))
                    email = (row.get("Email") or "").strip().lower()
                    updated = row.get("enrichment_updated_at")
                    
                    if email and "@" in email:
                        # Check if fresh (≤30 days)
                        try:
                            updated_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                            age_days = (datetime.now(timezone.utc) - updated_dt).days
                            if age_days <= 30:
                                cached[li] = email
                        except:
                            pass
        except Exception as e:
            print(f"Cache check error: {e}")
    
    print(f"Cache hits: {len(cached)} / {len(leads)}")
    return cached


def contactout_verify(email: str) -> str:
    """Verify email with ContactOut (free)."""
    try:
        data, meta = base.treg("GET", "/call/contactout.people.email.verify",
                              query={"email": email}, timeout=15, retries=1)
        charge(meta.get("cost_micro", 0), "contactout")
        
        if isinstance(data, dict):
            inner = data.get("data", data)
            status = str(inner.get("status") or inner.get("result") or "").lower()
            return status
    except Exception as e:
        if "429" in str(e):
            return "rate_limited"
        return "error"
    return "unknown"


def blitz_find(linkedin: str) -> str:
    """Find email with Blitz."""
    if not under_cap(500):  # ~$0.0005
        return ""
    
    url = linkedin if linkedin.startswith("http") else f"https://{linkedin}"
    try:
        data, meta = base.treg("POST", "/call/blitzapi.people.email.find",
                              {"person_linkedin_url": url}, timeout=40, retries=2)
        charge(meta.get("cost_micro", 0), "blitz")
        
        if isinstance(data, dict):
            email = data.get("email", "")
            if not email and isinstance(data.get("all_emails"), list):
                if data["all_emails"]:
                    email = (data["all_emails"][0] or {}).get("email", "")
            return (email or "").strip().lower()
    except Exception:
        pass
    return ""


def quickenrich_find(lead: dict) -> str:
    """Find email with QuickEnrich."""
    if not under_cap(5000):  # ~$0.005
        return ""
    
    query = {
        "first_name": lead["first"],
        "last_name": lead["last"],
        "company_url": lead["domain"]
    }
    if lead.get("linkedin"):
        li = lead["linkedin"]
        query["linkedin_url"] = li if li.startswith("http") else f"https://{li}"
    
    try:
        data, meta = base.treg("GET", "/call/quickenrich.people.email.find",
                              query=query, timeout=60, retries=2)
        charge(meta.get("cost_micro", 0), "quickenrich")
        
        if isinstance(data, dict):
            email = data.get("email", "")
            if not email:
                dd = data.get("data")
                if isinstance(dd, dict):
                    email = dd.get("email", "")
                elif isinstance(dd, list) and dd:
                    email = (dd[0] or {}).get("email", "")
            return (email or "").strip().lower()
    except Exception:
        pass
    return ""


def trykitt_find(lead: dict) -> str:
    """Find email with TryKitt."""
    if not under_cap(5000):  # ~$0.005
        return ""
    
    full_name = f"{lead['first']} {lead['last']}".strip()
    try:
        data, meta = base.treg("POST", "/call/trykitt.people.email.find",
                              {"domain": lead["domain"], "fullName": full_name, "realtime": True},
                              timeout=90, retries=2)
        charge(meta.get("cost_micro", 0), "trykitt")
        
        if isinstance(data, dict):
            email = data.get("email", "").strip().lower()
            if email and email != "no-results-found":
                return email
    except Exception:
        pass
    return ""


def mv_verify(email: str) -> str:
    """Verify with MailboxValidator."""
    if not under_cap(1800):  # ~$0.00178
        return "unknown"
    
    try:
        data, meta = base.treg("GET", "/call/millionverifier.people.email.verify",
                              query={"email": email}, timeout=20, retries=2)
        charge(meta.get("cost_micro", 0), "millionverifier")
        
        if isinstance(data, dict):
            result = data.get("result", "unknown").lower()
            return result
    except Exception as e:
        print(f"MV error for {email}: {e}")
    return "unknown"


def enrich_lead(lead: dict, cached: dict) -> dict:
    """Enrich one lead through the pipeline."""
    # Check cache
    if lead.get("li") and lead["li"] in cached:
        lead["email"] = cached[lead["li"]]
        lead["email_source"] = "cache"
        lead["email_status"] = "cached"
        stats["cache_hits"] += 1
        return lead
    
    # Generate pattern emails
    patterns = base.pattern_emails(lead["first"], lead["last"], lead["domain"])[:3]
    
    # Try pattern + ContactOut
    for pattern in patterns:
        status = contactout_verify(pattern)
        if status in {"valid", "ok", "deliverable", "smtp_valid", "good"}:
            lead["email"] = pattern
            lead["email_source"] = "pattern+contactout"
            lead["email_status"] = status
            stats["pattern_found"] += 1
            stats["contactout_found"] += 1
            return lead
        if status == "rate_limited":
            break
    
    # Try Blitz
    if lead.get("linkedin"):
        email = blitz_find(lead["linkedin"])
        if email and "@" in email:
            lead["email"] = email
            lead["email_source"] = "blitz"
            lead["email_status"] = "blitz"
            stats["blitz_found"] += 1
            return lead
    
    # Try QuickEnrich
    email = quickenrich_find(lead)
    if email and "@" in email:
        lead["email"] = email
        lead["email_source"] = "quickenrich"
        lead["email_status"] = "quickenrich"
        stats["quickenrich_found"] += 1
        return lead
    
    # Try TryKitt
    email = trykitt_find(lead)
    if email and "@" in email:
        lead["email"] = email
        lead["email_source"] = "trykitt"
        lead["email_status"] = "trykitt"
        stats["trykitt_found"] += 1
        return lead
    
    # No email found
    return lead


def enrich_batch(leads: list[dict], workers: int = 20) -> list[dict]:
    """Enrich leads concurrently."""
    print(f"\nEnriching {len(leads)} leads...")
    
    # Check cache first
    cached = check_cache(leads)
    
    enriched = []
    with ThreadPoolExecutor(workers) as pool:
        futures = {pool.submit(enrich_lead, lead, cached): lead for lead in leads}
        
        for i, future in enumerate(as_completed(futures)):
            try:
                result = future.result()
                enriched.append(result)
                
                if (i + 1) % 50 == 0:
                    print(f"  Progress: {i + 1}/{len(leads)} leads enriched")
                    
                    if _stop_spend:
                        print("  Cancelling remaining tasks (cap reached)")
                        for f in futures:
                            f.cancel()
                        break
            except Exception as e:
                lead = futures[future]
                print(f"  Error enriching {lead.get('first', '')} {lead.get('last', '')}: {e}")
                enriched.append(lead)
    
    return enriched


def mv_batch(leads: list[dict], workers: int = 30) -> list[dict]:
    """Run MV on all leads with emails."""
    print(f"\nRunning MailboxValidator on {len(leads)} leads...")
    
    verified = []
    with ThreadPoolExecutor(workers) as pool:
        def verify_one(lead):
            if not lead.get("email"):
                lead["mv_status"] = "no_email"
                return lead
            
            # Skip if from fresh cache
            if lead.get("email_source") == "cache":
                lead["mv_status"] = "cached_valid"
                stats["mv_valid"] += 1
                return lead
            
            mv_result = mv_verify(lead["email"])
            lead["mv_status"] = mv_result
            stats["mv_calls"] += 1
            
            if mv_result in {"ok", "valid", "deliverable"}:
                stats["mv_valid"] += 1
            elif mv_result in {"accept_all", "catch_all", "catchall"}:
                stats["mv_catchall"] += 1
            else:
                stats["mv_invalid"] += 1
            
            return lead
        
        futures = {pool.submit(verify_one, lead): lead for lead in leads}
        
        for i, future in enumerate(as_completed(futures)):
            try:
                result = future.result()
                verified.append(result)
                
                if (i + 1) % 50 == 0:
                    print(f"  MV progress: {i + 1}/{len(leads)}")
                    
                    if _stop_spend:
                        print("  Cancelling remaining MV calls (cap reached)")
                        for f in futures:
                            f.cancel()
                        break
            except Exception as e:
                lead = futures[future]
                print(f"  MV error for {lead.get('email', '')}: {e}")
                verified.append(lead)
    
    return verified


def write_csvs(leads: list[dict]):
    """Write valid and catch-all CSVs."""
    valid = [l for l in leads if l.get("mv_status") in {"ok", "valid", "deliverable", "cached_valid"}]
    catchall = [l for l in leads if l.get("mv_status") in {"accept_all", "catch_all", "catchall"}]
    
    # Valid CSV
    if valid:
        path = OUT_DIR / "mars_usa_valid.csv"
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "first", "last", "title", "company", "domain", "linkedin",
                "email", "email_source", "mv_status", "size", "industry", "segment"
            ])
            writer.writeheader()
            for lead in valid:
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
        print(f"\nWrote {len(valid)} valid leads to {path}")
    
    # Catch-all CSV
    if catchall:
        path = OUT_DIR / "mars_usa_catchall.csv"
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "first", "last", "title", "company", "domain", "linkedin",
                "email", "email_source", "mv_status", "size", "industry", "segment"
            ])
            writer.writeheader()
            for lead in catchall:
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
        print(f"Wrote {len(catchall)} catch-all leads to {path}")


def main():
    parser = argparse.ArgumentParser(description="MARS enrichment pipeline")
    parser.add_argument("--confirm-spend", type=float, metavar="USD",
                       help=f"Confirm spend up to ${REMAINING_CAP_USD:.2f}")
    parser.add_argument("--workers", type=int, default=20,
                       help="Concurrent workers (default: 20)")
    
    args = parser.parse_args()
    
    if not args.confirm_spend:
        print("MARS Enrichment Pipeline")
        print(f"Remaining budget: ${REMAINING_CAP_USD:.2f}")
        print()
        print(f"Run with: --confirm-spend {REMAINING_CAP_USD:.2f}")
        return 1
    
    if args.confirm_spend > REMAINING_CAP_USD:
        print(f"Error: Amount ${args.confirm_spend:.2f} > remaining ${REMAINING_CAP_USD:.2f}")
        return 1
    
    # Load token
    base.TOKEN = base.load_treg_token()
    
    print("=" * 80)
    print("MARS Enrichment Pipeline")
    print("=" * 80)
    
    # Load leads
    leads_file = OUT_DIR / "leads_pre_enrich.jsonl"
    if not leads_file.exists():
        print(f"Error: {leads_file} not found")
        return 1
    
    leads = [json.loads(line) for line in leads_file.read_text().strip().split("\n")]
    stats["total_leads"] = len(leads)
    print(f"Loaded {len(leads)} leads from {leads_file}")
    
    # Check balance
    try:
        bal = base.balance_usd()
        print(f"Treg balance: ${bal:.2f}")
    except Exception as e:
        print(f"Balance check error: {e}")
        bal = 0.0
    print()
    
    # Enrich
    enriched = enrich_batch(leads, workers=args.workers)
    
    # MV verification
    verified = mv_batch(enriched, workers=30)
    
    # Write CSVs
    write_csvs(verified)
    
    # Final stats
    total_spent = _spent_micro / 1_000_000
    stats["total_spent_usd"] = total_spent
    
    print(f"\n{'=' * 80}")
    print("ENRICHMENT COMPLETE")
    print('=' * 80)
    print(f"\nSpent: ${total_spent:.2f} / ${REMAINING_CAP_USD:.2f} cap")
    print(f"\nEmail sources:")
    print(f"  Cache hits: {stats['cache_hits']}")
    print(f"  Pattern+ContactOut: {stats['contactout_found']}")
    print(f"  Blitz: {stats['blitz_found']}")
    print(f"  QuickEnrich: {stats['quickenrich_found']}")
    print(f"  TryKitt: {stats['trykitt_found']}")
    print(f"\nMailboxValidator:")
    print(f"  Valid: {stats['mv_valid']}")
    print(f"  Catch-all: {stats['mv_catchall']}")
    print(f"  Invalid: {stats['mv_invalid']}")
    print(f"\nCost by provider:")
    for prov, cost in sorted(stats["cost_by_provider"].items()):
        print(f"  {prov}: ${cost:.4f}")
    
    # Save stats
    stats_file = OUT_DIR / "enrichment_stats.json"
    stats_file.write_text(json.dumps(stats, indent=2, default=str))
    print(f"\nStats: {stats_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
