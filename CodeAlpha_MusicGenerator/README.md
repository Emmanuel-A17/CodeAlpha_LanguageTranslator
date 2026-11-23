# 🎵 Melodia — Génération de musique avec l'IA (CodeAlpha, Tâche 3)

Un réseau de neurones **LSTM** apprend à partir de fichiers MIDI, puis compose de nouvelles mélodies
qu'on peut écouter, visualiser (rouleau de piano) et télécharger en **MIDI** et **WAV**.

## Pipeline
| Étape | Fichier | Ce qui se passe |
|---|---|---|
| 1. Collecte | `collect_data.py` | Mélodies de démo, corpus de Bach (music21) ou vos propres `.mid` |
| 2. Prétraitement | `musicai/midi_io.py`, `tokens.py`, `dataset.py` | MIDI → notes → 194 tokens (NOTE_ON, NOTE_OFF, TIME_SHIFT…) ; transposition dans 12 tonalités |
| 3. Modèle | `musicai/lstm.py` | Embedding → LSTM 2 couches → prédiction du token suivant |
| 4. Entraînement | `train.py` | Entropie croisée, AdamW, validation, arrêt anticipé |
| 5. Génération | `musicai/sampler.py` | Tirage token par token (température, top-k, règles de validité) |
| 6. MIDI / audio | `midi_io.py`, `synth.py` | Écriture `.mid` et synthèse `.wav` |
| 7. Interface | `app.py`, `static/` | Page web Flask |

Un modèle **chaîne de Markov** est entraîné aussi : il sert de point de comparaison au LSTM.

## Installation et lancement (Windows / VSCode)
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

python collect_data.py --demo     # données de démonstration (10 mélodies)
python train.py                   # entraîne le LSTM (et le modèle de Markov)
python app.py                     # puis ouvrir http://127.0.0.1:5000
```
Sans PyTorch : `python train.py --markov-only` fonctionne quand même.
En ligne de commande : `python generate.py --seconds 30 --tempo 110`.

## Avoir de la vraie bonne musique
Les 10 mélodies de démo sont **trop peu** pour un LSTM : il apprendrait surtout à les recopier.
Pour un vrai résultat, utilisez beaucoup plus de MIDI :
```powershell
pip install music21
python collect_data.py --bach          # centaines de chorals de Bach
python collect_data.py --from "C:\mes_midi"   # ou vos propres fichiers .mid
python train.py --epochs 40
```
Un GPU accélère beaucoup l'entraînement ; sur CPU, gardez `--hidden 128` et peu d'époques.

## Limites honnêtes
- Les notes sont quantifiées à la double-croche : pas de rubato ni de nuances de vélocité.
- Tous les instruments sont fusionnés en un seul (piano) ; la batterie est ignorée.
- Le LSTM ne retient que des structures courtes : pas de forme musicale globale (couplet/refrain).
- Le son WAV est un synthétiseur simple, pas un vrai piano échantillonné.

## Mettre sur GitHub
Nom du dépôt demandé : `CodeAlpha_MusicGenerator`.
