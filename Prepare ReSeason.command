#!/bin/zsh
set -eu
TASK_DIR="${0:A:h}"
exec python3 -B "$TASK_DIR/scripts/reseason.py" prepare "$@"
