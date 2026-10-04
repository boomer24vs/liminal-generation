"""Image providers: one plain HTTP function per provider (requests only, no SDK)."""

import base64
import time
from dataclasses import dataclass

import requests

TIMEOUT = 120  # seconds, whole generation
CUSTOM = "custom"


@dataclass(frozen=True)
class Provider:
    key: str
    label: str
    env_var: str
    token_prefix: str | None  # used to pre-select the provider when a token is pasted


@dataclass(frozen=True)
class Model:
    provider: str
    id: str
    label: str
    price: str  # indicative, per image
    native_16x9: bool
    size: str | None = None  # OpenAI only


PROVIDERS = {
    "replicate": Provider("replicate", "Replicate", "REPLICATE_API_TOKEN", "r8_"),
    "fal": Provider("fal", "fal.ai", "FAL_KEY", None),
    "openai": Provider("openai", "OpenAI", "OPENAI_API_KEY", "sk-"),
    "google": Provider("google", "Google", "GEMINI_API_KEY", "AIza"),
}

MODELS = [
    Model("replicate", "black-forest-labs/flux-schnell", "FLUX.1 schnell", "$0.003", True),
    Model("replicate", "black-forest-labs/flux-dev", "FLUX.1 dev", "$0.025", True),
    Model("replicate", "black-forest-labs/flux-1.1-pro", "FLUX 1.1 pro", "$0.04", True),
    Model("fal", "fal-ai/flux/schnell", "FLUX.1 schnell", "~$0.003", True),
    Model("fal", "fal-ai/flux/dev", "FLUX.1 dev", "~$0.025", True),
    Model("fal", "fal-ai/flux-2-pro", "FLUX 2 pro", "~$0.05", True),
    Model("openai", "gpt-image-2.5-flare", "GPT Image 2.5 Flare", "~$0.05", True, "1536x864"),
    Model("openai", "gpt-image-2", "GPT Image 2", "~$0.04", False, "1536x1024"),
    Model("google", "gemini-3.1-flash-lite-image", "Gemini 3.1 Flash Lite Image", "$0.034", True),
    Model("google", "gemini-2.5-flash-image", "Gemini 2.5 Flash Image", "$0.039", True),
    Model("google", "gemini-3.1-flash-image", "Gemini 3.1 Flash Image", "~$0.067", True),
]

DEFAULT_PROVIDER = "replicate"
DEFAULT_MODEL = "black-forest-labs/flux-schnell"


class ProviderError(Exception):
    """Short, user-facing error message."""


class InvalidParams(ProviderError):
    """The API rejected the request parameters (not billed): a custom model may retry with the prompt only."""


@dataclass
class ImageResult:
    data: bytes
    seed: int | None


def models_for(provider):
    return [m for m in MODELS if m.provider == provider]


def find_model(provider, model_id):
    return next((m for m in models_for(provider) if m.id == model_id), None)


def detect_provider(token):
    token = token.strip()
    return next((p.key for p in PROVIDERS.values() if p.token_prefix and token.startswith(p.token_prefix)), None)


def _check(response):
    """Map HTTP errors to short messages."""
    if response.ok:
        return response
    try:
        body = response.json()
    except ValueError:
        body = {}
    full = str(body.get("detail") or body.get("error") or body)
    detail = full[:200]
    status = response.status_code
    if status in (401, 403) or "API key not valid" in full or "API_KEY_INVALID" in full:
        raise ProviderError("invalid token")
    if status == 404:
        raise ProviderError("unknown model")
    if status in (402, 429):
        raise ProviderError("quota or rate limit reached")
    if status in (400, 422):
        raise InvalidParams(f"invalid parameters: {detail}")
    raise ProviderError(f"provider error {status}")


def _request(method, url, deadline, **kwargs):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ProviderError("timeout")
    try:
        return _check(requests.request(method, url, timeout=remaining, **kwargs))
    except requests.Timeout:
        raise ProviderError("timeout") from None
    except requests.ConnectionError:
        raise ProviderError("network error") from None


def _download(url, deadline):
    if url.startswith("data:"):
        return base64.b64decode(url.split(",", 1)[1])
    return _request("GET", url, deadline).content


# --- Replicate -----------------------------------------------------------

def _replicate(model_id, prompt, seed, token, deadline, minimal):
    headers = {"Authorization": f"Bearer {token}", "Prefer": "wait=60"}
    params = {"prompt": prompt}
    if not minimal:
        params.update(aspect_ratio="16:9", seed=seed, output_format="png")
    if ":" in model_id:  # owner/name:version
        url = "https://api.replicate.com/v1/predictions"
        body = {"version": model_id.split(":", 1)[1], "input": params}
    else:
        url = f"https://api.replicate.com/v1/models/{model_id}/predictions"
        body = {"input": params}
    prediction = _request("POST", url, deadline, headers=headers, json=body).json()
    while prediction.get("status") in ("starting", "processing"):
        time.sleep(2)
        prediction = _request("GET", prediction["urls"]["get"], deadline, headers=headers).json()
    if prediction.get("status") != "succeeded":
        raise ProviderError(str(prediction.get("error") or "generation failed")[:200])
    output = prediction.get("output")
    url = output[0] if isinstance(output, list) else output
    if not isinstance(url, str):
        raise ProviderError("no image returned")
    return ImageResult(_download(url, deadline), None if minimal else seed)


def _replicate_verify(token, deadline):
    _request("GET", "https://api.replicate.com/v1/account", deadline, headers={"Authorization": f"Bearer {token}"})


# --- fal.ai --------------------------------------------------------------

def _fal(model_id, prompt, seed, token, deadline, minimal):
    params = {"prompt": prompt}
    if not minimal:
        params.update(image_size="landscape_16_9", seed=seed, output_format="png", num_images=1)
    result = _request(
        "POST", f"https://fal.run/{model_id}", deadline, headers={"Authorization": f"Key {token}"}, json=params
    ).json()
    images = result.get("images") or []
    if not images:
        raise ProviderError("no image returned")
    return ImageResult(_download(images[0]["url"], deadline), result.get("seed", None if minimal else seed))


def _fal_verify(token, deadline):
    # Free listing endpoint; an invalid key is rejected with 401/403.
    _request("GET", "https://api.fal.ai/v1/models", deadline, headers={"Authorization": f"Key {token}"},
             params={"limit": 1})


# --- OpenAI --------------------------------------------------------------

def _openai(model_id, prompt, seed, token, deadline, minimal):
    params = {"model": model_id, "prompt": prompt, "n": 1}
    if not minimal:
        model = find_model("openai", model_id)
        params.update(size=model.size if model else "1536x1024", quality="medium", output_format="png")
    result = _request(
        "POST", "https://api.openai.com/v1/images/generations", deadline,
        headers={"Authorization": f"Bearer {token}"}, json=params,
    ).json()
    item = (result.get("data") or [{}])[0]
    if item.get("b64_json"):
        return ImageResult(base64.b64decode(item["b64_json"]), None)
    if item.get("url"):
        return ImageResult(_download(item["url"], deadline), None)
    raise ProviderError("no image returned")


def _openai_verify(token, deadline):
    _request("GET", "https://api.openai.com/v1/models", deadline, headers={"Authorization": f"Bearer {token}"})


# --- Google (Gemini API) -------------------------------------------------

GOOGLE_API = "https://generativelanguage.googleapis.com/v1beta"


def _google(model_id, prompt, seed, token, deadline, minimal):
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    if not minimal:
        body["generationConfig"] = {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "16:9"}}
    result = _request(
        "POST", f"{GOOGLE_API}/models/{model_id}:generateContent", deadline,
        headers={"x-goog-api-key": token}, json=body,
    ).json()
    for candidate in result.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                return ImageResult(base64.b64decode(inline["data"]), None)
    reason = result.get("promptFeedback", {}).get("blockReason")
    raise ProviderError(f"blocked: {reason}" if reason else "no image returned")


def _google_verify(token, deadline):
    _request("GET", f"{GOOGLE_API}/models", deadline, headers={"x-goog-api-key": token}, params={"pageSize": 1})


# --- Dispatch ------------------------------------------------------------

_GENERATORS = {"replicate": _replicate, "fal": _fal, "openai": _openai, "google": _google}
_VERIFIERS = {"replicate": _replicate_verify, "fal": _fal_verify, "openai": _openai_verify, "google": _google_verify}


def generate_image(provider, model_id, prompt, seed, token, custom=False, timeout=TIMEOUT):
    """Generate one image. A custom model retries once with the prompt only if its parameters are rejected."""
    deadline = time.monotonic() + timeout
    generate = _GENERATORS[provider]
    try:
        return generate(model_id, prompt, seed, token, deadline, minimal=False)
    except InvalidParams:
        if not custom:
            raise
        return generate(model_id, prompt, seed, token, deadline, minimal=True)


def verify_token(provider, token, timeout=15):
    """Raise ProviderError if the token is rejected. Never triggers a billed generation."""
    _VERIFIERS[provider](token, time.monotonic() + timeout)
