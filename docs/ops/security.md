# Bảo mật

**Trạng thái:** Sẵn sàng

- Không commit `.env`, API key, hoặc weights chứa dữ liệu nhạy cảm.
- Validate `source` file: từ chối `..` traversal.
- Inspector mặc định chỉ `127.0.0.1`. Khi mở LAN (`inspector.host: 0.0.0.0`),
  phải khai báo subnet được phép trong `inspector.allow_networks`.
- Mọi endpoint dữ liệu (`/api/state`, `/api/cameras`, `/api/metrics`) trả `403`
  cho client ngoài `allow_networks` (loopback luôn được phép). `/` và
  `/api/health` là công khai.
- Token tùy chọn: đặt `SMART_PARKING_INSPECTOR_TOKEN` (khuyến nghị, không ghi
  token vào YAML). Khi bật, client gửi header `X-API-Token` hoặc
  `Authorization: Bearer <token>`. Dashboard: `http://<server>:8765/?token=<token>`.
- Giai đoạn 2 API: rate-limit, auth đầy đủ, giới hạn upload.
- RTSP: chỉ trong LAN; không expose Internet trần.

Ví dụ cấu hình LAN:

```yaml
inspector:
  enabled: true
  host: 0.0.0.0
  port: 8765
  allow_networks:
    - 127.0.0.0/8
    - 192.168.100.0/24
```

```bash
# Tùy chọn: bật token (không commit)
export SMART_PARKING_INSPECTOR_TOKEN="$(openssl rand -hex 24)"
curl -H "X-API-Token: $SMART_PARKING_INSPECTOR_TOKEN" \
  http://192.168.100.239:8765/api/state
```

Nên kết hợp firewall ở tầng OS (ví dụ `ufw allow from 192.168.100.0/24 to any port 8765 proto tcp`).

## Checklist review

- [x] Chính sách path và secret
- [x] Inspector giới hạn loopback/allowlist + token tùy chọn
