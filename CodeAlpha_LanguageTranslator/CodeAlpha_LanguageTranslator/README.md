# Lingua — Language Translation Tool

**CodeAlpha · Artificial Intelligence Internship · Tâche 1**

Application web de traduction : saisie du texte, choix des langues source et cible, traduction via une API, affichage clair du résultat. Options bonus incluses : bouton de copie et synthèse vocale (text-to-speech).

## Fonctionnalités

- Plus de 80 langues, détection automatique de la langue source
- Inversion des langues en un clic
- Bouton **Copier** et bouton **Écouter** (Web Speech API)
- Historique des dernières traductions (stocké dans le navigateur)
- Thème clair / sombre, design responsive
- Raccourci `Ctrl + Entrée` pour traduire
- Moteur de secours automatique (MyMemory) si Google est indisponible

## Structure

```
CodeAlpha_LanguageTranslator/
├── app.py              # Backend Flask + API de traduction
├── requirements.txt
└── static/
    ├── index.html
    ├── style.css
    └── script.js
```

## Installation et lancement

```bash
pip install -r requirements.txt
python app.py
```

Puis ouvrir http://127.0.0.1:5000

## API

| Méthode | Route             | Description                                      |
|---------|-------------------|--------------------------------------------------|
| GET     | `/api/languages`  | Liste des langues disponibles                    |
| POST    | `/api/translate`  | Corps JSON : `{ "text", "source", "target" }`    |

## Utiliser l'API officielle Google Cloud Translation

Par défaut l'application utilise l'endpoint public de Google Translate (aucune clé requise), pratique pour un projet de stage. Pour une utilisation en production, remplacez la fonction `translate_google` dans `app.py` par un appel à l'API officielle :

```python
resp = requests.post(
    "https://translation.googleapis.com/language/translate/v2",
    params={"key": os.environ["GOOGLE_API_KEY"]},
    json={"q": text, "source": source, "target": target, "format": "text"},
)
```

## Soumission CodeAlpha

1. Dépôt GitHub nommé `CodeAlpha_LanguageTranslator`
2. Vidéo de démonstration publiée sur LinkedIn avec le lien du dépôt
3. Formulaire de soumission partagé dans le groupe WhatsApp
