"""Frame sample buffer for fire/smoke worker."""

import numpy as np

from smart_parking.pipeline.frame_sample_buffer import FrameSampleBuffer


def test_buffer_peek_latest() -> None:
    buf = FrameSampleBuffer()
    img = np.zeros((4, 4, 3), dtype=np.uint8)
    buf.offer(1, 100.0, img)
    buf.offer(2, 200.0, img)
    sample = buf.peek()
    assert sample is not None
    assert sample.frame_id == 2
