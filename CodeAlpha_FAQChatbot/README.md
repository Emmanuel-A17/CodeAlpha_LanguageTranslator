# Nova Shop — Chatbot for FAQs

**CodeAlpha · Artificial Intelligence Internship · Tâche 2**

Chatbot de FAQ en français : l'utilisateur pose une question avec ses propres mots, le programme retrouve la FAQ la plus proche grâce au traitement du langage naturel et à la **similarité cosinus**, puis affiche la réponse dans une interface de chat.

> Le sujet (boutique « Nova Shop ») et les informations (prix, horaires, téléphone) sont **fictifs**, à remplacer par vos vraies données dans `faqs.json`.

## Fonctionnement

1. **Collecte** : 32 FAQ en 7 catégories dans `faqs.json` (chaque FAQ a une question, des formulations alternatives et une réponse).
2. **Prétraitement** (NLTK) : minuscules, retrait des élisions (`l'article`), tokenisation, suppression des mots vides, regroupement des synonymes (`offerte` = `gratuite`), racinisation (`commandes` → `command`).
3. **Vectorisation** : TF-IDF sur les mots **et** sur les caractères (tolère les fautes de frappe : « comande », « livraizon »).
4. **Correspondance** : similarité cosinus entre la question et chaque formulation de FAQ, avec pénalités pour les mots inconnus ou trop vagues.
5. **Décision** :
   - confiance haute → réponse directe ;
   - confiance moyenne → réponse prudente (« Je pense que cela peut vous aider ») + questions proches ;
   - confiance faible → message de repli + suggestions.
6. **Conversation** : « bonjour », « merci », « au revoir », « qui es-tu ? » sont gérés sans passer par les FAQ.

## Structure

```
CodeAlpha_FAQChatbot/
├── app.py              # Serveur Flask + API
├── chatbot.py          # Moteur NLP (prétraitement, TF-IDF, cosinus)
├── faqs.json           # Base de FAQ (à personnaliser)
├── requirements.txt
├── README.md
├── .gitignore
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

Puis ouvrir **http://127.0.0.1:5000** (et non un fichier HTML ou Live Server).

Test rapide dans le terminal, sans interface : `python chatbot.py`

## API

| Méthode | Route              | Description                                          |
|---------|--------------------|------------------------------------------------------|
| GET     | `/api/health`      | État du serveur, nombre de FAQ, moteur NLP           |
| GET     | `/api/faqs`        | Toutes les questions, par catégorie                  |
| GET     | `/api/suggestions` | Questions populaires                                 |
| POST    | `/api/chat`        | `{ "message": "..." }` → réponse, confiance, suggestions |

## Personnaliser la base de FAQ

Modifiez `faqs.json` : pour chaque entrée, ajoutez dans `variants` les façons dont vos clients posent réellement la question. C'est le moyen le plus efficace d'améliorer la précision. Relancez ensuite `python app.py`.

## Précision mesurée

Test sur 36 questions reformulées, écrites sans consulter le moteur (jeu jamais utilisé pour le régler) : **32 bonnes réponses (89 %)**, 1 réponse fausse affirmée avec confiance, et aucune fausse réponse affirmée sur 8 questions hors sujet. Ces tests ont été faits avec le mode de secours du moteur (voir ci-dessous) ; les résultats avec le stemmer NLTK peuvent légèrement varier.

Limites : approche par mots-clés (pas de compréhension du sens) ; une question hors sujet qui partage un mot avec une FAQ peut recevoir une réponse hésitante.

## À propos de NLTK

Le tokenizer et le stemmer français de NLTK ne nécessitent aucun téléchargement de données. Si NLTK n'est pas installé, `chatbot.py` bascule automatiquement sur un équivalent simple (l'interface affiche alors « NLP fallback » au lieu de « NLP nltk »).

## Soumission CodeAlpha

1. Dépôt GitHub nommé `CodeAlpha_FAQChatbot`
2. Vidéo de démonstration sur LinkedIn (en taguant @CodeAlpha) avec le lien du dépôt
3. Formulaire de soumission partagé dans le groupe WhatsApp
