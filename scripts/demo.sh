#!/usr/bin/env bash
# One-command Lab Z demo with a validated reference crew already loaded.
#
#   cp .env.example .env   # add GEMINI_API_KEY and/or OPENAI_API_KEY
#   ./scripts/demo.sh                       # Technical Due Diligence (default)
#   ./scripts/demo.sh business-coaching-crew
#
# Then open http://localhost:3000 — register, create a workspace, chat.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CREW_SLUG="${1:-technical-due-diligence}"
if [[ ! "$CREW_SLUG" =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
  echo "error: crew must be a directory name under backend/crews/examples/" >&2
  exit 1
fi
EXAMPLE="$REPO_ROOT/backend/crews/examples/$CREW_SLUG"
ENV_FILE="$REPO_ROOT/.env"
ENV_EXAMPLE="$REPO_ROOT/.env.example"

cd "$REPO_ROOT"

if [[ ! -d "$EXAMPLE/agents" ]]; then
  echo "error: unknown bundled crew '$CREW_SLUG'" >&2
  exit 1
fi
CREW_NAME="$(
  awk '/^display_name: / { sub(/^display_name: /, ""); print; exit }' "$EXAMPLE/crew.yaml"
)"
CREW_NAME="${CREW_NAME:-$CREW_SLUG}"

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ ! -f "$ENV_EXAMPLE" ]]; then
    echo "error: no .env and no .env.example in $REPO_ROOT" >&2
    exit 1
  fi
  cp "$ENV_EXAMPLE" "$ENV_FILE"
  echo "Created .env from .env.example."
  echo "Add GEMINI_API_KEY and/or OPENAI_API_KEY, then rerun this command."
  echo "OpenAI as a fallback is strongly recommended — multi-agent runs burn Gemini free-tier RPM."
  exit 1
fi

key_ok() {
  local name="$1"
  local raw
  raw="$(grep -E "^${name}=" "$ENV_FILE" | tail -n1 | cut -d= -f2- || true)"
  raw="${raw%\"}"
  raw="${raw#\"}"
  raw="${raw%\'}"
  raw="${raw#\'}"
  raw="$(printf '%s' "$raw" | tr -d '[:space:]')"
  if [[ -z "$raw" ]]; then
    return 1
  fi
  case "$raw" in
    your_*|*_key_here|changeme|xxx|TODO) return 1 ;;
  esac
  return 0
}

if ! key_ok GEMINI_API_KEY && ! key_ok OPENAI_API_KEY; then
  echo "error: set GEMINI_API_KEY and/or OPENAI_API_KEY in .env" >&2
  echo "OpenAI as a fallback is strongly recommended for multi-agent runs." >&2
  exit 1
fi

echo "Lab Z demo"
echo "  crew  $CREW_NAME"
echo "  ui    http://localhost:3000"
echo "  api   http://localhost:3001"
echo

"$REPO_ROOT/scripts/load-crew.sh" "$EXAMPLE"

echo
echo "Starting Zero (Ctrl-C to stop)..."
exec docker compose up --build
