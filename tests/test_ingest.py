from smart_parking.ingest.sources import VideoSource, WebcamSource, parse_source


def test_parse_webcam() -> None:
    src = parse_source("webcam:0")
    assert isinstance(src, WebcamSource)


def test_parse_video() -> None:
    src = parse_source("data/sample.mp4")
    assert isinstance(src, VideoSource)
