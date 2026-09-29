"""ytdown 실행파일 진입점: 빈 포트를 찾아 서버를 켜고 브라우저를 연다."""

from __future__ import annotations

import shutil
import socket
import sys
import threading
import time
import webbrowser

import uvicorn

from app.main import DOWNLOAD_DIR, app

HOST = "127.0.0.1"


def find_free_port(start: int = 8000, tries: int = 20) -> int:
    for port in range(start, start + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((HOST, port))
                return port
            except OSError:
                continue
    raise RuntimeError("사용할 수 있는 포트를 찾지 못했습니다.")


def open_browser_when_ready(url: str, port: int) -> None:
    for _ in range(50):
        try:
            with socket.create_connection((HOST, port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.2)
    webbrowser.open(url)


def main() -> None:
    # 이전 실행에서 남은 임시 파일 정리
    shutil.rmtree(DOWNLOAD_DIR, ignore_errors=True)

    port = find_free_port()
    url = f"http://{HOST}:{port}"
    print("=" * 50)
    print(" ytdown 실행 중")
    print(f" 브라우저에서 {url} 을 여세요.")
    print(" 종료하려면 이 창을 닫으세요.")
    print("=" * 50)
    threading.Thread(target=open_browser_when_ready, args=(url, port), daemon=True).start()
    uvicorn.run(app, host=HOST, port=port, log_level="warning")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"오류: {e}")
        if getattr(sys, "frozen", False):
            input("Enter 키를 누르면 종료합니다.")
        raise
