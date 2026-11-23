"""Détecteur d'objets YOLOv4-tiny (80 classes COCO) via le module « dnn » d'OpenCV. Pas besoin de PyTorch."""

from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"

COCO = ("person bicycle car motorbike aeroplane bus train truck boat traffic-light fire-hydrant stop-sign "
        "parking-meter bench bird cat dog horse sheep cow elephant bear zebra giraffe backpack umbrella handbag tie "
        "suitcase frisbee skis snowboard sports-ball kite baseball-bat baseball-glove skateboard surfboard "
        "tennis-racket bottle wine-glass cup fork knife spoon bowl banana apple sandwich orange broccoli carrot "
        "hot-dog pizza donut cake chair sofa pottedplant bed diningtable toilet tvmonitor laptop mouse remote "
        "keyboard cell-phone microwave oven toaster sink refrigerator book clock vase scissors teddy-bear "
        "hair-drier toothbrush").split()
CLASS_NAMES = [name.replace("-", " ") for name in COCO]
assert len(CLASS_NAMES) == 80


class YoloDetector:
    def __init__(self, conf=0.4, nms=0.45, size=416, classes=None):
        import cv2
        self.cv2 = cv2
        cfg, weights = MODELS / "yolov4-tiny.cfg", MODELS / "yolov4-tiny.weights"
        if not weights.exists():
            raise FileNotFoundError(f"Poids du modèle introuvables : {weights}")
        if not hasattr(cv2.dnn, "readNetFromDarknet"):
            raise RuntimeError("Votre version d'OpenCV est trop récente (5.x). Lancez : "
                               "pip install \"opencv-python>=4.8,<5\"")
        self.net = cv2.dnn.readNetFromDarknet(str(cfg), str(weights))
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        self.outputs = self.net.getUnconnectedOutLayersNames()
        self.conf, self.nms, self.size = conf, nms, size
        self.classes = set(classes) if classes else None     # None = toutes les classes

    def detect(self, frame):
        """Retourne [(x1, y1, x2, y2, score, nom_de_classe)] en pixels de l'image."""
        cv2 = self.cv2
        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, 1 / 255.0, (self.size, self.size), swapRB=True, crop=False)
        self.net.setInput(blob)
        boxes, scores, ids = [], [], []
        for out in self.net.forward(self.outputs):
            for row in out:                                   # row = [cx, cy, w, h, objectness, 80 scores]
                class_scores = row[5:]
                cid = int(np.argmax(class_scores))
                score = float(row[4] * class_scores[cid])
                if score < self.conf:
                    continue
                if self.classes and CLASS_NAMES[cid] not in self.classes:
                    continue
                bw, bh = row[2] * w, row[3] * h
                boxes.append([int(row[0] * w - bw / 2), int(row[1] * h - bh / 2), int(bw), int(bh)])
                scores.append(score)
                ids.append(cid)
        keep = cv2.dnn.NMSBoxes(boxes, scores, self.conf, self.nms) if boxes else []
        result = []
        for i in np.array(keep).flatten():
            x, y, bw, bh = boxes[i]
            result.append((max(x, 0), max(y, 0), min(x + bw, w), min(y + bh, h), scores[i], CLASS_NAMES[ids[i]]))
        return result
