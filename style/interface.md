# Interface — spécification

Source de vérité pour l'UI. À mettre à jour avant toute refonte.

## Principes
- Minimalisme : seulement l'essentiel à l'écran. Pas de prompt, pas de nom de modèle, pas de barre de statut permanente.
- Thème sombre (CustomTkinter, mode `dark`).
- Textes de l'interface en **anglais**.
- L'UI ne se fige jamais : tout appel réseau / I/O lourd tourne dans un thread.

## Fenêtre principale
- Taille par défaut : **640×400**, redimensionnable, minimum **480×330**. La dernière taille est mémorisée dans la config.
- Disposition :

```
┌──────────────────────────────────────┐
│                                      │
│          zone image 16:9             │
│                                      │
├──────────────────────────────────────┤
│ [  Generate  ]  [  Save  ]        ⚙  │  ← barre ~60 px
└──────────────────────────────────────┘
```

- Zone image : ratio 16:9 conservé lors du redimensionnement, fond gris très sombre.
  - Au démarrage : vide.
  - Image non 16:9 (ex. OpenAI 1536×1024) : affichée entière, bandes de la couleur du fond. **À l'écran uniquement**, le fichier garde sa résolution d'origine.
- Messages : texte discret centré en overlay sur la zone image, jamais de popup.
  - Pendant la génération : `generating…` (l'image précédente reste visible dessous).
  - Erreur (token invalide, modèle inconnu, réseau, quota, timeout) : message court, disparaît après quelques secondes, image précédente conservée.
  - Après enregistrement : `saved` pendant ~2 s.
  - Aucun token disponible : `Add an API token in ⚙`, bouton Generate désactivé.
- `Generate` désactivé pendant une génération (pas d'annulation). Timeout réseau : 120 s, pas de retry automatique.
- `Save` désactivé tant qu'aucune image n'est affichée.
- Régénérer sans enregistrer : l'image précédente est perdue, sans avertissement.

## Taille des contrôles
- Contrôles larges et faciles à cliquer : boutons de 44 px de haut, texte en 16 px (⚙ en 22 px).
- Panneau ⚙ : champs et menus de 38 px de haut, texte en 15 px.

## Raccourcis (non affichés)
| Touche | Action |
|---|---|
| `Space` / `Enter` | Generate |
| `Ctrl+S` | Save |
| `Esc` | Quitter |

## Enregistrement (« Save as »)
- Boîte native GNOME via `zenity --file-selection --save`, repli sur `tkinter.filedialog` si `zenity` est absent.
- Dossier proposé : dernier dossier utilisé (`generated/` au premier lancement).
- Nom proposé : `YYYYMMDD-HHMMSS_<slug-environnement>.png` (ex. `20261004-213015_flooded-poolroom.png`).
- Toujours en PNG (conversion locale si besoin) + fichier `.json` du même nom à côté :
  `prompt`, `provider`, `model`, `seed` (`null` si non supporté), `width`, `height`, `created_at`, `fragments` tirés.

## Panneau ⚙ (fenêtre séparée, petite)
- **Provider** : liste déroulante (Replicate, fal.ai, OpenAI, Google).
- **API token** : champ masqué + bouton 👁. Si le token vient d'une variable d'environnement, mention `(from env)` et champ non éditable.
  - Coller un token au préfixe reconnu (`r8_` → Replicate, `sk-` → OpenAI, `AIza` → Google) pré-sélectionne le provider.
- **Model** : liste déroulante avec prix indicatif (ex. `FLUX.1 schnell — $0.003`), + entrée `custom…` qui fait apparaître un champ texte pour l'identifiant du modèle.
- **Verify** : teste le token par un appel gratuit (aucune génération facturée), affiche `ok` / l'erreur sous le bouton.
- Enregistrement automatique à la fermeture. Le couple provider + modèle sélectionné devient celui utilisé par Generate.

## Modèles prédéfinis
| Provider | Modèles | Prix indicatif | 16:9 natif |
|---|---|---|---|
| Replicate | FLUX.1 schnell (**défaut global**) · FLUX.1 dev · FLUX 1.1 pro | 0,003 $ · 0,025 $ · 0,04 $ | oui |
| fal.ai | FLUX.1 schnell · FLUX.1 dev · FLUX 2 pro | ≈0,003 $ · ≈0,025 $ · ≈0,05 $ | oui |
| OpenAI | GPT Image 1 Mini · GPT Image 2 (qualité `medium` fixe) | ≈0,01 $ · ≈0,04 $ | non → 1536×1024 |
| Google | Imagen 4 Fast · Imagen 4 · Gemini 2.5 Flash Image | 0,02 $ · 0,04 $ · 0,039 $ | oui |

- Modèle natif 16:9 : demandé en 16:9. Sinon : résolution la plus proche supportée, **sans recadrage**.
- Modèle `custom…` : envoi de `prompt` + ratio 16:9 + `seed`. Sur erreur de validation (non facturée) uniquement, un seul retry avec `prompt` seul.

## Stockage local
- Config : `~/.config/liminal/config.json` (permissions `600`) — tokens par provider, provider/modèle actifs, taille de fenêtre, dernier dossier.
- Variables d'environnement prioritaires : `REPLICATE_API_TOKEN`, `FAL_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`.
- Historique des combinaisons : `~/.local/share/liminal/history.json`.
