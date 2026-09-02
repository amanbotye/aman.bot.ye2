#!/bin/sh
set -eu
alembic upgrade head
exec python main.py
