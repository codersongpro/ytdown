import pytest

from app.downloader import (
    DownloaderError,
    build_opts,
    extract_video_id,
    friendly_error,
    safe_filename,
    unique_path,
)

VID = "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "url",
    [
        f"https://www.youtube.com/watch?v={VID}",
        f"https://youtube.com/watch?v={VID}&list=PL123&t=10s",
        f"https://m.youtube.com/watch?v={VID}",
        f"https://music.youtube.com/watch?v={VID}",
        f"https://youtu.be/{VID}?si=abc",
        f"https://www.youtube.com/shorts/{VID}",
        f"https://www.youtube.com/embed/{VID}",
        f"www.youtube.com/watch?v={VID}",
        f"  https://youtu.be/{VID}  ",
    ],
)
def test_extract_video_id_valid(url):
    assert extract_video_id(url) == VID


@pytest.mark.parametrize(
    "url",
    [
        "",
        "https://vimeo.com/12345",
        "https://evil.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/",
        "https://www.youtube.com/playlist?list=PL123",
        "https://www.youtube.com/watch?v=short",
        "https://youtube.com.evil.com/watch?v=dQw4w9WgXcQ",
    ],
)
def test_extract_video_id_invalid(url):
    with pytest.raises(DownloaderError):
        extract_video_id(url)


def test_build_opts_mp4(tmp_path):
    opts = build_opts("mp4", "720", tmp_path)
    assert "[height<=720]" in opts["format"]
    assert opts["merge_output_format"] == "mp4"
    assert opts["noplaylist"] is True


def test_build_opts_mp4_best_has_no_limit(tmp_path):
    assert "height" not in build_opts("mp4", "best", tmp_path)["format"]


def test_build_opts_mp3(tmp_path):
    pp = build_opts("mp3", "192", tmp_path)["postprocessors"][0]
    assert pp["key"] == "FFmpegExtractAudio"
    assert pp["preferredcodec"] == "mp3"
    assert pp["preferredquality"] == "192"


@pytest.mark.parametrize("fmt,q", [("mp4", "4320"), ("mp3", "999"), ("avi", "720")])
def test_build_opts_rejects_bad_input(tmp_path, fmt, q):
    with pytest.raises(DownloaderError):
        build_opts(fmt, q, tmp_path)


def test_safe_filename():
    assert safe_filename('a/b:c*d?"e<f>g|h', "mp3") == "abcdefgh.mp3"
    assert safe_filename("", "mp4") == "download.mp4"
    assert safe_filename("수업 자료  영상", "mp4") == "수업 자료 영상.mp4"


def test_friendly_error_messages():
    assert "비공개" in friendly_error(Exception("ERROR: Private video"))
    assert "삭제" in friendly_error(Exception("Video unavailable"))
    assert "막았" in friendly_error(Exception("Sign in to confirm you're not a bot"))


def test_friendly_error_certificate():
    err = Exception(
        "ERROR: [youtube] 393-FVtpLPc: Unable to download API page: [SSL: CERTIFICATE_VERIFY_FAILED] "
        "certificate verify failed: self-signed certificate in certificate chain"
    )
    assert "인증서" in friendly_error(err)


def test_friendly_error_unknown_shows_detail():
    msg = friendly_error(Exception("ERROR: something odd happened; please report this issue on https://x"))
    assert "something odd happened" in msg
    assert "please report" not in msg


def test_unique_path(tmp_path):
    assert unique_path(tmp_path, "a.mp3") == tmp_path / "a.mp3"
    (tmp_path / "a.mp3").touch()
    assert unique_path(tmp_path, "a.mp3") == tmp_path / "a (1).mp3"
    (tmp_path / "a (1).mp3").touch()
    assert unique_path(tmp_path, "a.mp3") == tmp_path / "a (2).mp3"
