#!/usr/bin/env python3
"""
MARS USA Manufacturing Lead Generation - October 18, 2026

Approved budget: $3.65 estimated, $5.00 HARD CAP
Client: MARS (Zillion Systems)
Source: Icypeas people search via treg.to
Filters: All USA (person location US + company HQ US, no state limits)
         Headcount 10-499 (bands: 10-199 = founder/owner titles, 200-499 = ops titles)
         NO industry filter (broader variant)
         4 segments: Seg1 CNC, Seg2 Foundries, Seg3 AS9100, Seg4 Sheet Metal
         Dedupe across segments (priority: Seg1 > Seg2 > Seg3 > Seg4)
         1 person per company
         
Pipeline: Icypeas search → hygiene/suppression → cache check → pattern emails →
          ContactOut verify (free) → Blitz → QuickEnrich/TryKitt → MV (all non-cached)
          
Storage: Supabase "Lead Database" + lead_lists registration
Outputs: runs/mars-2026-10-18/mars_usa_valid.csv (MV-valid)
         runs/mars-2026-10-18/mars_usa_catchall.csv (catch-all emails)
"""

import sys
from pathlib import Path

# Add parent scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

import argparse
import csv
import json
import os
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

# Import from gws script
import gws_icypeas_sheet2 as base

# Configuration
BASE_DIR = Path(__file__).parent.parent
OUT_DIR = BASE_DIR / "runs" / "mars-2026-10-18"
OUT_DIR.mkdir(parents=True, exist_ok=True)

UPLOADS = Path("/home/ubuntu/.cursor/projects/workspace/uploads")
FILTERS_FILE = UPLOADS / "mars_filters_2026-10-18b_allUSA_bands_d437.json"
COUNTS_FILE = UPLOADS / "mars_counts_2026-10-18b_allUSA_bands_7410.json"
SUPPRESS_DOMAINS = UPLOADS / "mars_suppress_domains_0755.txt"
SUPPRESS_EMAILS = UPLOADS / "mars_suppress_emails_08f5.txt"
SUPPRESS_LINKEDIN = UPLOADS / "mars_suppress_linkedin_5cb7.txt"

HARD_CAP_USD = 5.00
EST_COST_USD = 3.65

# Thread-safe spend tracking
_spent_micro = 0
_cap_micro = int(HARD_CAP_USD * 1_000_000)
_stop_spend = False
_lock = threading.Lock()

# Suppression
SUPPRESS_DOM_SET: set[str] = set()
SUPPRESS_EM_SET: set[str] = set()
SUPPRESS_LI_SET: set[str] = set()

# Segment priority for deduping
SEG_PRIORITY = {"Seg1": 1, "Seg2": 2, "Seg3_A": 3, "Seg4": 4}

# Stats
stats = {
    "start_balance": 0.0,
    "end_balance": 0.0,
    "segments": {},
    "cost_by_provider": defaultdict(float),
    "emails_by_source": defaultdict(int),
    "mv_status": defaultdict(int),
}


def load_suppressions():
    """Load all suppression lists."""
    global SUPPRESS_DOM_SET, SUPPRESS_EM_SET, SUPPRESS_LI_SET
    
    if SUPPRESS_DOMAINS.exists():
        SUPPRESS_DOM_SET = {
            line.strip().lower()
            for line in SUPPRESS_DOMAINS.read_text().strip().split("\n")
            if line.strip()
        }
        print(f"Loaded {len(SUPPRESS_DOM_SET)} suppression domains")
    
    if SUPPRESS_EMAILS.exists():
        SUPPRESS_EM_SET = {
            line.strip().lower()
            for line in SUPPRESS_EMAILS.read_text().strip().split("\n")
            if line.strip() and "@" in line
        }
        print(f"Loaded {len(SUPPRESS_EM_SET)} suppression emails")
    
    if SUPPRESS_LINKEDIN.exists():
        SUPPRESS_LI_SET = {
            base.normalize_linkedin(line.strip())
            for line in SUPPRESS_LINKEDIN.read_text().strip().split("\n")
            if line.strip()
        }
        print(f"Loaded {len(SUPPRESS_LI_SET)} suppression LinkedIn URLs")


def is_suppressed(lead: dict, email: str | None = None) -> str | None:
    """Check if lead/email is suppressed. Returns reason or None."""
    if lead.get("li") and lead["li"] in SUPPRESS_LI_SET:
        return "linkedin"
    if lead.get("domain") and lead["domain"] in SUPPRESS_DOM_SET:
        return "domain"
    if email and email.lower() in SUPPRESS_EM_SET:
        return "email"
    return None


def under_cap(need_micro: int = 0) -> bool:
    """Check if under spend cap."""
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


def load_filters():
    """Load approved filters."""
    return json.loads(FILTERS_FILE.read_text())


def get_query(seg_name: str, band: str, filters: dict) -> dict:
    """Get pre-built Icypeas query from filters."""
    # Map short names to full names
    seg_map = {
        "Seg1": "Seg1_CNC_Machine_Shops",
        "Seg2": "Seg2_Foundries_Metal_Casting",
        "Seg3_A": "Seg3_AS9100_Aerospace_Turbine",
        "Seg4": "Seg4_Sheet_Metal_Fabrication"
    }
    
    full_name = seg_map[seg_name]
    seg_data = filters["segments"][full_name]
    
    # Get pre-built query: broader_{band}_people
    query_key = f"broader_{band}_people"
    return seg_data["icypeas_queries"][query_key]




def search_segment_band(seg_key: str, band_key: str, query: dict) -> list[dict]:
    """Run Icypeas search for one segment/band combo."""
    leads = []
    token = None
    page = 0
    max_pages = 30
    
    print(f"  Searching {seg_key} {band_key}...")
    
    while page < max_pages:
        if not under_cap(50_000):  # ~$0.00038 * 100 rows = $0.038
            print(f"  Stopping search - approaching cap")
            break
        
        body = {"query": query, "pagination": {"size": 100}}
        if token:
            body["pagination"]["token"] = token
        
        try:
            data, meta = base.treg("POST", "/call/icypeas.people.search", body=body, timeout=90)
            charge(meta.get("cost_micro", 0), "icypeas")
            
            page_leads = data.get("leads", []) if data else []
            if not page_leads:
                break
            
            leads.extend(page_leads)
            page += 1
            
            pagination = data.get("pagination", {}) if data else {}
            token = pagination.get("token")
            
            if not token or len(page_leads) < 100:
                break
            
            if page % 5 == 0:
                print(f"    Page {page}: {len(leads)} total")
                
        except Exception as e:
            print(f"  Search error: {e}")
            break
    
    print(f"  {seg_key} {band_key}: {len(leads)} leads")
    return leads


def parse_lead(raw: dict, seg_key: str, band_key: str) -> dict:
    """Parse Icypeas raw lead."""
    return {
        "segment": seg_key,
        "band": band_key,
        "first": (raw.get("firstname") or "").strip(),
        "last": (raw.get("lastname") or "").strip(),
        "title": (raw.get("lastJobTitle") or "").strip(),
        "company": (raw.get("lastCompanyName") or "").strip(),
        "domain": base.domain_of(raw.get("lastCompanyWebsite") or ""),
        "linkedin": (raw.get("profileUrl") or "").strip(),
        "li": base.normalize_linkedin(raw.get("profileUrl") or ""),
        "size": raw.get("lastCompanySize"),
        "industry": raw.get("lastCompanyIndustry"),
        "location": raw.get("address"),
        "company_description": (raw.get("lastCompanyDescription") or "").strip(),
        "company_address": (raw.get("lastCompanyAddress") or "").strip(),
    }


def hygiene(leads: list[dict]) -> tuple[list[dict], dict]:
    """Apply hygiene filters. Returns (clean, skips)."""
    clean = []
    skips = defaultdict(int)
    seen_dom = set()
    seen_li = set()
    
    for lead in leads:
        # Name
        if not lead["first"] or not lead["last"]:
            skips["no_name"] += 1
            continue
        
        # Domain
        if not lead["domain"] or "linkedin.com" in lead["domain"]:
            skips["no_domain"] += 1
            continue
        
        # Title
        if not base.title_ok(lead["title"], lead["company"]):
            skips["title"] += 1
            continue
        
        # Division/subsidiary
        company_lower = lead["company"].lower()
        if "division of" in company_lower or "subsidiary of" in company_lower:
            skips["division_subsidiary"] += 1
            continue
        
        # Suppression
        reason = is_suppressed(lead)
        if reason:
            skips[f"suppressed_{reason}"] += 1
            continue
        
        # Dedupe within segment
        if lead["domain"] in seen_dom:
            skips["dupe_domain"] += 1
            continue
        if lead["li"] and lead["li"] in seen_li:
            skips["dupe_linkedin"] += 1
            continue
        
        seen_dom.add(lead["domain"])
        if lead["li"]:
            seen_li.add(lead["li"])
        clean.append(lead)
    
    return clean, dict(skips)


def dedupe_cross_segment(segments_data: dict) -> list[dict]:
    """Dedupe across segments by priority: Seg1 > Seg2 > Seg3_A > Seg4."""
    all_leads = []
    
    for seg_key in ["Seg1", "Seg2", "Seg3_A", "Seg4"]:
        if seg_key in segments_data:
            for lead in segments_data[seg_key]["clean"]:
                lead["seg_priority"] = SEG_PRIORITY[seg_key]
                all_leads.append(lead)
    
    # Sort by priority
    all_leads.sort(key=lambda x: x["seg_priority"])
    
    # Dedupe
    seen_li = set()
    seen_dom = set()
    final = []
    
    for lead in all_leads:
        if lead["li"]:
            if lead["li"] in seen_li:
                continue
            seen_li.add(lead["li"])
        
        if lead["domain"] in seen_dom:
            continue
        seen_dom.add(lead["domain"])
        
        final.append(lead)
    
    return final


def write_csv(leads: list[dict], filename: str):
    """Write leads to CSV."""
    if not leads:
        return
    
    path = OUT_DIR / filename
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "first", "last", "title", "company", "domain", "linkedin",
            "email", "email_source", "email_status", "size", "industry", "segment"
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
                "email_status": lead.get("email_status", ""),
                "size": lead.get("size", ""),
                "industry": lead.get("industry", ""),
                "segment": lead.get("segment", ""),
            })
    print(f"Wrote {len(leads)} leads to {path}")


def main():
    parser = argparse.ArgumentParser(description="MARS USA Manufacturing lead generation")
    parser.add_argument("--confirm-spend", type=float, metavar="USD",
                       help=f"Confirm spend up to this amount (max ${HARD_CAP_USD:.2f})")
    parser.add_argument("--dry-run", action="store_true",
                       help="Dry run (show plan only)")
    
    args = parser.parse_args()
    
    if not args.confirm_spend and not args.dry_run:
        print(f"MARS USA Manufacturing Lead Generation")
        print(f"Estimated: ${EST_COST_USD:.2f}, Hard cap: ${HARD_CAP_USD:.2f}")
        print()
        print("Run with:")
        print(f"  --confirm-spend {HARD_CAP_USD:.2f}  # to proceed")
        print(f"  --dry-run                    # to see plan only")
        return 1
    
    if args.confirm_spend:
        if args.confirm_spend > HARD_CAP_USD:
            print(f"Error: Confirmed amount ${args.confirm_spend:.2f} > hard cap ${HARD_CAP_USD:.2f}")
            return 1
    
    # Load token
    base.TOKEN = base.load_treg_token()
    
    print("=" * 80)
    print("MARS USA Manufacturing Lead Generation - October 18, 2026")
    print("=" * 80)
    print(f"Estimated: ${EST_COST_USD:.2f}, Hard cap: ${HARD_CAP_USD:.2f}")
    print()
    
    # Check balance
    try:
        bal = base.balance_usd()
        stats["start_balance"] = bal
        print(f"Treg balance: ${bal:.2f}")
        if bal < EST_COST_USD:
            print(f"⚠️  Warning: balance < estimated cost")
    except Exception as e:
        print(f"Could not check balance: {e}")
        bal = 0.0
    print()
    
    # Load suppressions
    print("Loading suppressions...")
    load_suppressions()
    print()
    
    # Load filters
    print("Loading filters...")
    filters = load_filters()
    print("Using broader variant (NO industry filter)")
    print()
    
    if args.dry_run:
        print("DRY RUN - would search these segments:")
        for seg_key in ["Seg1", "Seg2", "Seg3_A", "Seg4"]:
            print(f"  {seg_key}: {SEG_PRIORITY[seg_key]} priority")
        print("\nExiting (dry run)")
        return 0
    
    # Run searches
    segments_data = {}
    
    for seg_key in ["Seg1", "Seg2", "Seg3_A", "Seg4"]:
        print(f"\n{'=' * 60}")
        print(f"{seg_key} - Priority {SEG_PRIORITY[seg_key]}")
        print('=' * 60)
        
        seg_data = {"raw": [], "clean": [], "skips": {}}
        
        for band_key in ["10-199", "200-499"]:
            query = get_query(seg_key, band_key, filters)
            raw_leads = search_segment_band(seg_key, band_key, query)
            
            parsed = [parse_lead(raw, seg_key, band_key) for raw in raw_leads]
            seg_data["raw"].extend(parsed)
        
        clean, skips = hygiene(seg_data["raw"])
        seg_data["clean"] = clean
        seg_data["skips"] = skips
        
        print(f"\n{seg_key} Summary:")
        print(f"  Raw: {len(seg_data['raw'])}, Clean: {len(clean)}, Skipped: {sum(skips.values())}")
        
        segments_data[seg_key] = seg_data
        stats["segments"][seg_key] = {
            "raw": len(seg_data["raw"]),
            "clean": len(clean),
            "skips": dict(skips)
        }
        
        if _stop_spend:
            print("\n⚠️  Spend cap reached")
            break
    
    print(f"\n\n{'=' * 60}")
    print("Cross-segment deduplication")
    print('=' * 60)
    
    final_leads = dedupe_cross_segment(segments_data)
    print(f"Final: {len(final_leads)} leads")
    
    # Save state
    state_file = OUT_DIR / "leads_pre_enrich.jsonl"
    with state_file.open("w") as f:
        for lead in final_leads:
            f.write(json.dumps(lead) + "\n")
    print(f"Saved: {state_file}")
    
    # Write placeholder CSVs
    write_csv(final_leads, "mars_usa_leads.csv")
    
    # Final report
    try:
        end_bal = base.balance_usd()
        stats["end_balance"] = end_bal
    except:
        end_bal = bal
    
    total_spent = _spent_micro / 1_000_000
    
    print(f"\n\n{'=' * 80}")
    print("FINAL REPORT")
    print('=' * 80)
    print(f"\nBalance: ${stats['start_balance']:.2f} → ${stats['end_balance']:.2f}")
    print(f"Spent: ${total_spent:.2f} / ${HARD_CAP_USD:.2f} cap")
    print(f"\nLeads: {len(final_leads)}")
    print(f"\nCost by provider:")
    for prov, cost in sorted(stats["cost_by_provider"].items()):
        print(f"  {prov}: ${cost:.4f}")
    
    report_file = OUT_DIR / "report.json"
    report_file.write_text(json.dumps(stats, indent=2, default=str))
    print(f"\nReport: {report_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
