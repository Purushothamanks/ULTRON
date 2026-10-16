#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Activate environment
if [ -d "/home/purushothaman/vision_env" ]; then
    source /home/purushothaman/vision_env/bin/activate
fi

# Start FastAPI server
echo "Starting Vision Command Console on http://localhost:8000 ..."
python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
