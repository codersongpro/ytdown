@echo off
chcp 65001 > nul
rem ytdown 실행 (Windows)
cd /d "%~dp0"
if not exist .venv (
  echo 처음 실행: 가상환경을 만드는 중...
  python -m venv .venv || (echo Python이 설치되어 있지 않습니다. https://www.python.org 에서 설치해 주세요. & pause & exit /b 1)
)
call .venv\Scripts\activate.bat
echo 필요한 프로그램 설치/업데이트 중...
python -m pip install -q -U pip
python -m pip install -q -U -r requirements.txt

echo ytdown 창이 열립니다.
python launcher.py
pause
