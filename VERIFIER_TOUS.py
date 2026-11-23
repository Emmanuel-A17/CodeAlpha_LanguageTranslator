"""Script de vérification de tous les projets CodeAlpha."""
import py_compile
import importlib
import sys

FILES = [
    # FAQChatbot
    "CodeAlpha_FAQChatbot/app.py",
    "CodeAlpha_FAQChatbot/chatbot.py",
    # LanguageTranslator
    "CodeAlpha_LanguageTranslator/CodeAlpha_LanguageTranslator/app.py",
    # MusicGenerator
    "CodeAlpha_MusicGenerator/app.py",
    "CodeAlpha_MusicGenerator/generate.py",
    "CodeAlpha_MusicGenerator/train.py",
    "CodeAlpha_MusicGenerator/collect_data.py",
    "CodeAlpha_MusicGenerator/musicai/__init__.py",
    "CodeAlpha_MusicGenerator/musicai/engine.py",
    "CodeAlpha_MusicGenerator/musicai/lstm.py",
    "CodeAlpha_MusicGenerator/musicai/markov.py",
    "CodeAlpha_MusicGenerator/musicai/midi_io.py",
    "CodeAlpha_MusicGenerator/musicai/sampler.py",
    "CodeAlpha_MusicGenerator/musicai/synth.py",
    "CodeAlpha_MusicGenerator/musicai/tokens.py",
    "CodeAlpha_MusicGenerator/musicai/dataset.py",
    "CodeAlpha_MusicGenerator/musicai/demo_tunes.py",
    # ObjectTracker
    "CodeAlpha_ObjectTracker/CodeAlpha_ObjectTracker/app.py",
    "CodeAlpha_ObjectTracker/CodeAlpha_ObjectTracker/track.py",
    "CodeAlpha_ObjectTracker/CodeAlpha_ObjectTracker/objtrack/__init__.py",
    "CodeAlpha_ObjectTracker/CodeAlpha_ObjectTracker/objtrack/detector.py",
    "CodeAlpha_ObjectTracker/CodeAlpha_ObjectTracker/objtrack/draw.py",
    "CodeAlpha_ObjectTracker/CodeAlpha_ObjectTracker/objtrack/pipeline.py",
    "CodeAlpha_ObjectTracker/CodeAlpha_ObjectTracker/objtrack/sort.py",
]

DEPS = {
    "flask": "flask",
    "numpy": "numpy",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "nltk": "nltk",
    "requests": "requests",
    "torch": "torch",
}

BASE = r"c:\Users\HP\OneDrive\Desktop\CodeAlpha_Tâches"

def check_syntax():
    print("=" * 60)
    print("1. VÉRIFICATION SYNTAXE (py_compile)")
    print("=" * 60)
    errors = []
    for f in FILES:
        path = f"{BASE}/{f}"
        try:
            py_compile.compile(path, doraise=True)
            print(f"  OK: {f}")
        except py_compile.PyCompileError as e:
            errors.append((f, str(e)))
            print(f"  ERREUR: {f} - {e}")
    print(f"\nRésultat: {len(FILES) - len(errors)}/{len(FILES)} fichiers syntaxiquement corrects")
    return errors

def check_deps():
    print("\n" + "=" * 60)
    print("2. VÉRIFICATION DÉPENDENCES (imports)")
    print("=" * 60)
    missing = []
    for mod, pkg in DEPS.items():
        try:
            importlib.import_module(mod)
            print(f"  OK: {mod}")
        except ImportError:
            missing.append((mod, pkg))
            print(f"  MANQUANT: {mod} (pip install {pkg})")
    return missing

def check_files_exist():
    print("\n" + "=" * 60)
    print("3. VÉRIFICATION FICHIERS STATIQUES ET CONFIG")
    print("=" * 60)
    static_files = [
        "CodeAlpha_FAQChatbot/static/index.html",
        "CodeAlpha_FAQChatbot/static/script.js",
        "CodeAlpha_FAQChatbot/static/style.css",
        "CodeAlpha_FAQChatbot/faqs.json",
        "CodeAlpha_FAQChatbot/requirements.txt",
        "CodeAlpha_LanguageTranslator/CodeAlpha_LanguageTranslator/static/index.html",
        "CodeAlpha_LanguageTranslator/CodeAlpha_LanguageTranslator/static/script.js",
        "CodeAlpha_LanguageTranslator/CodeAlpha_LanguageTranslator/static/style.css",
        "CodeAlpha_LanguageTranslator/CodeAlpha_LanguageTranslator/requirements.txt",
        "CodeAlpha_MusicGenerator/static/index.html",
        "CodeAlpha_MusicGenerator/static/script.js",
        "CodeAlpha_MusicGenerator/static/style.css",
        "CodeAlpha_MusicGenerator/requirements.txt",
        "CodeAlpha_MusicGenerator/data/midi/.gitkeep",
        "CodeAlpha_ObjectTracker/CodeAlpha_ObjectTracker/static/index.html",
        "CodeAlpha_ObjectTracker/CodeAlpha_ObjectTracker/static/script.js",
        "CodeAlpha_ObjectTracker/CodeAlpha_ObjectTracker/static/style.css",
        "CodeAlpha_ObjectTracker/CodeAlpha_ObjectTracker/requirements.txt",
        "CodeAlpha_ObjectTracker/models/yolov4-tiny.cfg",
        "CodeAlpha_ObjectTracker/models/yolov4-tiny.weights",
    ]
    missing_files = []
    for f in static_files:
        path = f"{BASE}/{f}"
        import os
        if os.path.exists(path):
            print(f"  OK: {f}")
        else:
            missing_files.append(f)
            print(f"  MANQUANT: {f}")
    return missing_files

if __name__ == "__main__":
    syntax_errors = check_syntax()
    missing_deps = check_deps()
    missing_files = check_files_exist()

    print("\n" + "=" * 60)
    print("RÉSUMÉ FINAL")
    print("=" * 60)
    if syntax_errors:
        print(f"❌ {len(syntax_errors)} erreur(s) de syntaxe")
    else:
        print("✅ Aucun erreur de syntaxe")

    if missing_deps:
        print(f"❌ {len(missing_deps)} dépendance(s) manquante(s):")
        for mod, pkg in missing_deps:
            print(f"   - {mod} (installez avec: pip install {pkg})")
    else:
        print("✅ Toutes les dépendances principales sont présentes")

    if missing_files:
        print(f"❌ {len(missing_files)} fichier(s) manquant(s):")
        for f in missing_files:
            print(f"   - {f}")
    else:
        print("✅ Tous les fichiers statiques et de config sont présents")

    if not syntax_errors and not missing_deps and not missing_files:
        print("\n🎉 TOUS LES PROJETS SONT PRÊTS À S'EXÉCUTER")
    else:
        print("\n⚠️  Certains problèmes doivent être corrigés avant exécution")