#!/usr/bin/env bash
# From the repository root: bash examples/ieee123_course/scripts/run_bash.sh --lesson 00 --run-id first
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$REPO"
python -B examples/ieee123_course/run_course.py "$@"
