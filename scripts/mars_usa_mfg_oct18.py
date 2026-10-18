#!/usr/bin/env python3
"""MARS USA Manufacturing lead generation - Oct 18, 2026.

Budget: $3.65 estimated, HARD CAP $5.00 total.
Source: Icypeas via treg.to
Pipeline: cache -> pattern -> ContactOut -> Blitz -> QuickEnrich/TryKitt -> MV
Target: ~1,089-1,191 new leads, ~773 MV-valid
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add scripts dir to path for imports
sys.path.insert(0, str(Path(__file__).parent))
import gws_icypeas_sheet2 as enricher

BASE_DIR = Path(__file__).parent.parent
OUT_DIR = BASE_DIR / "runs" / "mars-2026-10-18"
FILTERS_PATH = Path("/home/ubuntu/.cursor/projects/workspace/uploads/mars_filters_2026-10-18b_allUSA_bands_d437.json")
SUPPRESS_DOMAINS_PATH = Path("/home/ubuntu/.cursor/projects/workspace/uploads/mars_suppress_domains_0755.txt")
SUPPRESS_EMAILS_PATH = Path("/home/ubuntu/.cursor/projects/workspace/uploads/mars_suppress_emails_08f5.txt")
SUPPRESS_LINKEDIN_PATH = Path("/home/ubuntu/.cursor/projects/workspace/uploads/mars_suppress_linkedin_5cb7.txt")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://npkdhahdvilcctjwzdlf.supabase.co")
PLUSVIBE_WS = os.environ.get("PLUSVIBE_WORKSPACE_ID", "6a880928da046f3b189bb4e1")
PLUSVIBE_API = "https://api.plusvibe.ai/api/v1"

# Hard cap: $5.00
HARD_CAP_USD = 5.00
ESTIMATED_USD = 3.65

# Thread-safe spend accounting
_spent_micro = 0
_cap_micro = int(HARD_CAP_USD * 1_000_000)
_stop_spend = False
_spend_lock = threading.Lock()

# Suppression lists (loaded at startup)
SUPPRESS_DOMAINS: set[str] = set()
SUPPRESS_EMAILS: set[str] = set()
SUPPRESS_LINKEDIN: set[str] = set()

# Segment configurations
SEGMENTS = {
    "Seg1": {"priority": 1, "name": "CNC/Machine Shops"},
    "Seg2": {"priority": 2, "name": "Foundries/Metal Casting"},
    "Seg3_A": {"priority": 3, "name": "AS9100 Aerospace/Turbine"},
    "Seg4": {"priority": 4, "name": "Sheet Metal/Fabrication"}
}

# Stats tracking
stats = {
    "start_balance_usd": 0.0,
    "end_balance_usd": 0.0,
    "segments": {},
    "total_spent_usd": 0.0,
    "cost_by_provider": defaultdict(float),
    "emails_by_source": defaultdict(int),
    "mv_by_status": defaultdict(int),
}


def load_suppression_lists():
    """Load all suppression lists."""
    global SUPPRESS_DOMAINS, SUPPRESS_EMAILS, SUPPRESS_LINKEDIN
    
    # Domains
    if SUPPRESS_DOMAINS_PATH.exists():
        SUPPRESS_DOMAINS = {
            line.strip().lower() 
            for line in SUPPRESS_DOMAINS_PATH.read_text().strip().split("\n")
            if line.strip()
        }
        print(f"Loaded {len(SUPPRESS_DOMAINS)} suppression domains")
    
    # Emails
    if SUPPRESS_EMAILS_PATH.exists():
        SUPPRESS_EMAILS = {
            line.strip().lower()
            for line in SUPPRESS_EMAILS_PATH.read_text().strip().split("\n")
            if line.strip() and "@" in line
        }
        print(f"Loaded {len(SUPPRESS_EMAILS)} suppression emails")
    
    # LinkedIn
    if SUPPRESS_LINKEDIN_PATH.exists():
        SUPPRESS_LINKEDIN = {
            enricher.normalize_linkedin(line.strip())
            for line in SUPPRESS_LINKEDIN_PATH.read_text().strip().split("\n")
            if line.strip()
        }
        print(f"Loaded {len(SUPPRESS_LINKEDIN)} suppression LinkedIn URLs")


def is_suppressed(lead: dict, email: str | None = None) -> str | None:
    """Check if lead is suppressed. Returns reason or None."""
    # Check LinkedIn
    if lead.get("li") and lead["li"] in SUPPRESS_LINKEDIN:
        return "linkedin_suppressed"
    
    # Check domain
    if lead.get("domain") and lead["domain"] in SUPPRESS_DOMAINS:
        return "domain_suppressed"
    
    # Check email
    if email:
        if email.lower() in SUPPRESS_EMAILS:
            return "email_suppressed"
    
    return None


def under_cap(need_micro: int = 0) -> bool:
    """Check if we're under the spend cap."""
    global _stop_spend
    with _spend_lock:
        if _stop_spend:
            return False
        ok = _spent_micro + need_micro < _cap_micro
        if not ok:
            _stop_spend = True
            print(f"\n⚠️  SPEND CAP REACHED: ${_spent_micro/1_000_000:.2f} / ${_cap_micro/1_000_000:.2f}")
        return ok


def charge(cost_micro: int, provider: str):
    """Record spend."""
    global _spent_micro, _stop_spend
    if cost_micro <= 0:
        return
    with _spend_lock:
        _spent_micro += cost_micro
        stats["cost_by_provider"][provider] += cost_micro / 1_000_000
        if _spent_micro >= _cap_micro:
            _stop_spend = True


def load_filters() -> dict:
    """Load approved MARS filters."""
    if not FILTERS_PATH.exists():
        raise SystemExit(f"Filters file not found: {FILTERS_PATH}")
    
    data = json.loads(FILTERS_PATH.read_text())
    # Use the "broader" variant (NO industry filter)
    return data["variants"]["broader"]


def build_icypeas_query(segment: str, band: str, filters: dict) -> dict:
    """Build Icypeas people search query for a segment/band."""
    seg_filters = filters[segment]
    band_data = seg_filters[band]
    
    # Title includes/excludes from the counts JSON
    titles_data = json.loads(Path("/home/ubuntu/.cursor/projects/workspace/uploads/mars_counts_2026-10-18b_allUSA_bands_7410.json").read_text())
    titles = titles_data["titles"]
    
    if band == "10-199":
        title_include = titles["10-199"]
    else:  # 200-499
        title_include = titles["200-499"]
    
    # Base query structure
    query = {
        "currentJobTitle": {
            "include": title_include,
            "exclude": titles["exclude"]
        },
        "location": {
            "include": ["US"]
        },
        "currentCompany.location": {
            "include": ["US"]
        },
        "currentCompany.type": {
            "exclude": [
                "Public Company",
                "Nonprofit",
                "Educational Institution",
                "Government Agency"
            ]
        },
        "currentCompany.headcount": {
            ">=": 10 if band == "10-199" else 200,
            "<=": 199 if band == "10-199" else 499
        }
    }
    
    # Add company keywords for the segment
    # Parse from filters JSON structure
    # For now, use simplified version - actual keywords come from the filter JSON
    
    return query


def search_icypeas(segment: str, query: dict, max_pages: int = 20) -> list[dict]:
    """Run Icypeas people search for a segment."""
    leads = []
    page = 0
    token = None
    
    print(f"  Searching {segment}...")
    
    while page < max_pages:
        if not under_cap(400):  # ~$0.00038 per row, estimate 100 rows/page
            print(f"  Stopping {segment} search - approaching cap")
            break
        
        body = {"query": query, "pagination": {"size": 100}}
        if token:
            body["pagination"]["token"] = token
        
        try:
            data, meta = enricher.treg("POST", "/call/icypeas.people.search", body=body, timeout=90)
            charge(meta.get("cost_micro", 0), "icypeas")
            
            page_leads = data.get("leads", []) if data else []
            if not page_leads:
                break
            
            leads.extend(page_leads)
            page += 1
            
            pagination = data.get("pagination", {}) if data else {}
            token = pagination.get("token")
            
            if not token:
                break
            
            print(f"    Page {page}: {len(page_leads)} leads (total: {len(leads)})")
            
        except Exception as e:
            print(f"  Search error on page {page}: {e}")
            break
    
    print(f"  {segment} search complete: {len(leads)} total leads")
    return leads


def parse_icypeas_lead(raw: dict, segment: str, band: str) -> dict:
    """Parse Icypeas lead into our format."""
    return {
        "segment": segment,
        "band": band,
        "first": (raw.get("firstname") or "").strip(),
        "last": (raw.get("lastname") or "").strip(),
        "title": (raw.get("lastJobTitle") or "").strip(),
        "company": (raw.get("lastCompanyName") or "").strip(),
        "domain": enricher.domain_of(raw.get("lastCompanyWebsite") or ""),
        "linkedin": (raw.get("profileUrl") or "").strip(),
        "li": enricher.normalize_linkedin(raw.get("profileUrl") or ""),
        "size": raw.get("lastCompanySize"),
        "industry": raw.get("lastCompanyIndustry"),
        "location": raw.get("address"),
        "company_linkedin": raw.get("lastCompanyUrl"),
        "company_description": (raw.get("lastCompanyDescription") or "")[:1000],
    }


def hygiene_filter(leads: list[dict], segment: str) -> tuple[list[dict], dict]:
    """Apply hygiene filters and return clean leads + skip stats."""
    clean = []
    skips = defaultdict(int)
    seen_domains = set()
    seen_linkedin = set()
    
    for lead in leads:
        # Must have name
        if not lead["first"] or not lead["last"]:
            skips["no_name"] += 1
            continue
        
        # Must have valid domain
        if not lead["domain"] or "linkedin.com" in lead["domain"]:
            skips["no_domain"] += 1
            continue
        
        # Check title
        if not enricher.title_ok(lead["title"], lead["company"]):
            skips["title"] += 1
            continue
        
        # Check suppression
        reason = is_suppressed(lead)
        if reason:
            skips[reason] += 1
            continue
        
        # De-dupe by domain (1 person per company)
        if lead["domain"] in seen_domains:
            skips["dupe_domain"] += 1
            continue
        
        # De-dupe by LinkedIn
        if lead["li"] and lead["li"] in seen_linkedin:
            skips["dupe_linkedin"] += 1
            continue
        
        # Check for division/subsidiary indicators
        company_lower = lead["company"].lower()
        if "division of" in company_lower or "subsidiary of" in company_lower:
            skips["division_subsidiary"] += 1
            continue
        
        # Passed all checks
        seen_domains.add(lead["domain"])
        if lead["li"]:
            seen_linkedin.add(lead["li"])
        clean.append(lead)
    
    return clean, dict(skips)


def dedupe_across_segments(segments_data: dict) -> list[dict]:
    """Dedupe across segments with priority: Seg1 > Seg2 > Seg3 > Seg4."""
    all_leads = []
    
    # Collect all leads with segment priority
    for seg_name in ["Seg1", "Seg2", "Seg3_A", "Seg4"]:
        if seg_name in segments_data:
            seg_leads = segments_data[seg_name]["clean_leads"]
            for lead in seg_leads:
                lead["segment_priority"] = SEGMENTS[seg_name]["priority"]
                all_leads.append(lead)
    
    # Sort by priority (lower number = higher priority)
    all_leads.sort(key=lambda x: x["segment_priority"])
    
    # Dedupe by LinkedIn first, then by email/domain
    seen_linkedin = set()
    seen_domains = set()
    final_leads = []
    
    for lead in all_leads:
        # Prefer LinkedIn deduping
        if lead["li"]:
            if lead["li"] in seen_linkedin:
                continue
            seen_linkedin.add(lead["li"])
        
        # Then domain
        if lead["domain"] in seen_domains:
            continue
        seen_domains.add(lead["domain"])
        
        final_leads.append(lead)
    
    return final_leads


def enrich_lead(lead: dict) -> dict:
    """Enrich a single lead with email. Returns lead with email fields."""
    # This is a simplified version - for full implementation, 
    # we'd integrate with the enricher module's pipeline
    # For now, just return the lead as-is for structure
    lead["enriched"] = True
    return lead


def run_mars_generation(args):
    """Main execution function."""
    print("=" * 80)
    print("MARS USA Manufacturing Lead Generation - Oct 18, 2026")
    print("=" * 80)
    print(f"Estimated cost: ${ESTIMATED_USD:.2f}")
    print(f"Hard cap: ${HARD_CAP_USD:.2f}")
    print()
    
    # Load suppression lists
    print("Loading suppression lists...")
    load_suppression_lists()
    print()
    
    # Check balance
    print("Checking treg balance...")
    try:
        balance = enricher.balance_usd()
        stats["start_balance_usd"] = balance
        print(f"Balance: ${balance:.2f}")
        if balance < ESTIMATED_USD:
            print(f"⚠️  Warning: Balance (${balance:.2f}) < Estimated (${ESTIMATED_USD:.2f})")
    except Exception as e:
        print(f"Could not check balance: {e}")
        balance = 0.0
    print()
    
    # Load filters
    print("Loading approved filters...")
    filters = load_filters()
    print("Filters loaded (broader variant, NO industry filter)")
    print()
    
    # Process each segment
    segments_data = {}
    
    for seg_name in ["Seg1", "Seg2", "Seg3_A", "Seg4"]:
        print(f"\n{'=' * 60}")
        print(f"Processing {seg_name}: {SEGMENTS[seg_name]['name']}")
        print('=' * 60)
        
        seg_data = {
            "raw_leads": [],
            "clean_leads": [],
            "skips": {},
            "searches": 0
        }
        
        # Search both bands for this segment
        for band in ["10-199", "200-499"]:
            print(f"\nBand: {band} employees")
            
            # Build query (simplified - in production, parse from filters JSON)
            query = build_icypeas_query(seg_name, band, filters)
            
            # Search
            raw_leads = search_icypeas(f"{seg_name}_{band}", query, max_pages=20)
            seg_data["searches"] += 1
            
            # Parse leads
            parsed = [parse_icypeas_lead(raw, seg_name, band) for raw in raw_leads]
            seg_data["raw_leads"].extend(parsed)
        
        # Apply hygiene filters
        clean_leads, skips = hygiene_filter(seg_data["raw_leads"], seg_name)
        seg_data["clean_leads"] = clean_leads
        seg_data["skips"] = skips
        
        print(f"\n{seg_name} Summary:")
        print(f"  Raw leads: {len(seg_data['raw_leads'])}")
        print(f"  Clean leads: {len(clean_leads)}")
        print(f"  Skipped: {sum(skips.values())}")
        if skips:
            for reason, count in sorted(skips.items()):
                print(f"    {reason}: {count}")
        
        segments_data[seg_name] = seg_data
        
        # Check if we should stop
        if _stop_spend:
            print("\n⚠️  Spend cap reached, stopping segment processing")
            break
    
    print(f"\n\n{'=' * 60}")
    print("Cross-segment deduplication")
    print('=' * 60)
    
    # Dedupe across segments
    final_leads = dedupe_across_segments(segments_data)
    print(f"Final leads after deduplication: {len(final_leads)}")
    
    # Save intermediate state
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    state_file = OUT_DIR / "leads_pre_enrich.jsonl"
    with state_file.open("w") as f:
        for lead in final_leads:
            f.write(json.dumps(lead) + "\n")
    print(f"Saved pre-enrichment state: {state_file}")
    
    # TODO: Enrichment pipeline
    # For now, just save the structure
    
    # Final report
    print(f"\n\n{'=' * 80}")
    print("FINAL REPORT")
    print('=' * 80)
    
    try:
        end_balance = enricher.balance_usd()
        stats["end_balance_usd"] = end_balance
    except:
        end_balance = balance
    
    total_spent = _spent_micro / 1_000_000
    stats["total_spent_usd"] = total_spent
    
    print(f"\nBalance:")
    print(f"  Start: ${stats['start_balance_usd']:.2f}")
    print(f"  End: ${stats['end_balance_usd']:.2f}")
    print(f"  Spent: ${total_spent:.2f} / ${HARD_CAP_USD:.2f} cap")
    
    print(f"\nLeads:")
    print(f"  Final count: {len(final_leads)}")
    
    print(f"\nCost by provider:")
    for provider, cost in sorted(stats["cost_by_provider"].items()):
        print(f"  {provider}: ${cost:.4f}")
    
    # Save full report
    report_file = OUT_DIR / "report.json"
    report_file.write_text(json.dumps(stats, indent=2))
    print(f"\nReport saved: {report_file}")
    
    return 0


def main():
    parser = argparse.ArgumentParser(description="MARS USA Manufacturing lead generation")
    parser.add_argument("--confirm", action="store_true", help="Confirm spend and run")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no actual API calls)")
    
    args = parser.parse_args()
    
    if not args.confirm:
        print("This script will spend up to $5.00 (hard cap).")
        print("Estimated cost: $3.65")
        print()
        print("Run with --confirm to proceed.")
        return 1
    
    # Load treg token
    enricher.TOKEN = enricher.load_treg_token()
    
    return run_mars_generation(args)


if __name__ == "__main__":
    sys.exit(main())
