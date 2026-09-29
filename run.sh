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
URL="http://127.0.0.1:8000"
( sleep 2; (open "$URL" 2>/dev/null || xdg-open "$URL" 2>/dev/null || true) ) &
echo "브라우저에서 $URL 을 여세요. 종료: Ctrl+C"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
