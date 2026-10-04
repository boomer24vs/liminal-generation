import io
import json
import stat
from datetime import datetime

from PIL import Image

import storage


def png_bytes(size=(32, 18), fmt="PNG"):
    buffer = io.BytesIO()
    Image.new("RGB", size, "yellow").save(buffer, format=fmt)
    return buffer.getvalue()


def test_config_defaults_and_roundtrip_with_private_permissions(tmp_path):
    path = tmp_path / "sub" / "config.json"
    config = storage.load_config(path)
    assert config["provider"] == "replicate" and config["geometry"] == "640x400"
    config["tokens"]["fal"] = "secret"
    storage.save_config(config, path)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert storage.load_config(path)["tokens"]["fal"] == "secret"


def test_corrupted_config_falls_back_to_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{not json")
    assert storage.load_config(path)["provider"] == "replicate"


def test_env_token_takes_precedence():
    config = storage.load_config("/nonexistent")
    config["tokens"]["replicate"] = "from-config"
    assert storage.get_token(config, "replicate", {}) == ("from-config", False)
    assert storage.get_token(config, "replicate", {"REPLICATE_API_TOKEN": "env"}) == ("env", True)
    assert storage.get_token(config, "openai", {}) == ("", False)


def test_active_model():
    config = storage.load_config("/nonexistent")
    assert storage.active_model(config) == ("replicate", "black-forest-labs/flux-schnell", False)
    config["provider"] = "fal"
    assert storage.active_model(config) == ("fal", "fal-ai/flux/schnell", False)
    config["models"]["fal"] = "custom"
    config["custom_models"]["fal"] = " fal-ai/other "
    assert storage.active_model(config) == ("fal", "fal-ai/other", True)


def test_suggested_filename():
    name = storage.suggested_filename("flooded-poolroom", datetime(2026, 10, 4, 21, 30, 15))
    assert name == "20261004-213015_flooded-poolroom.png"


def test_save_image_converts_to_png_and_writes_metadata(tmp_path):
    path = storage.save_image(png_bytes(fmt="JPEG"), tmp_path / "out" / "img.jpg", {"prompt": "p", "seed": None})
    assert path.suffix == ".png"
    assert Image.open(path).format == "PNG"
    metadata = json.loads(path.with_suffix(".json").read_text())
    assert metadata == {"prompt": "p", "seed": None, "width": 32, "height": 18}


def test_history_roundtrip(tmp_path):
    import generator
    path = tmp_path / "h" / "history.json"
    history = generator.History(combos={"k"}, recent=[{"environment": "e", "lighting": "l"}])
    storage.save_history(history, path)
    assert storage.load_history(path).combos == {"k"}
    assert storage.load_history(tmp_path / "missing.json").combos == set()
