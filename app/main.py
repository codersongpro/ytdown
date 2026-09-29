"""ytdown 로컬 웹앱 (FastAPI)."""

from __future__ import annotations

import shutil
import tempfile
import threading
import time
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import downloader
from .downloader import DownloaderError

BASE_DIR = Path(__file__).resolve().parent
# 실행파일(exe)로 묶였을 때도 쓸 수 있도록 OS 임시 폴더 사용
DOWNLOAD_DIR = Path(tempfile.gettempdir()) / "ytdown"
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
    for jid in expired:
        shutil.rmtree(DOWNLOAD_DIR / jid, ignore_errors=True)


def _run_job(job_id: str, req: DownloadRequest, title: str) -> None:
    out_dir = DOWNLOAD_DIR / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    _update(job_id, status="queued")
    with _slots:
        _update(job_id, status="downloading")
        try:
            path = downloader.download(
                req.url,
                req.format,
                req.quality,
                out_dir,
                on_progress=lambda pct, st: _update(job_id, progress=round(pct, 1), status=st),
            )
        except DownloaderError as e:
            _update(job_id, status="error", error=str(e))
            shutil.rmtree(out_dir, ignore_errors=True)
            return
        except Exception:  # noqa: BLE001
            _update(job_id, status="error", error="알 수 없는 오류가 발생했습니다.")
            shutil.rmtree(out_dir, ignore_errors=True)
            return
    _update(
        job_id,
        status="done",
        progress=100.0,
        path=str(path),
        filename=downloader.safe_filename(title, req.format),
    )


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
        downloader.extract_video_id(req.url)
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
        return {k: job.get(k) for k in ("status", "progress", "error", "filename")}


@app.get("/api/file/{job_id}")
def api_file(job_id: str, background: BackgroundTasks):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job or job.get("status") != "done":
        raise HTTPException(status_code=404, detail="파일이 준비되지 않았습니다.")

    def remove() -> None:
        with _jobs_lock:
            _jobs.pop(job_id, None)
        shutil.rmtree(DOWNLOAD_DIR / job_id, ignore_errors=True)

    background.add_task(remove)
    media = "video/mp4" if job["path"].endswith(".mp4") else "audio/mpeg"
    return FileResponse(job["path"], media_type=media, filename=job["filename"])


app.mount("/", StaticFiles(directory=BASE_DIR / "static", html=True), name="static")
