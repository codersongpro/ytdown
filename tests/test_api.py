import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import downloader, main


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "CONFIG_DIR", tmp_path / "cfg")
    monkeypatch.setattr(main, "SETTINGS_FILE", tmp_path / "cfg" / "settings.json")
    monkeypatch.setattr(main, "DOWNLOAD_DIR", tmp_path / "work")
    monkeypatch.setattr(main, "default_save_dir", lambda: tmp_path)
    return TestClient(main.app)


def test_settings_roundtrip(client, tmp_path):
    assert client.get("/api/settings").json()["save_dir"] == str(tmp_path)
    target = tmp_path / "music"
    target.mkdir()
    assert client.post("/api/settings", json={"save_dir": str(target)}).status_code == 200
    assert client.get("/api/settings").json()["save_dir"] == str(target)
    assert client.post("/api/settings", json={"save_dir": str(tmp_path / "nope")}).status_code == 400


def test_download_saves_into_save_dir(client, tmp_path, monkeypatch):
    monkeypatch.setattr(downloader, "fetch_info", lambda url: {"title": "수업: 자료?"})

    def fake_download(url, fmt, quality, out_dir, on_progress=None):
        on_progress(50.0, "downloading")
        p = Path(out_dir) / f"media.{fmt}"
        p.write_bytes(b"x")
        return p

    monkeypatch.setattr(downloader, "download", fake_download)
    for expected in ("수업 자료.mp3", "수업 자료 (1).mp3"):
        jid = client.post(
            "/api/download", json={"url": "https://youtu.be/dQw4w9WgXcQ", "format": "mp3", "quality": "192"}
        ).json()["job_id"]
        for _ in range(50):
            job = client.get(f"/api/progress/{jid}").json()
            if job["status"] == "done":
                break
            time.sleep(0.05)
        assert job["filename"] == expected
        assert (tmp_path / expected).exists()
    assert not any((tmp_path / "work").iterdir())  # 임시 폴더 정리됨


def test_download_error_is_reported(client, monkeypatch):
    monkeypatch.setattr(downloader, "fetch_info", lambda url: {"title": "t"})

    def boom(*a, **k):
        raise downloader.DownloaderError("보안 인증서 오류입니다.")

    monkeypatch.setattr(downloader, "download", boom)
    jid = client.post(
        "/api/download", json={"url": "https://youtu.be/dQw4w9WgXcQ", "format": "mp4", "quality": "720"}
    ).json()["job_id"]
    for _ in range(50):
        job = client.get(f"/api/progress/{jid}").json()
        if job["status"] == "error":
            break
        time.sleep(0.05)
    assert job["error"] == "보안 인증서 오류입니다."
