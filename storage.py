"""Local storage: config, history, image saving and the "Save as" dialog."""

import io
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from PIL import Image

import generator
import providers

CONFIG_PATH = Path.home() / ".config" / "liminal" / "config.json"
HISTORY_PATH = Path.home() / ".local" / "share" / "liminal" / "history.json"
DEFAULT_SAVE_DIR = Path(__file__).parent / "generated"

DEFAULT_CONFIG = {
    "provider": providers.DEFAULT_PROVIDER,
    "models": {"replicate": providers.DEFAULT_MODEL},  # provider -> model id, or providers.CUSTOM
    "custom_models": {},  # provider -> custom model id
    "tokens": {},  # provider -> token (environment variables take precedence)
    "geometry": "640x400",
    "last_dir": str(DEFAULT_SAVE_DIR),
}


def _read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def load_config(path=CONFIG_PATH):
    config = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy
    config.update(_read_json(path))
    return config


def save_config(config, path=CONFIG_PATH):
    """Write the config readable by the owner only (it contains tokens)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    os.chmod(path, 0o600)


def get_token(config, provider, environ=os.environ):
    """Return (token, from_env). Environment variables take precedence over the config."""
    env_token = environ.get(providers.PROVIDERS[provider].env_var, "").strip()
    if env_token:
        return env_token, True
    return config["tokens"].get(provider, "").strip(), False


def active_model(config):
    """Return (provider, model_id, custom)."""
    provider = config["provider"]
    model_id = config["models"].get(provider) or providers.models_for(provider)[0].id
    if model_id == providers.CUSTOM:
        return provider, config["custom_models"].get(provider, "").strip(), True
    return provider, model_id, False


def load_history(path=HISTORY_PATH):
    return generator.History.from_dict(_read_json(path))


def save_history(history, path=HISTORY_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history.to_dict()), encoding="utf-8")


def suggested_filename(slug, now=None):
    return f"{(now or datetime.now()):%Y%m%d-%H%M%S}_{slug}.png"


def save_image(image_bytes, path, metadata):
    """Save as PNG (converting if needed) with a .json of the same name next to it. Returns the PNG path."""
    path = Path(path)
    if path.suffix.lower() != ".png":
        path = path.with_suffix(".png")
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.open(io.BytesIO(image_bytes))
    image.save(path, format="PNG")
    metadata = {**metadata, "width": image.width, "height": image.height}
    path.with_suffix(".json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def zenity_available():
    return shutil.which("zenity") is not None


def ask_save_path_zenity(initial_dir, filename):
    """Blocking native GNOME "Save as" dialog. Returns the chosen path, or None if cancelled."""
    result = subprocess.run(
        [
            "zenity", "--file-selection", "--save", "--title=Save image",
            f"--filename={Path(initial_dir) / filename}", "--file-filter=PNG images | *.png",
        ],
        capture_output=True, text=True,
    )
    path = result.stdout.strip()
    return path if result.returncode == 0 and path else None
