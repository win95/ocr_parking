# Module ingest

**Trạng thái:** Đã triển khai  
**Code:** `smart_parking.ingest`

## Mục đích

Đọc frame từ file video, webcam hoặc RTSP; tùy chọn bỏ frame khi backlog.

## API

- `parse_source(spec: str) -> VideoSource | WebcamSource`
- `FrameLoop(source, max_queue=1)` → lặp frame với `frame_id`, `timestamp_ms`, `image`

## Cấu hình

`source` trong YAML.

## Lỗi

- File không tồn tại → lỗi rõ khi mở.
- Webcam lỗi → gợi ý `v4l2-ctl`.

## Kiểm thử

- Parse `webcam:0` và đường dẫn file.
- `frame_id` tăng dần.

## Checklist review

- [x] API đã liệt kê
- [x] Trường hợp lỗi
