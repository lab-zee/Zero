#!/usr/bin/env bash
# Load a CrewDefine crew into the runtime overlay used by docker-compose / local dev.
#
# Usage:
#   ./scripts/demo.sh                         # Business Coach example + compose up
#   ./scripts/load-crew.sh /path/to/crews/my-crew
#   ./scripts/load-crew.sh --default          # revert to built-in Business Strategy crew
#   MODE=merge ./scripts/load-crew.sh ./crew  # add agents/tools without wiping active dir
#
# After loading, restart the backend (or: RESTART=1 ./scripts/load-crew.sh <crew>
# / ./scripts/load-crew.sh --restart <crew>).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ACTIVE_ROOT="$REPO_ROOT/backend/crews/active"
ACTIVE_AGENTS="$ACTIVE_ROOT/agents"
ACTIVE_TOOLS="$ACTIVE_ROOT/tools"
ENV_FILE="$REPO_ROOT/.env"
MODE="${MODE:-replace}"
RESTART="${RESTART:-0}"

usage() {
  cat <<'EOF'
Load a CrewDefine crew directory into backend/crews/active/ and update .env.

  ./scripts/demo.sh                             # example crew + docker compose up
  ./scripts/load-crew.sh <crew-dir>
  ./scripts/load-crew.sh --restart <crew-dir>   # also docker compose restart backend
  ./scripts/load-crew.sh --default | --labz     # built-in Business Strategy crew

Crew directory layout (from CrewDefine):
  <crew-dir>/agents/*.yaml
  <crew-dir>/tools/*.py        (optional)
  <crew-dir>/crew.yaml         (answer modes + output composition)

Environment written to .env (paths relative to backend/ — correct for docker-compose):
  AGENT_CONFIG_DIR=./crews/active/agents
  AGENT_PLUGINS_DIR=./crews/active/tools
  INJECT_COMMON_PROMPTS=false

Options:
  MODE=merge     Keep existing agents/tools and overlay new files (default: replace)
  RESTART=1      Restart docker compose backend after load
EOF
}

maybe_restart() {
  if [[ "$RESTART" == "1" ]]; then
    if command -v docker >/dev/null 2>&1; then
      echo "Restarting backend..."
      (cd "$REPO_ROOT" && docker compose restart backend)
    else
      echo "warning: RESTART=1 but docker not found — restart the backend manually" >&2
    fi
  else
    echo "Restart the backend: docker compose restart backend"
    echo "  (or re-run with --restart / RESTART=1)"
  fi
}

write_env() {
  local tmp
  tmp="$(mktemp)"
  if [[ -f "$ENV_FILE" ]]; then
    grep -v -E '^(AGENT_CONFIG_DIR|AGENT_PLUGINS_DIR|INJECT_COMMON_PROMPTS)=' "$ENV_FILE" > "$tmp" || true
  fi
  {
    cat "$tmp"
    echo "AGENT_CONFIG_DIR=./crews/active/agents"
    echo "AGENT_PLUGINS_DIR=./crews/active/tools"
    echo "INJECT_COMMON_PROMPTS=false"
  } > "$ENV_FILE"
  rm -f "$tmp"
}

clear_env_overrides() {
  local tmp
  tmp="$(mktemp)"
  if [[ -f "$ENV_FILE" ]]; then
    grep -v -E '^(AGENT_CONFIG_DIR|AGENT_PLUGINS_DIR|INJECT_COMMON_PROMPTS)=' "$ENV_FILE" > "$tmp" || true
    mv "$tmp" "$ENV_FILE"
  fi
}

reset_default() {
  rm -rf "$ACTIVE_ROOT"
  mkdir -p "$ACTIVE_AGENTS" "$ACTIVE_TOOLS"
  touch "$ACTIVE_AGENTS/.gitkeep" "$ACTIVE_TOOLS/.gitkeep"
  clear_env_overrides
  echo "Reverted to built-in LabZ crew (backend/src/agents/config)."
  echo "Removed AGENT_CONFIG_DIR / AGENT_PLUGINS_DIR overrides from .env (if present)."
  maybe_restart
}

load_crew() {
  local crew_dir="$1"
  local agents_src="$crew_dir/agents"
  local tools_src="$crew_dir/tools"

  if [[ ! -d "$agents_src" ]]; then
    echo "error: expected agents/ under $crew_dir" >&2
    exit 1
  fi

  shopt -s nullglob
  local yaml_files=("$agents_src"/*.yaml)
  shopt -u nullglob
  if [[ ${#yaml_files[@]} -eq 0 ]]; then
    echo "error: no *.yaml files in $agents_src" >&2
    exit 1
  fi

  for f in "${yaml_files[@]}"; do
    if [[ "$(basename "$f")" == "director.yaml" ]] || grep -q '^id: director' "$f" 2>/dev/null; then
      HAS_DIRECTOR=1
    fi
    if [[ "$(basename "$f")" == "synthesizer.yaml" ]] || grep -q '^id: synthesizer' "$f" 2>/dev/null; then
      HAS_SYNTHESIZER=1
    fi
  done

  if [[ -z "${HAS_DIRECTOR:-}" || -z "${HAS_SYNTHESIZER:-}" ]]; then
    echo "error: crew must include director and synthesizer agents (convention for LabZ runtime)" >&2
    exit 1
  fi

  echo "Validating crew..."
  VALIDATE_ARGS=("$REPO_ROOT/backend/scripts/validate_crew.py" "$crew_dir")
  if [[ -d "$tools_src" ]]; then
    VALIDATE_ARGS+=(--tools-dir "$tools_src")
  fi
  if ! python3 "${VALIDATE_ARGS[@]}"; then
    echo "error: crew validation failed — fix errors above before loading" >&2
    exit 1
  fi

  mkdir -p "$ACTIVE_AGENTS" "$ACTIVE_TOOLS"

  if [[ "$MODE" == "replace" ]]; then
    rm -rf "${ACTIVE_AGENTS:?}"/* "${ACTIVE_TOOLS:?}"/*
  fi

  cp "$agents_src"/*.yaml "$ACTIVE_AGENTS/"
  # Copy crew manifest if present (answer modes, display metadata)
  if [[ -f "$crew_dir/crew.yaml" ]]; then
    cp "$crew_dir/crew.yaml" "$ACTIVE_ROOT/crew.yaml"
  elif [[ -f "$agents_src/crew.yaml" ]]; then
    cp "$agents_src/crew.yaml" "$ACTIVE_ROOT/crew.yaml"
  fi

  if [[ -d "$tools_src" ]]; then
    shopt -s nullglob
    local tool_files=("$tools_src"/*.py)
    shopt -u nullglob
    if [[ ${#tool_files[@]} -gt 0 ]]; then
      cp "${tool_files[@]}" "$ACTIVE_TOOLS/"
    fi
  fi

  write_env

  echo "Loaded crew from: $crew_dir"
  echo "  agents -> $ACTIVE_AGENTS (${#yaml_files[@]} files)"
  if [[ -d "$tools_src" ]]; then
    echo "  tools  -> $ACTIVE_TOOLS"
  fi
  echo "Updated $ENV_FILE"
  maybe_restart
}

main() {
  if [[ $# -lt 1 ]]; then
    usage
    exit 1
  fi

  while [[ $# -gt 0 ]]; do
    case "$1" in
      -h|--help)
        usage
        exit 0
        ;;
      --default|--labz)
        reset_default
        exit 0
        ;;
      --restart)
        RESTART=1
        shift
        ;;
      -*)
        echo "error: unknown option $1" >&2
        usage
        exit 1
        ;;
      *)
        break
        ;;
    esac
  done

  if [[ $# -lt 1 ]]; then
    usage
    exit 1
  fi

  CREW_DIR="$(cd "$1" && pwd)"
  load_crew "$CREW_DIR"
}

main "$@"
