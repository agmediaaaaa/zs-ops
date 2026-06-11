#!/usr/bin/env python3
"""Download all NOT_CONTACTED leads from PlusVibe campaigns in a workspace."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_BASE = "https://api.plusvibe.ai/api/v1"
DEFAULT_WORKSPACE_ID = "6a13348c960455ee22ae829d"
DEFAULT_WORKSPACE_NAME = "Hire Tech Partners"
RATE_LIMIT_SECONDS = 0.21

LEAD_FIELDS = [
    "campaign_id",
    "camp_name",
    "status",
    "email",
    "first_name",
    "last_name",
    "company_name",
    "company_website",
    "job_title",
    "department",
    "phone_number",
    "linkedin_person_url",
    "linkedin_company_url",
    "city",
    "state",
    "country",
    "created_at",
    "modified_at",
    "_id",
]


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def api_request(api_key: str, method: str, path: str, params: dict[str, Any] | None = None) -> Any:
    query = f"?{urlencode(params)}" if params else ""
    request = Request(
        f"{API_BASE}{path}{query}",
        method=method,
        headers={
            "x-api-key": api_key,
            "Accept": "application/json",
            "User-Agent": "zs-ops-plusvibe-export/1.0",
        },
    )
    try:
        with urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else None
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"PlusVibe API error {exc.code} for {path}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"PlusVibe API request failed for {path}: {exc}") from exc


def normalize_items(payload: Any) -> list[dict[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("data", "leads", "results", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        if payload.get("_id") or payload.get("email"):
            return [payload]
    return []


def list_campaigns(api_key: str, workspace_id: str) -> list[dict[str, Any]]:
    campaigns: list[dict[str, Any]] = []
    skip = 0
    limit = 100
    while True:
        batch = normalize_items(
            api_request(
                api_key,
                "GET",
                "/campaign/list-all",
                {
                    "workspace_id": workspace_id,
                    "campaign_type": "all",
                    "skip": skip,
                    "limit": limit,
                },
            )
        )
        if not batch:
            break
        campaigns.extend(batch)
        if len(batch) < limit:
            break
        skip += limit
        time.sleep(RATE_LIMIT_SECONDS)
    return campaigns


def fetch_not_contacted_leads(
    api_key: str,
    workspace_id: str,
    campaign_id: str | None = None,
    page_size: int = 100,
) -> list[dict[str, Any]]:
    leads: list[dict[str, Any]] = []
    page = 1
    while True:
        params: dict[str, Any] = {
            "workspace_id": workspace_id,
            "status": "NOT_CONTACTED",
            "page": page,
            "limit": page_size,
            "sort": "_id",
            "direction": "asc",
        }
        if campaign_id:
            params["campaign_id"] = campaign_id

        batch = normalize_items(api_request(api_key, "GET", "/lead/workspace-leads", params))
        if not batch:
            break
        leads.extend(batch)
        if len(batch) < page_size:
            break
        page += 1
        time.sleep(RATE_LIMIT_SECONDS)
    return leads


def flatten_lead(lead: dict[str, Any]) -> dict[str, Any]:
    row = {field: lead.get(field, "") for field in LEAD_FIELDS}
    for key, value in lead.items():
        if key.startswith("custom_") and key not in row:
            row[key] = value
    return row


def write_csv(path: Path, leads: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [flatten_lead(lead) for lead in leads]
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    for field in LEAD_FIELDS:
        if field not in fieldnames:
            fieldnames.append(field)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    load_dotenv(repo_root / ".env")
    load_dotenv(repo_root / ".env.local")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-key", default=os.environ.get("PLUSVIBE_API_KEY"))
    parser.add_argument("--workspace-id", default=os.environ.get("PLUSVIBE_WORKSPACE_ID", DEFAULT_WORKSPACE_ID))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "exports",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write CSV to this exact file path instead of exports/ with a timestamp.",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the CSV after export (Numbers on macOS, default app elsewhere).",
    )
    parser.add_argument("--per-campaign", action="store_true", help="Fetch leads campaign-by-campaign.")
    args = parser.parse_args()

    if not args.api_key:
        print(
            "Missing PlusVibe API key. Set PLUSVIBE_API_KEY in .env or pass --api-key.\n"
            "Get your key from https://app.plusvibe.ai/v2/settings/api-access/",
            file=sys.stderr,
        )
        return 1

    auth = api_request(args.api_key, "GET", "/authenticate")
    workspaces = auth.get("workspaces", []) if isinstance(auth, dict) else []
    workspace_name = DEFAULT_WORKSPACE_NAME
    for workspace in workspaces:
        if workspace.get("_id") == args.workspace_id:
            workspace_name = workspace.get("name", workspace_name)
            break

    campaigns = list_campaigns(args.api_key, args.workspace_id)
    print(f"Workspace: {workspace_name} ({args.workspace_id})")
    print(f"Campaigns found: {len(campaigns)}")

    all_leads: list[dict[str, Any]] = []
    if args.per_campaign and campaigns:
        for campaign in campaigns:
            campaign_id = campaign.get("id") or campaign.get("_id")
            campaign_name = campaign.get("camp_name", campaign_id)
            if not campaign_id:
                continue
            leads = fetch_not_contacted_leads(args.api_key, args.workspace_id, campaign_id=campaign_id)
            print(f"  {campaign_name}: {len(leads)} not-contacted leads")
            all_leads.extend(leads)
    else:
        all_leads = fetch_not_contacted_leads(args.api_key, args.workspace_id)
        print(f"Not-contacted leads (workspace-wide): {len(all_leads)}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    slug = workspace_name.lower().replace(" ", "-")
    csv_path = args.output or (args.output_dir / f"{slug}-not-contacted-leads-{timestamp}.csv")
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    write_csv(csv_path, all_leads)
    print(f"Wrote CSV: {csv_path}")
    print(f"Rows: {len(all_leads)}")

    if not args.output:
        json_path = args.output_dir / f"{slug}-not-contacted-leads-{timestamp}.json"
        json_path.write_text(json.dumps(all_leads, indent=2), encoding="utf-8")

        summary = {
            "workspace_id": args.workspace_id,
            "workspace_name": workspace_name,
            "campaign_count": len(campaigns),
            "not_contacted_count": len(all_leads),
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "csv_path": str(csv_path),
            "json_path": str(json_path),
            "campaigns": [
                {
                    "id": campaign.get("id") or campaign.get("_id"),
                    "name": campaign.get("camp_name"),
                    "status": campaign.get("status"),
                    "lead_count": campaign.get("lead_count"),
                }
                for campaign in campaigns
            ],
        }
        summary_path = args.output_dir / f"{slug}-not-contacted-summary-{timestamp}.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"Wrote JSON: {json_path}")
        print(f"Wrote summary: {summary_path}")

    if args.open:
        if sys.platform == "darwin":
            subprocess.run(["open", "-a", "Numbers", str(csv_path)], check=False)
        else:
            subprocess.run(["xdg-open", str(csv_path)], check=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
