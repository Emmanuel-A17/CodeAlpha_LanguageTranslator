"""
CodeAlpha - Tâche 2 : Chatbot for FAQs
Moteur NLP : prétraitement (NLTK) + TF-IDF + similarité cosinus.

Pipeline :
  1. Prétraitement : minuscules, élisions, tokenisation, stop-words, racinisation (stemming)
  2. Vectorisation : TF-IDF sur les mots + TF-IDF sur les caractères (tolère les fautes de frappe)
  3. Correspondance : similarité cosinus entre la question de l'utilisateur et chaque FAQ
  4. Décision : réponse directe, réponse + suggestions, ou message de repli
"""

import json
import random
import re
import unicodedata
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# --------------------------------------------------------------------------
# NLTK (tokenisation + stemming). Si NLTK n'est pas installé, on utilise un
# équivalent simple pour que le programme fonctionne quand même.
# --------------------------------------------------------------------------
try:
    from nltk.stem.snowball import FrenchStemmer
    from nltk.tokenize import RegexpTokenizer

    _stemmer = FrenchStemmer()
    _tokenizer = RegexpTokenizer(r"\w+")
    NLP_BACKEND = "nltk"

    def _stem(word: str) -> str:
        return _stemmer.stem(word)

    def _tokenize(text: str):
        return _tokenizer.tokenize(text)

except ImportError:  # pragma: no cover
    NLP_BACKEND = "fallback"
    _SUFFIXES = ("ements", "ement", "ations", "ation", "ateurs", "ateur", "ements",
                 "ences", "ence", "ités", "ité", "eurs", "eur", "ions", "ion",
                 "ent", "ées", "ée", "és", "er", "ez", "es", "e", "s", "x")

    def _stem(word: str) -> str:
        for suffix in _SUFFIXES:
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                return word[: -len(suffix)]
        return word

    def _tokenize(text: str):
        return re.findall(r"\w+", text)

# --------------------------------------------------------------------------
# Paramètres
# --------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
FAQ_FILE = BASE_DIR / "faqs.json"

WORD_WEIGHT = 0.6      # poids du TF-IDF « mots »
CHAR_WEIGHT = 0.4      # poids du TF-IDF « caractères »
THRESHOLD_HIGH = 0.45  # au-dessus : réponse directe
THRESHOLD_LOW = 0.22   # en dessous : « je n'ai pas compris »
MAX_SUGGESTIONS = 3
ANSWER_WEIGHT = 0.75   # poids des phrases des réponses (indexées en plus des questions)
GENERIC_QUERY_FAQS = 6  # une question d'un seul mot présent dans autant de FAQ est trop ambiguë

STOPWORDS = {
    "a", "à", "au", "aux", "avec", "ce", "ces", "cet", "cette", "ceci", "cela", "ça", "c",
    "dans", "de", "des", "du", "d", "elle", "elles", "en", "es", "est", "et", "été", "être",
    "eu", "il", "ils", "j", "je", "l", "la", "le", "les", "leur", "leurs", "lui", "m", "ma",
    "mais", "me", "même", "mes", "moi", "mon", "n", "ne", "nos", "notre", "nous", "on", "ou",
    "où", "par", "pas", "pour", "qu", "que", "qui", "quoi", "s", "sa", "se", "ses", "si", "son",
    "sont", "sur", "t", "ta", "te", "tes", "toi", "ton", "tu", "un", "une", "vos", "votre",
    "vous", "y", "ai", "as", "avons", "avez", "ont", "suis", "sommes", "êtes", "serai",
    "sera", "serez", "ete", "etre", "comment", "quel", "quels", "quelle", "quelles", "quand",
    "puis", "peux", "peut", "pouvez", "peuvent", "veux", "veut", "voudrais", "voulez",
    "faut", "fait", "faire", "dois", "doit", "devez", "alors", "donc", "aussi", "très",
    "tres", "plus", "moins", "tout", "tous", "toute", "toutes", "bien", "juste", "svp",
    "stp", "please", "est-ce", "peut-on", "y-a-t-il", "ya", "il y a", "dit", "dire",
    "savoir", "besoin", "souhaite", "souhaiterais", "aimerais", "aimer",
    "font", "fais", "faisons", "pourquoi", "chose", "truc",
    "cherche", "cherches", "cherchons", "cherchez", "chercher", "venir",
    "avoir", "apres", "moment", "possible",
}

# Synonymes / formes proches ramenés à un seul mot (clés sans accents).
# Permet de comprendre « offerte » = « gratuite », « magasin » = « boutique », etc.
_SYNONYM_GROUPS = {
    "gratuit": "offert offerte offerts gratuite gratuites gratis free",
    "contacter": "joindre appeler appelez telephoner contact contactez contacts",
    "boutique": "magasin magasins shop boutiques",
    "etranger": "international internationale internationaux etrangere",
    "produit": "article articles objet objets marchandise produits",
    "commander": "achat achats acheter achete achetes achetee achete",
    "colis": "paquet paquets",
    "livrer": "livraison livraisons livre livres livree livrez livreur livreurs livrons "
              "envoi envois expedition expeditions expedie expedier expedies transport",
    "payer": "paiement paiements paye payee payez regler reglement",
    "retourner": "retour retours renvoyer renvoi renvoyez rendre",
    "echanger": "echange echanges echangez",
    "annuler": "annulation annulations annule annulee",
    "suivre": "suivi suivis suivez",
    "creer": "inscrire inscription inscriptions inscris inscrit enregistrer enregistrement",
    "supprimer": "suppression effacer efface fermer fermeture",
    "desabonner": "desabonnement desinscrire desinscription desinscris desabonne",
    "horaire": "horaires heure heures ouvert ouverts ouverte ouverture ouvrez",
    "mail": "mails email emails courriel courriels courrier",
    "especes": "espece cash liquide",
    "defectueux": "defectueuse casse cassee abime abimee endommage endommagee deteriore",
    "fonctionner": "fonctionne fonctionnent marche marchent",
    "retard": "retards tarde tarder attends attendre attend attendu",
    "erreur": "probleme problemes souci soucis echec echoue echouee bug refuse refusee anomalie",
    "frais": "prix tarif tarifs cout couts coute coutent couter payant",
    "recuperer": "retirer retrait retraits recupere recuperation",
    "debiter": "debite debitee debit preleve prelevee prelevement preleves",
    "perdu": "perdue perdus egare egaree disparu introuvable introuvables",
    "modifier": "modification modifications changer changement corriger correction",
    "recevoir": "reception receptionner recois recoit recevrai recevez recevons",
    "securite": "securise securisee securises confidentiel confidentielle confidentiels "
                "confidentialite protege protegee protegees protection fiable risque risquee",
    "promo": "promotion promotions promotionnel promotionnelle promotionnels promos "
             "reduction reductions remise remises coupon coupons",
    "taille": "tailles pointure pointures",
    "disponible": "disponibles disponibilite stock epuise epuisee rupture",
}
# Mots avec accents à ne pas confondre avec un stop-word une fois les accents retirés (« sûr » != « sur »)
EXACT_SYNONYMS = {"sûr": "securite", "sûre": "securite", "sûrs": "securite", "sûres": "securite"}
SYNONYMS = {w: canon for canon, words in _SYNONYM_GROUPS.items() for w in words.split()}

# Intentions de conversation (réponses sans passer par les FAQ)
INTENTS = {
    "greeting": {
        "patterns": ["bonjour", "bonsoir", "salut", "coucou", "hello", "hey", "bjr", "slt", "hi",
                     "salut a toi", "bonne journee", "bonsoir a vous"],
        "answers": [
            "Bonjour ! 👋 Je suis l'assistant de Nova Shop. Posez-moi votre question sur les commandes, la livraison, le paiement ou les retours.",
            "Bonjour et bienvenue ! Comment puis-je vous aider aujourd'hui ?",
        ],
    },
    "thanks": {
        "patterns": ["merci", "merci beaucoup", "thanks", "thank you", "super merci", "merci bien",
                     "c'est gentil", "genial", "parfait", "top", "cool", "ok merci", "d'accord merci"],
        "fillers": ["aide", "reponse", "info", "infos", "informations", "reponses", "service", "travail", "tout"],
        "answers": [
            "Avec plaisir ! 😊 N'hésitez pas si vous avez d'autres questions.",
            "De rien ! Je reste disponible si vous avez besoin d'autre chose.",
        ],
    },
    "bye": {
        "patterns": ["au revoir", "bye", "a bientot", "a plus", "a la prochaine", "ciao", "adieu",
                     "bonne soiree", "bonne continuation", "a demain"],
        "answers": ["Au revoir et à bientôt sur Nova Shop ! 👋", "À bientôt ! Belle journée à vous."],
    },
    "identity": {
        "patterns": ["qui es tu", "tu es qui", "qui etes vous", "vous etes qui", "comment tu t'appelles",
                     "comment t'appelles tu", "tu es un robot", "es tu un robot", "tu es une ia",
                     "tu es humain", "c'est quoi ton nom"],
        "answers": [
            "Je suis l'assistant virtuel de Nova Shop 🤖. Je réponds aux questions fréquentes grâce à du traitement automatique du langage. "
            "Pour une demande spécifique, notre équipe humaine est joignable par e-mail ou WhatsApp."
        ],
    },
    "help": {
        "patterns": ["aide", "aide moi", "help", "que peux tu faire", "que sais tu faire", "tu peux m'aider",
                     "peux tu m'aider", "pouvez vous m'aider", "a quoi sers tu", "comment ca marche",
                     "j'ai besoin d'aide", "besoin d'aide"],
        "answers": [
            "Je peux répondre à vos questions sur : les commandes et leur suivi, la livraison, les moyens de paiement, "
            "les retours et remboursements, votre compte, les produits et le service client. Essayez par exemple : « Quels sont les délais de livraison ? »"
        ],
    },
}

FALLBACK_ANSWERS = [
    "Je n'ai pas trouvé de réponse précise à votre question. 🤔 Pouvez-vous la reformuler avec d'autres mots ?",
    "Hmm, je ne suis pas sûr de bien comprendre. Essayez de reformuler ou choisissez l'une des questions ci-dessous.",
]
LOW_CONFIDENCE_PREFIX = "Je pense que cela peut vous aider :\n\n"


# --------------------------------------------------------------------------
# Prétraitement
# --------------------------------------------------------------------------
def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


_STOP_NOACCENT = {strip_accents(w) for w in STOPWORDS}

try:  # stop-words NLTK si le corpus est déjà téléchargé (facultatif)
    from nltk.corpus import stopwords as _nltk_stop

    _STOP_NOACCENT |= {strip_accents(w) for w in _nltk_stop.words("french")} - {"pas", "non", "plus"}
except Exception:  # corpus absent ou NLTK non installé : on garde notre liste
    pass


def normalize(text: str) -> str:
    """Minuscules, apostrophes unifiées, élisions retirées (l'article -> article)."""
    text = text.lower().replace("’", "'").replace("`", "'")
    text = re.sub(r"\b(?:qu|[cdjlmnst])'", " ", text)
    return text


def preprocess(text: str) -> list:
    """Texte -> liste de racines (tokens nettoyés, sans stop-words, sans accents)."""
    tokens = []
    for token in _tokenize(normalize(text)):
        token = EXACT_SYNONYMS.get(token, token)
        plain = strip_accents(token)
        if plain in _STOP_NOACCENT:
            continue
        if len(plain) < 2 and not plain.isdigit():
            continue
        if plain in SYNONYMS:  # forme canonique (offerte -> gratuit, magasin -> boutique...)
            token = SYNONYMS[plain]
        tokens.append(strip_accents(_stem(token)))
    return tokens


# Mots trop courants pour prouver, seuls, qu'une FAQ correspond (on compare des racines)
WEAK_WORDS = {t for w in ("combien", "temps", "jour", "recevoir") for t in preprocess(w)}


def _simple(text: str) -> str:
    """Version « brute » pour la détection d'intention : sans accents ni ponctuation."""
    text = strip_accents(normalize(text))
    text = re.sub(r"[^a-z0-9' ]+", " ", text)
    text = text.replace("'", " ")
    return re.sub(r"\s+", " ", text).strip()


# --------------------------------------------------------------------------
# Le chatbot
# --------------------------------------------------------------------------
class FAQChatbot:
    def __init__(self, faq_file: Path = FAQ_FILE):
        data = json.loads(Path(faq_file).read_text(encoding="utf-8"))
        self.topic = data.get("topic", "")
        self.faqs = data["faqs"]
        self._by_id = {f["id"]: f for f in self.faqs}

        # Un « document » par formulation (question principale + variantes)
        phrases = [(faq["id"], preprocess(p)) for faq in self.faqs
                   for p in [faq["question"]] + faq.get("variants", [])]

        self._doc_texts, self._doc_faq, self._doc_tokens, self._doc_weight = [], [], [], []

        def add_doc(faq_id, tokens, weight):
            self._doc_texts.append(" ".join(tokens))
            self._doc_faq.append(faq_id)
            self._doc_tokens.append(set(tokens))
            self._doc_weight.append(weight)

        for faq_id, tokens in phrases:
            if tokens:
                add_doc(faq_id, tokens, 1.0)

        # Les phrases de la réponse servent aussi (noms de villes, « PDF », « chiffrée »...), avec un poids réduit
        for faq in self.faqs:
            for sentence in re.split(r"(?<=[.!?:])\s+|\n+", faq["answer"]):
                tokens = preprocess(sentence)
                if len(tokens) >= 2:
                    add_doc(faq["id"], tokens, ANSWER_WEIGHT)
        self._doc_weight = np.array(self._doc_weight)

        # Nombre de FAQ dans lesquelles chaque racine apparaît (détecte les mots trop généraux)
        self._faq_count = {}
        for faq_id, doc in zip(self._doc_faq, self._doc_tokens):
            for token in doc:
                self._faq_count.setdefault(token, set()).add(faq_id)

        self._word_vec = TfidfVectorizer(token_pattern=r"\S+", ngram_range=(1, 2), sublinear_tf=True)
        self._char_vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
        self._word_matrix = self._word_vec.fit_transform(self._doc_texts)
        self._char_matrix = self._char_vec.fit_transform(self._doc_texts)

        # Motifs d'intentions (les plus longs d'abord)
        self._intent_patterns = sorted(
            ((_simple(p), name) for name, d in INTENTS.items() for p in d["patterns"]),
            key=lambda x: -len(x[0]),
        )

    # ---- similarité cosinus -------------------------------------------------
    def rank(self, message: str):
        """Retourne [(faq_id, score)] trié par score décroissant (meilleur score par FAQ)."""
        tokens = preprocess(message)
        if not tokens:
            return []
        query = " ".join(tokens)
        word_sim = cosine_similarity(self._word_vec.transform([query]), self._word_matrix)[0]
        char_sim = cosine_similarity(self._char_vec.transform([query]), self._char_matrix)[0]
        scores = WORD_WEIGHT * word_sim + CHAR_WEIGHT * char_sim
        # Aucun mot en commun et peu de lettres communes : simple coïncidence, on pénalise
        trusted = (word_sim >= 0.05) | (char_sim >= 0.5)
        scores = np.where(trusted, scores, scores * 0.5)
        # Couverture : part des mots de la question qu'on retrouve dans la formulation de la FAQ.
        # « quel temps fait-il à Cotonou » ne couvre que la moitié de « boutique Cotonou ».
        query_set = set(tokens)
        coverage = np.array([len(query_set & doc) / len(query_set) for doc in self._doc_tokens])
        scores = np.where(word_sim >= 0.05, scores * (0.6 + 0.4 * coverage), scores)
        # Seul un mot « faible » (ex. « combien ») en commun : ce n'est pas une vraie correspondance
        weak_only = np.array([bool(query_set & doc) and (query_set & doc) <= WEAK_WORDS for doc in self._doc_tokens])
        scores = np.where(weak_only, scores * 0.4, scores)
        # Beaucoup de mots inconnus dans la question : la correspondance est moins fiable
        vocab = self._word_vec.vocabulary_
        if sum(1 for t in query_set if t in vocab) / len(query_set) < 0.5:
            scores = scores * 0.7
        scores = scores * self._doc_weight

        best = {}
        for faq_id, score in zip(self._doc_faq, scores):
            if score > best.get(faq_id, 0.0):
                best[faq_id] = float(score)
        return sorted(best.items(), key=lambda x: -x[1])

    def _is_doubtful(self, message: str) -> bool:
        """Vrai si la question est trop vague ou contient des mots inconnus : on répond avec prudence."""
        tokens = preprocess(message)
        vocab = self._word_vec.vocabulary_
        known = [t for t in tokens if t in vocab]
        if len(known) <= 2 and len(known) < len(tokens):  # mots inconnus (« iPhone », « Paris »...)
            return True
        return len(tokens) == 1 and len(self._faq_count.get(tokens[0], ())) >= GENERIC_QUERY_FAQS

    # ---- intentions ---------------------------------------------------------
    def _match_intent(self, message: str, loose: bool = False):
        text = _simple(message)
        if not text:
            return None
        found, remaining = None, f" {text} "
        for pattern, name in self._intent_patterns:
            needle = f" {pattern} "
            if needle in remaining:
                found = found or name
                remaining = remaining.replace(needle, " ")
        if not found:
            return None
        if loose:
            return found if len(text.split()) <= 8 else None
        fillers = set(INTENTS[found].get("fillers", []))
        leftover = [t for t in preprocess(remaining) if t not in {strip_accents(_stem(f)) for f in fillers}]
        return found if not leftover else None

    # ---- réponse ------------------------------------------------------------
    def _suggestions(self, ranked, exclude_id=None, limit=MAX_SUGGESTIONS):
        out = []
        for faq_id, score in ranked:
            if faq_id == exclude_id or score < 0.08:
                continue
            out.append({"id": faq_id, "question": self._by_id[faq_id]["question"]})
            if len(out) == limit:
                break
        return out

    def reply(self, message: str) -> dict:
        message = (message or "").strip()
        if not message:
            return {"type": "empty", "reply": "Posez-moi votre question, je suis là pour vous aider. 🙂",
                    "confidence": 0.0, "suggestions": []}

        # 1) message purement conversationnel ("bonjour", "merci"...)
        intent = self._match_intent(message)
        if intent:
            return {"type": "intent", "intent": intent, "reply": random.choice(INTENTS[intent]["answers"]),
                    "confidence": 1.0, "suggestions": self.popular() if intent in ("greeting", "help") else []}

        # 2) correspondance avec les FAQ (similarité cosinus)
        ranked = self.rank(message)
        if ranked and ranked[0][1] >= THRESHOLD_LOW:
            faq_id, score = ranked[0]
            faq = self._by_id[faq_id]
            confident = score >= THRESHOLD_HIGH and not self._is_doubtful(message)
            return {
                "type": "answer" if confident else "low_confidence",
                "reply": faq["answer"] if confident else LOW_CONFIDENCE_PREFIX + faq["answer"],
                "matched_question": faq["question"],
                "category": faq["category"],
                "faq_id": faq_id,
                "confidence": round(score, 3),
                "suggestions": self._suggestions(ranked, exclude_id=faq_id),
            }

        # 3) intention présente dans une phrase plus longue ("merci pour votre aide précieuse")
        intent = self._match_intent(message, loose=True)
        if intent:
            return {"type": "intent", "intent": intent, "reply": random.choice(INTENTS[intent]["answers"]),
                    "confidence": 1.0, "suggestions": []}

        # 4) repli
        return {"type": "fallback", "reply": random.choice(FALLBACK_ANSWERS),
                "confidence": round(ranked[0][1], 3) if ranked else 0.0,
                "suggestions": self._suggestions(ranked) or self.popular()}

    # ---- listes pour l'interface -------------------------------------------
    def popular(self, limit=6):
        return [{"id": f["id"], "question": f["question"]} for f in self.faqs if f.get("popular")][:limit]

    def answer_by_id(self, faq_id: int):
        faq = self._by_id.get(faq_id)
        if not faq:
            return None
        return {"type": "answer", "reply": faq["answer"], "matched_question": faq["question"],
                "category": faq["category"], "faq_id": faq_id, "confidence": 1.0,
                "suggestions": self._suggestions(self.rank(faq["question"]), exclude_id=faq_id)}

    def catalog(self):
        grouped = {}
        for f in self.faqs:
            grouped.setdefault(f["category"], []).append({"id": f["id"], "question": f["question"]})
        return grouped


# Test rapide dans le terminal : python chatbot.py
if __name__ == "__main__":
    bot = FAQChatbot()
    print(f"Chatbot prêt ({len(bot.faqs)} FAQ, moteur NLP : {NLP_BACKEND}). Tapez 'quit' pour sortir.\n")
    while True:
        try:
            q = input("Vous > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in {"quit", "exit", "q"}:
            break
        r = bot.reply(q)
        print(f"Bot ({r['type']}, {r['confidence']}) > {r['reply']}\n")
