#!/usr/bin/env bash
set -euo pipefail

backend_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$backend_dir"

compose=(docker compose --env-file .env.oracle -f docker-compose.oracle.yml)

"${compose[@]}" ps

curl --fail --silent --show-error http://127.0.0.1:8000/health
echo
curl --fail --silent --show-error http://127.0.0.1:8000/health/db
echo

"${compose[@]}" exec -T api python -c \
  "import platform, chromadb, torch; print({'arch': platform.machine(), 'torch': torch.__version__, 'chromadb': chromadb.__version__})"

"${compose[@]}" exec -T api python -c \
  "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(headless=True); print('playwright chromium: OK'); b.close(); p.stop()"

if [[ "${VERIFY_AI:-0}" == "1" ]]; then
  curl --fail --silent --show-error \
    -H "Content-Type: application/json" \
    -d '{"message":"오늘 학사일정을 한 문장으로 알려줘"}' \
    http://127.0.0.1:8000/api/ai/chat/demo
  echo
fi

echo "Oracle deployment verification passed"
