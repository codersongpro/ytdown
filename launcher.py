"""ytdown 실행 진입점: 내부 서버를 켜고 프로그램 창(pywebview) 안에 화면을 띄운다."""

from __future__ import annotations

import os
import shutil
import socket
import sys
import threading
import time
import traceback
from pathlib import Path

HOST = "127.0.0.1"
LOG_FILE = Path.home() / ".ytdown" / "ytdown.log"


def _redirect_output_if_windowed() -> None:
    # 콘솔 없는 실행파일에서는 stdout/stderr가 None이라 로그 출력 시 오류가 난다
    if sys.stdout is None or sys.stderr is None:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        log = open(LOG_FILE, "a", encoding="utf-8", buffering=1)  # noqa: SIM115
        sys.stdout = sys.stdout or log
        sys.stderr = sys.stderr or log


_redirect_output_if_windowed()

import uvicorn  # noqa: E402

from app.main import DOWNLOAD_DIR, app  # noqa: E402


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


def wait_until_ready(port: int, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((HOST, port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError("내부 서버가 시작되지 않았습니다.")


class Api:
    """화면(JS)에서 window.pywebview.api.* 로 부르는 기능."""

    def choose_folder(self) -> str | None:
        import webview

        result = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
        return result[0] if result else None


def main() -> None:
    shutil.rmtree(DOWNLOAD_DIR, ignore_errors=True)  # 이전 실행에서 남은 임시 파일 정리

    port = find_free_port()
    url = f"http://{HOST}:{port}"
    server = uvicorn.Server(uvicorn.Config(app, host=HOST, port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    wait_until_ready(port)

    if "--browser" in sys.argv:
        import webbrowser

        webbrowser.open(url)
        print(f"{url} 에서 실행 중입니다. 종료: Ctrl+C")
        threading.Event().wait()
        return

    import webview

    webview.create_window("ytdown", url, js_api=Api(), width=560, height=860, min_size=(380, 600))
    webview.start()
    # 창을 닫으면 서버 스레드와 진행 중인 작업까지 모두 종료
    os._exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        raise
