# LIMINAL BACKROOMS GENERATOR

## Contexte
Créer un utilitaire graphique sous Linux permettant de générer à la demande des images d'espaces liminaux et de backrooms uniques, photo-réalistes et atmosphériques, au format 16:9.
L'application repose sur un bouton déclencheur, une rotation combinatoire de prompts (décors, éclairages, détails, artefacts analogiques…) et appelle l'API d'image choisie par l'utilisateur (Replicate, fal.ai, OpenAI ou Google, avec son propre token) pour afficher l'image, puis la sauvegarder via « Save as ».

## Stack & commandes
- OS : Linux (Fedora, GNOME, Wayland via XWayland)
- Python : 3.12+ (système : 3.14), gestionnaire : venv (`.venv/`)
- Dépendances (`requirements.txt`) : `customtkinter`, `pillow`, `requests`. Dev (`requirements-dev.txt`) : `pytest`.
- Prérequis système : `sudo dnf install python3-tkinter` (tkinter ne s'installe pas via pip). `zenity` optionnel (boîte « Save as » native).
- Tous les fournisseurs sont appelés en HTTP direct via `requests` (pas de SDK).
- Tokens : variables d'environnement (`REPLICATE_API_TOKEN`, `FAL_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`) prioritaires, sinon saisis dans le panneau ⚙ et stockés dans `~/.config/liminal/config.json` (permissions `600`).
- Lancer l'app : `.venv/bin/python main.py`
- Lancer les tests : `.venv/bin/python -m pytest tests/`

## Structure
- `generated/` : dossier proposé par défaut pour « Save as » (ignoré par git)
- `prompts/` : un `.txt` par catégorie, un fragment par ligne, `#` = commentaire, fragments à trous `{slot}` possibles
- `style/interface.md` : spécifications de l'UI (source de vérité)
- `main.py` : point d'entrée, interface CustomTkinter et boucle d'événements
- `generator.py` : assemblage procédural du prompt, unicité (historique persistant, anti-proximité, seed)
- `providers.py` : une fonction d'appel par fournisseur + table des modèles prédéfinis (prix, 16:9 natif)
- `storage.py` : config, téléchargement/conversion PNG, sauvegarde image + `.json` de métadonnées
- `postprocess.py` : rendu analogique local (Pillow) appliqué à chaque image générée, avec des intensités tirées au hasard à chaque fois (basse résolution, flou, aberration chromatique, couleurs fanées, grain parfois absent ou en couleur)
- `tests/` : tests pytest, tous les appels réseau mockés

## Style visé
- La source de vérité pour l'UI est `style/interface.md`.
- Outil : minimaliste, seulement l'essentiel à l'écran (image, Generate, Save, ⚙), thème sombre, textes de l'UI en anglais.
- Rendu des images : aspect argentique / analogique, photo brute amateur (1985–2008, flash direct, VHS/disposable camera), zéro esthétique CGI ou lisse.
- Contenu : espaces vides, **toujours sans personne**. Inspirations : Backrooms de Kane Pixels, r/LiminalSpace.
- La variété ne doit jamais faire sortir du style liminal (quantités bornées, palettes liminales).
- Éviter : fenêtres encombrées, blocage/gel du thread UI pendant les requêtes réseau.

## Workflow
1. Consulter ou mettre à jour `style/interface.md` avant toute refonte de l'UI.
2. Tout appel réseau lourd ou tâche d'I/O doit obligatoirement tourner dans un thread séparé (arrière-plan).
3. Chaque image retenue s'enregistre via « Save as » avec un `.json` de métadonnées à côté (prompt, provider, modèle, seed…).
4. Une fonctionnalité = une fonction simple et testée isolément, sans abstraction excessive.
5. Les tests ne font jamais d'appel API réel (facturé).
6. Git : chaque modification est commitée sur une branche dédiée (jamais directement sur `main`). Une fois validée par l'utilisateur, la branche est fusionnée dans `main` et `main` est poussé sur `origin` (https://github.com/boomer24vs/liminal-generation).
7. Grill : avant tout changement important (nouvelle fonctionnalité, refonte, changement de modèle/fournisseur/structure des prompts) ou dès qu'une question notable se pose sur le projet, interroger l'utilisateur en profondeur avec la skill `grilling` (rounds de questions numérotées avec recommandation) avant d'implémenter.

## Agents & skills (utilisés seulement quand utile)
- `code-reviewer` : avant toute validation ou restructuration d'un script conséquent.
- `debugging-and-error-recovery` : en cas d'erreurs d'API, de timeouts réseau ou de dépendances X11/Wayland.
- `idea-refine` : pour peaufiner la variété des briques de prompts ou l'ergonomie de la fenêtre.
- Ne pas lancer d'agent pour des ajustements mineurs.

## Règles de comportement
- Ne pas poser de questions inutiles : choisir un défaut raisonnable et le signaler.
- Ne pas ajouter de dépendances ou fonctionnalités non demandées.
- **Sécurité :** Ne jamais coder en dur un token dans les scripts ni le stocker dans le projet.
- **Coûts :** le modèle par défaut est FLUX.1 schnell (Replicate). Prévenir et demander confirmation avant de changer ce défaut vers une option plus coûteuse. Le choix de l'utilisateur dans ⚙ est libre (prix affiché).
- Répondre en français, écrire le code et les identifiants en anglais.
- Indiquer clairement ce qui a été testé localement et ce qui reste à valider par l'utilisateur.
- Avant de démarrer l'implémentation complète, poser les questions nécessaires pour cadrer précisément le format et l'UI attendus.
