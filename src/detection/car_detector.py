# Detector de carros usando YOLO (Ultralytics) – desenha caixas verdes no frame
from __future__ import annotations

from typing import Any

_DETECTION_AVAILABLE = False
_YOLO_MODEL = None


def _check_dependencies() -> bool:
    global _DETECTION_AVAILABLE
    if _DETECTION_AVAILABLE:
        return True
    try:
        import cv2  # noqa: F401
        import numpy as np  # noqa: F401
        from ultralytics import YOLO  # noqa: F401
        _DETECTION_AVAILABLE = True
        return True
    except ImportError:
        return False


def is_detection_available() -> bool:
    """Retorna True se ultralytics/opencv estão instalados e a detecção pode ser usada."""
    return _check_dependencies()


def _get_model(model_path: str | None = None):
    global _YOLO_MODEL
    if _YOLO_MODEL is not None:
        return _YOLO_MODEL
    from ultralytics import YOLO
    path = model_path or "yolov8n.pt"
    _YOLO_MODEL = YOLO(path)
    return _YOLO_MODEL


class CarDetector:
    """
    Detecta carros em imagens e desenha caixas verdes.
    Se ultralytics/opencv não estiverem instalados, detect() retorna [] e annotate() devolve a imagem original.
    """

    # COCO class index for "car"
    COCO_CLASS_CAR = 2

    def __init__(self, model_path: str | None = None, confidence_threshold: float = 0.5):
        self.model_path = model_path
        self.confidence_threshold = max(0.0, min(1.0, confidence_threshold))
        self._model = None

    def _ensure_model(self) -> bool:
        if not _check_dependencies():
            return False
        if self._model is None:
            try:
                self._model = _get_model(self.model_path)
            except Exception:
                return False
        return True

    def detect(self, image_bytes_or_ndarray: bytes | Any) -> list[dict]:
        """
        Retorna lista de detecções: [{"class": "car", "bbox": [x1,y1,x2,y2], "confidence": float}, ...].
        Retorna [] se dependências não disponíveis ou em caso de erro.
        """
        if not self._ensure_model():
            return []
        import cv2
        import numpy as np

        img = self._to_ndarray(image_bytes_or_ndarray)
        if img is None:
            return []

        try:
            # Apenas classe "car" (COCO index 2)
            results = self._model.predict(
                img,
                classes=[self.COCO_CLASS_CAR],
                conf=self.confidence_threshold,
                verbose=False,
            )
        except Exception:
            return []

        detections = []
        for r in results:
            if r.boxes is None:
                continue
            for i, box in enumerate(r.boxes):
                conf = float(box.conf.item()) if box.conf.numel() else 0.0
                if conf < self.confidence_threshold:
                    continue
                xyxy = box.xyxy[0].cpu().numpy()
                x1, y1, x2, y2 = float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])
                cls_id = int(box.cls.item()) if box.cls.numel() else self.COCO_CLASS_CAR
                name = r.names.get(cls_id, "car")
                detections.append({
                    "class": name,
                    "bbox": [x1, y1, x2, y2],
                    "confidence": conf,
                })
        return detections

    def _to_ndarray(self, image_bytes_or_ndarray: bytes | Any):
        import cv2
        import numpy as np

        if isinstance(image_bytes_or_ndarray, bytes):
            buf = np.frombuffer(image_bytes_or_ndarray, dtype=np.uint8)
            img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            return img
        if hasattr(image_bytes_or_ndarray, "__array__"):
            arr = np.asarray(image_bytes_or_ndarray)
            if arr.ndim == 2:
                return cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
            if arr.ndim == 3:
                return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR) if arr.shape[2] == 3 else arr
        return None

    def annotate(
        self,
        image_bytes_or_ndarray: bytes | Any,
        detections: list[dict] | None = None,
        *,
        format: str = "jpeg",
        quality: int = 85,
    ) -> bytes:
        """
        Desenha caixas verdes na imagem e retorna os bytes (JPEG por padrão).
        Se detections for None, chama detect() internamente.
        Em caso de falha ou dependências ausentes, retorna a imagem original (bytes).
        """
        import cv2
        import numpy as np

        img = self._to_ndarray(image_bytes_or_ndarray)
        if img is None and isinstance(image_bytes_or_ndarray, bytes):
            return image_bytes_or_ndarray
        if img is None:
            return b""

        if detections is None and self._ensure_model():
            detections = self.detect(img)
        elif detections is None:
            detections = []

        for d in detections:
            bbox = d.get("bbox")
            if not bbox or len(bbox) < 4:
                continue
            x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = d.get("class", "car")
            conf = d.get("confidence", 0)
            text = f"{label} {conf:.2f}"
            cv2.putText(
                img, text, (x1, y1 - 6),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5, (0, 255, 0), 1, cv2.LINE_AA,
            )

        if format.lower() in ("jpeg", "jpg"):
            ext = ".jpg"
            params = [cv2.IMWRITE_JPEG_QUALITY, max(1, min(100, quality))]
        else:
            ext = ".png"
            params = []
        ok, encoded = cv2.imencode(ext, img, params)
        if not ok:
            if isinstance(image_bytes_or_ndarray, bytes):
                return image_bytes_or_ndarray
            return b""
        return encoded.tobytes()
