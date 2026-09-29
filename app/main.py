"""ytdown 로컬 서버 (FastAPI). 데스크톱 창(launcher.py) 안에서 화면을 띄운다."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import downloader
from .downloader import DownloaderError

BASE_DIR = Path(__file__).resolve().parent
# 실행파일(exe)로 묶였을 때도 쓸 수 있도록 OS 임시 폴더 사용
DOWNLOAD_DIR = Path(tempfile.gettempdir()) / "ytdown"
CONFIG_DIR = Path.home() / ".ytdown"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
MAX_CONCURRENT = 2
JOB_TTL_SEC = 60 * 60

app = FastAPI(title="ytdown")

_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()
_slots = threading.Semaphore(MAX_CONCURRENT)


class InfoRequest(BaseModel):
    url: str


class DownloadRequest(BaseModel):
    url: str
    format: str  # "mp4" | "mp3"
    quality: str


class SettingsRequest(BaseModel):
    save_dir: str


class OpenRequest(BaseModel):
    job_id: str | None = None


def default_save_dir() -> Path:
    downloads = Path.home() / "Downloads"
    return downloads if downloads.is_dir() else Path.home()


def get_save_dir() -> Path:
    try:
        saved = Path(json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))["save_dir"])
        if saved.is_dir():
            return saved
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return default_save_dir()


def set_save_dir(path: Path) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps({"save_dir": str(path)}, ensure_ascii=False), encoding="utf-8")


def reveal_in_file_manager(path: Path) -> None:
    """탐색기/Finder에서 파일(또는 폴더)을 연다."""
    if sys.platform == "win32":
        if path.is_file():
            subprocess.Popen(["explorer", "/select,", str(path)])
        else:
            os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(path)] if path.is_file() else ["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path if path.is_dir() else path.parent)])


def _update(job_id: str, **fields) -> None:
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id].update(fields)


def _cleanup_old_jobs() -> None:
    now = time.time()
    with _jobs_lock:
        expired = [jid for jid, j in _jobs.items() if now - j["created"] > JOB_TTL_SEC]
        for jid in expired:
            _jobs.pop(jid, None)


def _run_job(job_id: str, req: DownloadRequest, title: str) -> None:
    work_dir = DOWNLOAD_DIR / job_id
    work_dir.mkdir(parents=True, exist_ok=True)
    try:
        with _slots:
            _update(job_id, status="downloading")
            media = downloader.download(
                req.url,
                req.format,
                req.quality,
                work_dir,
                on_progress=lambda pct, st: _update(job_id, progress=round(pct, 1), status=st),
            )
        save_dir = get_save_dir()
        save_dir.mkdir(parents=True, exist_ok=True)
        target = downloader.unique_path(save_dir, downloader.safe_filename(title, req.format))
        shutil.move(str(media), target)
        _update(job_id, status="done", progress=100.0, path=str(target), filename=target.name)
    except DownloaderError as e:
        _update(job_id, status="error", error=str(e))
    except Exception as e:  # noqa: BLE001
        _update(job_id, status="error", error=f"알 수 없는 오류가 발생했습니다. ({e})")
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


@app.post("/api/info")
def api_info(req: InfoRequest):
    try:
        return downloader.fetch_info(req.url)
    except DownloaderError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/download")
def api_download(req: DownloadRequest):
    _cleanup_old_jobs()
    try:
        downloader.build_opts(req.format, req.quality, DOWNLOAD_DIR)
        info = downloader.fetch_info(req.url)
    except DownloaderError as e:
        raise HTTPException(status_code=400, detail=str(e))

    job_id = uuid.uuid4().hex
    with _jobs_lock:
        _jobs[job_id] = {"status": "queued", "progress": 0.0, "created": time.time()}
    threading.Thread(target=_run_job, args=(job_id, req, info["title"]), daemon=True).start()
    return {"job_id": job_id}


@app.get("/api/progress/{job_id}")
def api_progress(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
        return {k: job.get(k) for k in ("status", "progress", "error", "filename", "path")}


@app.get("/api/settings")
def api_get_settings():
    return {"save_dir": str(get_save_dir())}


@app.post("/api/settings")
def api_set_settings(req: SettingsRequest):
    path = Path(req.save_dir).expanduser()
    if not path.is_dir():
        raise HTTPException(status_code=400, detail="존재하지 않는 폴더입니다.")
    set_save_dir(path)
    return {"save_dir": str(path)}


@app.post("/api/open")
def api_open(req: OpenRequest):
    path = get_save_dir()
    if req.job_id:
        with _jobs_lock:
            job_path = (_jobs.get(req.job_id) or {}).get("path")
        if job_path and Path(job_path).exists():
            path = Path(job_path)
    try:
        reveal_in_file_manager(path)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"폴더를 열 수 없습니다. ({e})")
    return {"ok": True}


app.mount("/", StaticFiles(directory=BASE_DIR / "static", html=True), name="static")
