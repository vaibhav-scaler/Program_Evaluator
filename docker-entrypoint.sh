#!/bin/sh
set -e

# Metabase settings come from environment variables only (set them in the host's dashboard, never in git).
# These two are internal identifiers, not secrets, and keep their old defaults when unset.
export METABASE_CARD_ID="${METABASE_CARD_ID:-28973}"
export METABASE_EMAIL_PARAM_ID="${METABASE_EMAIL_PARAM_ID:-2dcd8f80-e4b6-46cf-936b-2102140cb7f2}"

# Make sure the data folders exist (a mounted volume may start empty)
mkdir -p /app/data /app/output

echo ">> Starting Scaler Program Evaluator on port ${PORT:-8000}..."
exec python run_app.py
