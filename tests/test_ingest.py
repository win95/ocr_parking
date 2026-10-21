import os

from smart_parking.ingest.sources import (
    VideoSource,
    WebcamSource,
    _apply_capture_options,
    _parse_capture_options,
    is_live_source,
    parse_source,
)


def test_parse_webcam() -> None:
    src = parse_source("webcam:0")
    assert isinstance(src, WebcamSource)


def test_parse_video() -> None:
    src = parse_source("data/sample.mp4")
    assert isinstance(src, VideoSource)


def test_parse_rtsp_is_live() -> None:
    src = parse_source("rtsp://192.168.1.10:8554/parking")
    assert isinstance(src, VideoSource)
    assert src.is_live is True


def test_file_source_is_not_live() -> None:
    src = parse_source("data/sample.mp4")
    assert src.is_live is False


def test_is_live_source() -> None:
    assert is_live_source("rtsp://host:8554/stream") is True
    assert is_live_source("webcam:2") is True
    assert is_live_source("data/sample.mp4") is False


def test_parse_capture_options_uses_avdict_syntax() -> None:
    """OpenCV parses this env var as av_dict: 'key;value' pairs joined by '|'."""
    parsed = _parse_capture_options("rtsp_transport;tcp|timeout;8000000")
    assert parsed == {"rtsp_transport": "tcp", "timeout": "8000000"}


def test_apply_capture_options_format(monkeypatch) -> None:
    """The value must stay in av_dict syntax or the capture fails to open."""
    monkeypatch.delenv("OPENCV_FFMPEG_CAPTURE_OPTIONS", raising=False)
    _apply_capture_options("tcp", 8000)
    raw = os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"]
    assert raw == "rtsp_transport;tcp|timeout;8000000"
    assert _parse_capture_options(raw) == {
        "rtsp_transport": "tcp",
        "timeout": "8000000",
    }


def test_apply_capture_options_preserves_user_options(monkeypatch) -> None:
    monkeypatch.setenv("OPENCV_FFMPEG_CAPTURE_OPTIONS", "max_delay;5000000")
    _apply_capture_options("tcp", 8000)
    parsed = _parse_capture_options(os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"])
    assert parsed["max_delay"] == "5000000"
    assert parsed["rtsp_transport"] == "tcp"
    assert parsed["timeout"] == "8000000"


def test_apply_capture_options_overrides_existing_keys(monkeypatch) -> None:
    monkeypatch.setenv("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;udp|timeout;1000")
    _apply_capture_options("tcp", 8000)
    parsed = _parse_capture_options(os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"])
    assert parsed["rtsp_transport"] == "tcp"
    assert parsed["timeout"] == "8000000"
