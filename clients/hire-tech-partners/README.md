# Hire Tech Partners — PlusVibe

Workspace ID: `6a13348c960455ee22ae829d`

## Download to your Mac (recommended)

Cloud agent artifact downloads often fail. Run this **on your Mac in Terminal**:

```bash
cd ~/path/to/zs-ops
export PLUSVIBE_API_KEY='your-plusvibe-api-key'
bash clients/hire-tech-partners/scripts/download_on_mac.sh
```

This saves:

`~/Downloads/hire-tech-partners-not-contacted-leads.csv`

…and opens it in **Numbers** as a proper table.

### One-liner (no repo clone)

Paste in **Terminal on your Mac**:

```bash
export PLUSVIBE_API_KEY='your-plusvibe-api-key' && \
curl -fsSL "https://raw.githubusercontent.com/agmediaaaaa/zs-ops/cursor/download-not-contacted-leads-7656/clients/hire-tech-partners/scripts/download_not_contacted_leads.py" -o /tmp/plusvibe_export.py && \
python3 /tmp/plusvibe_export.py --output "$HOME/Downloads/hire-tech-partners-not-contacted-leads.csv" --open
```

Replace `your-plusvibe-api-key` with your key from https://app.plusvibe.ai/v2/settings/api-access/

## Manual export (from repo)

```bash
python3 clients/hire-tech-partners/scripts/download_not_contacted_leads.py
```

Exports go to `clients/hire-tech-partners/exports/` (gitignored).
