<div align="center">

<img src="docs/media/icon.png" width="96" alt="Icône Liminal Generator">

# Liminal Generator

**Une petite app Linux qui génère en un clic des photos uniques d'espaces liminaux et de Backrooms.**

À chaque clic, elle compose un nouveau prompt (lieu, éclairage, appareil photo, détails…), l'envoie au modèle d'image de ton choix, puis donne au résultat l'aspect d'une photo argentique bon marché des années 1985 à 2008.

![Linux](https://img.shields.io/badge/Linux-X11%20%7C%20XWayland-FCC624?logo=linux&logoColor=black)
![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![CustomTkinter](https://img.shields.io/badge/CustomTkinter-6-1F6AA5)
![Licence : MIT](https://img.shields.io/badge/licence-MIT-green)

<img src="docs/media/hero.jpg" width="720" alt="Image générée : un couloir de bureau jaune et vide sous des néons">

[English](README.md) · **Français**

</div>

---

## Fonctionnalités

- 🚪 **Un seul bouton** : clique sur *Generate*, tu obtiens une nouvelle image 16:9 d'un lieu vide et étrange.
- 🎲 **Jamais deux fois la même image** : le prompt est assemblé à partir de près de 200 fragments (lieux, murs, sols, éclairages, appareils, détails, anomalies). Chaque combinaison est mémorisée et n'est plus jamais tirée, et le même lieu ou le même éclairage ne revient pas trop vite.
- 📼 **Aspect argentique** : chaque image passe par un post-traitement local d'intensité aléatoire (basse résolution, flou, aberration chromatique, couleurs fanées, grain parfois absent ou en couleur). Elle ressemble à une image de VHS ou à une photo d'appareil jetable, pas à de la 3D.
- 👤 **Parfois, quelqu'un est là** : environ une image sur six montre une présence humaine ambiguë (une silhouette au loin, une ombre que personne ne projette, quelqu'un face au mur…). Jamais deux d'affilée.
- 🔌 **Le modèle de ton choix** : Replicate, fal.ai, OpenAI ou Google, avec ta propre clé API. Le prix par image est affiché à côté de chaque modèle, et tu peux aussi saisir n'importe quel autre identifiant de modèle.
- 💾 **Save as** : boîte d'enregistrement native, en PNG, avec à côté un `.json` qui contient le prompt, le fournisseur, le modèle et la seed.
- 🖤 **Minimaliste** : une image, *Generate*, *Save* et ⚙. Thème sombre, et la fenêtre ne se fige jamais pendant la génération.

<table>
<tr>
<td align="center"><img src="docs/media/poolroom.jpg" width="330" alt="Piscine souterraine carrelée"></td>
<td align="center"><img src="docs/media/school.jpg" width="330" alt="Couloir d'école bordé de casiers"></td>
</tr>
<tr>
<td align="center"><img src="docs/media/hospital.jpg" width="330" alt="Long couloir d'hôpital"></td>
<td align="center"><img src="docs/media/presence.jpg" width="330" alt="Couloir étroit avec une silhouette debout au fond"><br><sub>Une des rares présences</sub></td>
</tr>
<tr>
<td align="center"><img src="docs/media/stairwell.jpg" width="330" alt="Cage d'escalier en béton sous un panneau de sortie"></td>
<td align="center"><img src="docs/media/waiting-room.jpg" width="330" alt="Salle d'attente abandonnée éclairée au flash"></td>
</tr>
</table>

<div align="center">
<img src="docs/media/app.jpg" width="560" alt="La fenêtre de l'app : l'image, Generate, Save et le bouton des réglages">
<br><sub>L'app</sub>
</div>

## Prérequis

- **Linux** avec une session X11, ou Wayland avec XWayland (le cas par défaut sous GNOME et KDE).
- **Python 3.12+** et **tkinter**, que pip ne peut pas installer :
  - Fedora : `sudo dnf install python3-tkinter`
  - Debian/Ubuntu : `sudo apt install python3-tk python3-venv`
- **Une clé API** chez l'un des fournisseurs ci-dessous, avec un peu de crédit dessus.
- Facultatif : **zenity**, pour la boîte d'enregistrement native de GNOME.

## Installation

```bash
git clone https://github.com/boomer24vs/liminal-generation.git
cd liminal-generation
./install.sh
```

Le script :
1. vérifie Python et tkinter ;
2. crée un environnement Python dans `.venv/` et installe les dépendances ;
3. ajoute **Liminal Generator** au menu des applications.

## Utilisation

Lance **Liminal Generator** depuis le menu des applications, ou `.venv/bin/python main.py`.

La première fois, clique sur **⚙**, choisis un fournisseur, colle ta clé API et choisis un modèle. *Verify* teste la clé sans rien générer, donc gratuitement.

| Action | Effet |
|---|---|
| *Generate*, `Espace` ou `Entrée` | Génère une nouvelle image |
| *Save* ou `Ctrl+S` | Enregistre l'image en PNG, avec un `.json` contenant son prompt et ses réglages |
| ⚙ | Fournisseur, clé API et modèle |
| `Échap` | Quitte |

## Fournisseurs et modèles

| Fournisseur | Modèles intégrés | Prix indicatif par image |
|---|---|---|
| [Replicate](https://replicate.com) | FLUX.1 schnell (par défaut) · FLUX.1 dev · FLUX 1.1 pro | 0,003 $ · 0,025 $ · 0,04 $ |
| [fal.ai](https://fal.ai) | FLUX.1 schnell · FLUX.1 dev · FLUX 2 pro | ~0,003 $ · ~0,025 $ · ~0,05 $ |
| [OpenAI](https://platform.openai.com) | GPT Image 2.5 Flare · GPT Image 2 | ~0,05 $ · ~0,04 $ |
| [Google](https://aistudio.google.com) | Gemini 3.1 Flash Lite Image · Gemini 2.5 Flash Image · Gemini 3.1 Flash Image | 0,034 $ · 0,039 $ · ~0,067 $ |

Les prix sont indicatifs : vérifie-les sur le site du fournisseur. Pour ce style, ce sont les modèles FLUX *pro* qui donnent les résultats les plus crédibles. Choisis *custom…* dans la liste des modèles pour utiliser n'importe quel autre modèle proposé par le fournisseur.

**Les clés API** sont lues d'abord dans ces variables d'environnement : `REPLICATE_API_TOKEN`, `FAL_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`. Les clés saisies dans ⚙ sont enregistrées dans `~/.config/liminal/config.json`, lisible par toi seul. Elles ne sont jamais écrites dans le dossier du projet.

## Personnaliser les prompts

Les prompts sont du texte brut dans [`prompts/`](prompts) : un fichier par catégorie, un fragment par ligne, `#` pour les commentaires. Ajoute, supprime ou réécris des lignes pour orienter les images. Un `{slot}` dans un fragment est remplacé par une ligne au hasard de `prompts/slots/<slot>.txt`.

## Dépannage

| Problème | Solution |
|---|---|
| `No module named 'tkinter'` | `sudo dnf install python3-tkinter` (Fedora) ou `sudo apt install python3-tk` (Debian/Ubuntu) |
| `Add an API token in ⚙` | Aucune clé pour le fournisseur choisi : colles-en une dans ⚙ |
| `invalid token` | La clé est fausse ou incomplète. Pour fal.ai, colle la clé entière, y compris la partie après `:` |
| `quota or rate limit reached` | Plus de crédit sur ton compte, ou trop de requêtes : ajoute du crédit ou attends un peu |
| `unknown model` | L'identifiant du modèle personnalisé n'existe pas chez ce fournisseur |
| La fenêtre ne s'ouvre pas sous Wayland pur | XWayland est nécessaire (il est actif par défaut sous GNOME et KDE) |

Testé sur Fedora 43 avec GNOME 49 (Wayland + XWayland). Les autres bureaux devraient fonctionner mais n'ont pas encore été testés : les issues sont les bienvenues.

## Développement

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests/
```

Les tests n'appellent jamais de vraie API : tous les appels réseau sont simulés.

## Désinstallation

```bash
rm ~/.local/share/applications/liminal-generator.desktop
rm -rf ~/.config/liminal ~/.local/share/liminal
rm -rf /chemin/vers/liminal-generation
```

## Organisation du projet

| Fichier | Rôle |
|---|---|
| `main.py` | Fenêtre, boutons, panneau de réglages, threads d'arrière-plan |
| `generator.py` | Assemblage du prompt et unicité (historique, anti-répétition, seed) |
| `providers.py` | Un appel HTTP par fournisseur, et la liste des modèles intégrés |
| `postprocess.py` | Aspect argentique local (Pillow) |
| `storage.py` | Config, téléchargement et enregistrement des images, métadonnées `.json` |
| `prompts/` | Fragments de prompt, un fichier texte par catégorie |
| `install.sh` | Installation en une étape |

## Mentions légales

- **Aucun lien avec les Backrooms, Kane Pixels ni aucun fournisseur d'images.** Les Backrooms et r/LiminalSpace ne sont que l'inspiration.
- Les images sont générées sur **ton propre** compte chez le fournisseur et facturées dessus. Ce que tu as le droit d'en faire dépend des conditions du fournisseur.
- Le code est sous [licence MIT](LICENSE).
