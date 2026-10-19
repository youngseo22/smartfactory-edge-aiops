#!/usr/bin/env bash
# 가상환경의 Python 으로 백엔드 실행 (활성화 불필요)
set -euo pipefail
cd "$(dirname "$0")/backend"

VENV_PY=".venv/bin/python"
if [ ! -f "$VENV_PY" ] && [ -f ".venv/Scripts/python.exe" ]; then
  VENV_PY=".venv/Scripts/python.exe"
fi

if [ ! -f "$VENV_PY" ]; then
  echo "오류: 가상환경 파이썬을 찾을 수 없습니다. 먼저 ./setup.sh 를 실행하세요."
  exit 1
fi

exec "$VENV_PY" -m uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" "$@"
