# Huấn luyện

**Trạng thái:** Sẵn sàng

1. Upload Roboflow; đặt `ROBOFLOW_API_KEY` trong `.env`.
2. Train YOLO11n/s trên GPU x86; YOLO11m nếu VRAM đủ.
3. Export `best.pt` → `models/parking_yolo11.pt`.

```bash
yolo train data=dataset.yaml model=yolo11s.pt epochs=100 imgsz=640 device=0
```

Helper: `scripts/roboflow_train.py`

MLflow (một run / lần train):

```bash
pip install -e ".[mlflow]"
python scripts/roboflow_train.py --workspace WS --project parking --version 3 \
  --model yolo11s.pt --config configs/default.yaml --mlflow
```

Ghi: `data.yaml`, tags `dataset` / `dataset_version`, `model_version`, optional pipeline YAML.

## Checklist review

- [x] Không commit secret
- [x] Đường export
