#!/usr/bin/env bash
# Run this on your Mac in Terminal. Saves a table-ready CSV to ~/Downloads.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
DOWNLOADS="${HOME}/Downloads"
OUT_FILE="${DOWNLOADS}/hire-tech-partners-not-contacted-leads.csv"

if [[ -f "${REPO_ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${REPO_ROOT}/.env"
  set +a
fi

if [[ -z "${PLUSVIBE_API_KEY:-}" ]]; then
  echo "Set your PlusVibe API key first:"
  echo "  export PLUSVIBE_API_KEY='your-key-here'"
  exit 1
fi

mkdir -p "${DOWNLOADS}"

python3 "${SCRIPT_DIR}/download_not_contacted_leads.py" \
  --output "${OUT_FILE}" \
  --open

echo ""
echo "Saved to: ${OUT_FILE}"
