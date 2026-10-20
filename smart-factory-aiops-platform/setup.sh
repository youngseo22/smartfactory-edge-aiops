#!/usr/bin/env bash
# 가상환경(backend/.venv) 생성 + 백엔드/프론트엔드 의존성 설치
#   ./setup.sh          # 기본(mock 모드)
#   ./setup.sh --gcp    # GCP 연동 패키지까지 설치
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
  if command -v python >/dev/null 2>&1; then
    PY="python"
  fi
fi

"$PY" -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ 필요"'

# Windows Git Bash 및 Linux/macOS venv 파이썬 위치 대응
VENV_PY="backend/.venv/bin/python"
if [ ! -f "$VENV_PY" ] && [ -f "backend/.venv/Scripts/python.exe" ]; then
  VENV_PY="backend/.venv/Scripts/python.exe"
fi

if [ ! -f "$VENV_PY" ]; then
  echo "▶ 가상환경 생성: backend/.venv"
  "$PY" -m venv backend/.venv
  if [ -f "backend/.venv/bin/python" ]; then
    VENV_PY="backend/.venv/bin/python"
  else
    VENV_PY="backend/.venv/Scripts/python.exe"
  fi
fi

if [ ! -f .env ] && [ -f .env.example ]; then
  echo "▶ .env.example -> .env 복사 생성"
  cp .env.example .env
fi

REQ=requirements.txt; [ "${1:-}" = "--gcp" ] && REQ=requirements-gcp.txt
echo "▶ 백엔드 의존성 설치 ($REQ)"
"$VENV_PY" -m pip install --upgrade pip
"$VENV_PY" -m pip install -r "backend/$REQ"

echo "▶ 프론트엔드 의존성 설치"
(cd frontend && npm install)
echo "✔ 완료 — ./run_backend.sh 와 ./run_frontend.sh 를 각각 실행하세요."
