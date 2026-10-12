# Changelog

## [0.1.0] - 2026-10-12

First release.

- One-button app (CustomTkinter, dark theme) that generates a new 16:9 liminal space / Backrooms image on each click.
- Procedural prompts from plain-text fragments in `prompts/`: places, walls, floors, lighting, cameras, viewpoints,
  details and subtle anomalies, with `{slot}` placeholders.
- Uniqueness: every combination is remembered and never drawn again, and recent places and lightings are not repeated.
- Rare unsettling human presences: about one image in six, never two in a row, replacing the anomaly.
- Local analog post-process with random strength: low resolution, blur, chromatic aberration, faded colours, grain.
- Providers called over plain HTTP with your own key: Replicate, fal.ai, OpenAI and Google, with indicative prices
  and custom model ids. FLUX.1 schnell on Replicate is the default.
- Settings panel ⚙: provider, masked API key (environment variables take precedence), model, free key check.
- *Save as*: native dialog (zenity, Tk fallback), PNG plus a `.json` with prompt, provider, model and seed.
- Keyboard shortcuts: `Space`/`Enter` to generate, `Ctrl+S` to save, `Esc` to quit.
- The window never freezes: every network call and file write runs in a background thread.
- `install.sh`: Python and tkinter checks, virtual environment, app menu shortcut.

[0.1.0]: https://github.com/boomer24vs/liminal-generation/releases/tag/v0.1.0
