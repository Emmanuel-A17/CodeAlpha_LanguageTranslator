"""
SORT (Simple Online and Realtime Tracking), écrit en NumPy pur.

Pour chaque image :
  1. chaque objet suivi « prédit » sa nouvelle position (filtre de Kalman : position + vitesse) ;
  2. on associe les détections aux objets suivis selon leur recouvrement (IoU), avec l'algorithme hongrois ;
  3. les objets associés sont corrigés ; les détections sans objet deviennent de nouveaux suivis ;
  4. un suivi qui n'est plus vu pendant `max_age` images est supprimé.
Chaque suivi garde un identifiant stable, et la classe la plus souvent détectée.
"""

from collections import Counter

import numpy as np


def iou_matrix(a, b):
    """IoU entre deux listes de boîtes [x1, y1, x2, y2] -> matrice (len(a), len(b))."""
    a, b = np.asarray(a, float).reshape(-1, 4), np.asarray(b, float).reshape(-1, 4)
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)))
    x1 = np.maximum(a[:, None, 0], b[None, :, 0])
    y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2])
    y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    area_a = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1])
    area_b = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / (area_a[:, None] + area_b[None, :] - inter + 1e-9)


def hungarian(cost):
    """Affectation de coût minimal (algorithme hongrois). Retourne la liste de paires (ligne, colonne)."""
    cost = np.asarray(cost, float)
    if cost.size == 0:
        return []
    transposed = cost.shape[0] > cost.shape[1]
    if transposed:
        cost = cost.T
    n, m = cost.shape                      # n <= m
    u, v = np.zeros(n + 1), np.zeros(m + 1)
    p, way = np.zeros(m + 1, int), np.zeros(m + 1, int)
    for i in range(1, n + 1):
        p[0], j0 = i, 0
        minv, used = np.full(m + 1, np.inf), np.zeros(m + 1, bool)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], np.inf, 0
            for j in range(1, m + 1):
                if not used[j]:
                    cur = cost[i0 - 1, j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j], way[j] = cur, j0
                    if minv[j] < delta:
                        delta, j1 = minv[j], j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
    pairs = [(p[j] - 1, j - 1) for j in range(1, m + 1) if p[j] > 0]
    return [(c, r) for r, c in pairs] if transposed else pairs


def to_z(box):
    w, h = box[2] - box[0], box[3] - box[1]
    return np.array([box[0] + w / 2, box[1] + h / 2, w * h, w / max(h, 1e-6)])


def to_box(x):
    w = np.sqrt(max(x[2] * x[3], 1e-6))
    h = x[2] / w
    return np.array([x[0] - w / 2, x[1] - h / 2, x[0] + w / 2, x[1] + h / 2])


class KalmanBox:
    """Filtre de Kalman d'une boîte. État : [cx, cy, aire, ratio, vx, vy, v_aire]."""
    _next_id = 0

    def __init__(self, box, label):
        self.x = np.zeros(7)
        self.x[:4] = to_z(box)
        self.P = np.diag([10, 10, 10, 10, 1e4, 1e4, 1e4]).astype(float)
        self.F = np.eye(7)
        self.F[0, 4] = self.F[1, 5] = self.F[2, 6] = 1
        self.H = np.eye(4, 7)
        self.R = np.diag([1, 1, 10, 10]).astype(float)
        self.Q = np.diag([1, 1, 1, 1, 0.01, 0.01, 1e-4]).astype(float)
        KalmanBox._next_id += 1
        self.id = KalmanBox._next_id
        self.labels = Counter([label])
        self.hits, self.streak, self.since_update = 1, 1, 0

    def predict(self):
        if self.x[6] + self.x[2] <= 0:
            self.x[6] = 0
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        self.since_update += 1
        if self.since_update > 1:
            self.streak = 0
        return to_box(self.x)

    def update(self, box, label):
        y = to_z(box) - self.H @ self.x
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (np.eye(7) - K @ self.H) @ self.P
        self.labels[label] += 1
        self.hits += 1
        self.streak += 1
        self.since_update = 0

    @property
    def box(self):
        return to_box(self.x)

    @property
    def label(self):
        return self.labels.most_common(1)[0][0]


class Sort:
    def __init__(self, max_age=20, min_hits=3, iou_threshold=0.25):
        self.max_age, self.min_hits, self.iou_threshold = max_age, min_hits, iou_threshold
        self.tracks = []
        self.frame = 0

    def update(self, detections):
        """detections : liste de (x1, y1, x2, y2, score, classe). Retourne [(x1, y1, x2, y2, id, classe, score)]."""
        self.frame += 1
        predicted = [t.predict() for t in self.tracks]
        boxes = [d[:4] for d in detections]

        matches, matched_t, matched_d = [], set(), set()
        if predicted and boxes:
            iou = iou_matrix(predicted, boxes)
            for t, d in hungarian(-iou):
                if iou[t, d] >= self.iou_threshold:
                    matches.append((t, d))
                    matched_t.add(t)
                    matched_d.add(d)

        scores = {}
        for t, d in matches:
            self.tracks[t].update(boxes[d], detections[d][5])
            scores[self.tracks[t].id] = detections[d][4]
        for d, det in enumerate(detections):
            if d not in matched_d:
                track = KalmanBox(boxes[d], det[5])
                self.tracks.append(track)
                scores[track.id] = det[4]

        output = []
        for t in self.tracks:
            visible = t.since_update == 0
            confirmed = t.hits >= self.min_hits or self.frame <= self.min_hits
            if visible and confirmed:
                x1, y1, x2, y2 = t.box
                output.append((x1, y1, x2, y2, t.id, t.label, scores.get(t.id, 0.0)))
        self.tracks = [t for t in self.tracks if t.since_update <= self.max_age]
        return output
