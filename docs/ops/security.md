# Bảo mật

**Trạng thái:** Sẵn sàng

- Không commit `.env`, API key, hoặc weights chứa dữ liệu nhạy cảm.
- Validate `source` file: từ chối `..` traversal.
- API Inspector: mặc định localhost; `/api/state` chặn client không phải loopback.
- Giai đoạn 2 API: rate-limit, auth, giới hạn upload.
- RTSP: chỉ trong LAN; không expose Internet trần.

## Checklist review

- [x] Chính sách path và secret
- [x] Inspector localhost
