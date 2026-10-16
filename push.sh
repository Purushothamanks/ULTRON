#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

MSG="${1:-Update Ultron Command Matrix}"

echo "==> Staging all project changes (ignoring .env)..."
git add .

if git diff-index --quiet HEAD --; then
    echo "==> No unstaged or uncommitted changes found."
else
    echo "==> Committing: $MSG"
    git commit -m "$MSG"
fi

echo "==> Pushing to origin main..."
git push origin main

echo "==> Successfully pushed to GitHub!"
