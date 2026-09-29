"""yt-dlp 래퍼: URL 검증, 정보 조회, MP4/MP3 다운로드."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlparse

import imageio_ffmpeg
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

MAX_DURATION_SEC = 3 * 60 * 60  # 3시간
VIDEO_QUALITIES = {"best": None, "1080": 1080, "720": 720, "480": 480}
AUDIO_QUALITIES = {"320", "192", "128"}

_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
}
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


class DownloaderError(Exception):
    """사용자에게 그대로 보여줄 수 있는 한글 오류."""


def extract_video_id(url: str) -> str:
    """유튜브 단일 영상 URL에서 영상 ID를 뽑는다. 아니면 DownloaderError."""
    url = (url or "").strip()
    if not re.match(r"^https?://", url):
        url = "https://" + url
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host not in _YOUTUBE_HOSTS:
        raise DownloaderError("유튜브 주소만 입력할 수 있습니다.")

    video_id = None
    parts = [p for p in parsed.path.split("/") if p]
    if host == "youtu.be":
        video_id = parts[0] if parts else None
    elif parts[:1] == ["watch"]:
        video_id = parse_qs(parsed.query).get("v", [None])[0]
    elif len(parts) >= 2 and parts[0] in ("shorts", "embed", "live", "v"):
        video_id = parts[1]

    if not video_id or not _VIDEO_ID_RE.match(video_id):
        raise DownloaderError("영상 주소를 인식하지 못했습니다. 영상 페이지 주소를 복사해 주세요.")
    return video_id


def canonical_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def safe_filename(title: str, ext: str) -> str:
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", title or "").strip(" .")
    name = re.sub(r"\s+", " ", name)[:120] or "download"
    return f"{name}.{ext}"


def _base_opts() -> dict:
    return {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
    }


def build_opts(fmt: str, quality: str, out_dir: Path) -> dict:
    """다운로드용 yt-dlp 옵션을 만든다."""
    opts = _base_opts()
    opts["outtmpl"] = str(out_dir / "media.%(ext)s")

    if fmt == "mp4":
        if quality not in VIDEO_QUALITIES:
            raise DownloaderError("지원하지 않는 화질입니다.")
        h = VIDEO_QUALITIES[quality]
        limit = f"[height<={h}]" if h else ""
        opts["format"] = (
            f"bestvideo[ext=mp4]{limit}+bestaudio[ext=m4a]/"
            f"bestvideo{limit}+bestaudio/"
            f"best[ext=mp4]{limit}/best{limit}/best"
        )
        opts["merge_output_format"] = "mp4"
        # 병합 결과가 mp4가 아닐 때(예: webm)도 mp4로 맞춘다
        opts["postprocessors"] = [{"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"}]
    elif fmt == "mp3":
        if quality not in AUDIO_QUALITIES:
            raise DownloaderError("지원하지 않는 음질입니다.")
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": quality}
        ]
    else:
        raise DownloaderError("MP4 또는 MP3만 선택할 수 있습니다.")
    return opts


def friendly_error(err: Exception) -> str:
    msg = str(err).lower()
    if "private" in msg:
        return "비공개 영상이라 받을 수 없습니다."
    if "sign in to confirm your age" in msg or ("age" in msg and "restrict" in msg):
        return "연령 제한 영상이라 받을 수 없습니다."
    if "not a bot" in msg or "sign in" in msg:
        return "유튜브가 요청을 일시적으로 막았습니다. 잠시 후 다시 시도하거나 yt-dlp를 업데이트해 주세요."
    if "unavailable" in msg or "removed" in msg or "does not exist" in msg:
        return "삭제되었거나 볼 수 없는 영상입니다."
    if "live" in msg and ("event" in msg or "stream" in msg):
        return "진행 중인 라이브 방송은 받을 수 없습니다."
    if "network" in msg or "timed out" in msg or "connection" in msg:
        return "네트워크 오류입니다. 인터넷 연결을 확인해 주세요."
    return "처리 중 오류가 발생했습니다. yt-dlp 업데이트 후 다시 시도해 주세요."


def fetch_info(url: str) -> dict:
    video_id = extract_video_id(url)
    try:
        with YoutubeDL(_base_opts()) as ydl:
            info = ydl.extract_info(canonical_url(video_id), download=False)
    except DownloadError as e:
        raise DownloaderError(friendly_error(e)) from e

    if info.get("is_live"):
        raise DownloaderError("진행 중인 라이브 방송은 받을 수 없습니다.")
    duration = info.get("duration") or 0
    if duration > MAX_DURATION_SEC:
        raise DownloaderError("3시간이 넘는 영상은 받을 수 없습니다.")
    return {
        "id": video_id,
        "title": info.get("title") or "",
        "channel": info.get("channel") or info.get("uploader") or "",
        "duration": duration,
        "thumbnail": info.get("thumbnail") or "",
    }


def download(
    url: str,
    fmt: str,
    quality: str,
    out_dir: Path,
    on_progress: Callable[[float, str], None] | None = None,
) -> Path:
    """영상을 받아 out_dir에 저장하고 결과 파일 경로를 돌려준다."""
    video_id = extract_video_id(url)
    opts = build_opts(fmt, quality, out_dir)

    def hook(d: dict) -> None:
        if not on_progress:
            return
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes") or 0
            on_progress((done / total * 100) if total else 0.0, "downloading")
        elif d.get("status") == "finished":
            on_progress(100.0, "processing")

    opts["progress_hooks"] = [hook]
    try:
        with YoutubeDL(opts) as ydl:
            ydl.download([canonical_url(video_id)])
    except DownloadError as e:
        raise DownloaderError(friendly_error(e)) from e

    result = out_dir / f"media.{fmt}"
    if not result.exists():
        raise DownloaderError("파일 변환에 실패했습니다.")
    return result
