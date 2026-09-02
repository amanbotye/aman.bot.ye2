#!/usr/bin/env bash
set -euo pipefail
alembic upgrade head
if [[ -n "${SANDBOX_DATABASE_URL:-}" ]]; then
  if [[ "${SANDBOX_DATABASE_URL}" == "${DATABASE_URL}" ]]; then
    echo "SANDBOX_DATABASE_URL must differ from DATABASE_URL" >&2
    exit 1
  fi
  DATABASE_URL="$SANDBOX_DATABASE_URL" alembic upgrade head
fi
exec python main.py
