# Hire Tech Partners — PlusVibe

Workspace ID: `6a13348c960455ee22ae829d`

## Download not-contacted leads

1. Copy `.env.example` to `.env` in the repo root and add your PlusVibe API key.
2. Run:

```bash
python3 clients/hire-tech-partners/scripts/download_not_contacted_leads.py
```

Exports are written to `clients/hire-tech-partners/exports/` (gitignored).

Use `--per-campaign` to fetch campaign-by-campaign instead of one workspace-wide query.
