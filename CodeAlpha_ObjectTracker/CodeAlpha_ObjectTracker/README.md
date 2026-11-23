# 🎯 Tracker — Détection et suivi d'objets (CodeAlpha, Tâche 4)

Détection d'objets en temps réel avec **YOLOv4-tiny** (80 classes COCO : personne, voiture, chien…),
suivi avec **SORT** (filtre de Kalman + algorithme hongrois) et affichage des boîtes, étiquettes et **identifiants de suivi**.

| Consigne CodeAlpha | Où |
|---|---|
| Entrée vidéo webcam / fichier (OpenCV) | `objtrack/pipeline.py` |
| Modèle pré-entraîné YOLO | `objtrack/detector.py`, `models/` |
| Détection + boîtes sur chaque image | `detector.py`, `draw.py` |
| Suivi SORT | `objtrack/sort.py` (écrit en NumPy, sans scipy) |
| Affichage temps réel avec étiquettes et IDs | `track.py` (fenêtre) ou `app.py` (navigateur) |

## Installation (Windows / VSCode)
```powershell
pip install -r requirements.txt
```
OpenCV doit être en version **4.x** (la 5.x ne sait plus lire les modèles Darknet) : c'est déjà précisé dans `requirements.txt`.

## Lancer
**Interface web** (webcam ou fichier vidéo, statistiques en direct) :
```powershell
python app.py        # puis ouvrir http://127.0.0.1:5000
```
**Fenêtre OpenCV** :
```powershell
python track.py                                  # webcam
python track.py --source ma_video.mp4 --save sortie.mp4
python track.py --classes person car --conf 0.5 --every 2
```
`q` ou `Échap` pour quitter. `--every 2` détecte une image sur deux : plus fluide sur un ordinateur lent
(SORT prédit la position entre deux détections).

## Comment ça marche
1. **Détection** : YOLO regarde chaque image et propose des boîtes (classe + confiance). NMS supprime les doublons.
2. **Suivi** : chaque objet suivi a un filtre de Kalman qui prédit où il sera à l'image suivante. On associe les nouvelles
   détections aux objets suivis selon leur recouvrement (IoU) avec l'algorithme hongrois. Un objet reste le même numéro
   (#1, #2…) tant qu'il est associé ; il est oublié après 20 images sans détection.

## Limites honnêtes
- YOLOv4-tiny est rapide mais moins précis que YOLOv8/Faster R-CNN : petits objets et scènes chargées difficiles.
- SORT n'utilise que la position : si deux objets se croisent ou si un objet disparaît longtemps, les numéros peuvent changer
  (Deep SORT, avec apparence visuelle, corrigerait cela).
- Sur CPU, comptez environ 10 à 25 images/s selon l'ordinateur.
- Le modèle (24 Mo, `models/yolov4-tiny.weights`) provient du projet Darknet / AlexeyAB (licence YOLO ouverte).

## GitHub
Nom du dépôt demandé : `CodeAlpha_ObjectDetectionTracking`.
