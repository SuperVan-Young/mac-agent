#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "WARN: env/setup_openroad_conda.sh is deprecated; use env/setup_conda.sh instead." >&2
exec "${SCRIPT_DIR}/setup_conda.sh" "$@"
