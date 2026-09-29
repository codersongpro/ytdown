#!/usr/bin/env bash
# ytdown 실행 (macOS / Linux)
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "처음 실행: 가상환경을 만드는 중..."
  python3 -m venv .venv
fi
source .venv/bin/activate
echo "필요한 프로그램 설치/업데이트 중..."
pip install -q -U pip
pip install -q -U -r requirements.txt
echo "ytdown 창이 열립니다."
python launcher.py
