import base64

import pytest
import requests

import providers

PNG = b"\x89PNG fake"


class FakeResponse:
    def __init__(self, status=200, json_data=None, content=b""):
        self.status_code = status
        self.ok = status < 400
        self._json = json_data if json_data is not None else {}
        self.content = content

    def json(self):
        return self._json


@pytest.fixture
def calls(monkeypatch):
    """Queue of fake responses; records every request made."""
    state = {"responses": [], "requests": []}

    def fake_request(method, url, timeout=None, **kwargs):
        state["requests"].append((method, url, kwargs))
        response = state["responses"].pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(providers.requests, "request", fake_request)
    monkeypatch.setattr(providers.time, "sleep", lambda _s: None)
    return state


def test_detect_provider():
    assert providers.detect_provider("r8_abc") == "replicate"
    assert providers.detect_provider(" sk-proj-x") == "openai"
    assert providers.detect_provider("AIzaSy") == "google"
    assert providers.detect_provider("1234:abcd") is None


def test_every_provider_has_models_and_default_exists():
    for key in providers.PROVIDERS:
        assert providers.models_for(key)
    assert providers.find_model(providers.DEFAULT_PROVIDER, providers.DEFAULT_MODEL)


def test_replicate_official_model_with_polling(calls):
    calls["responses"] = [
        FakeResponse(json_data={"status": "starting", "urls": {"get": "https://api.replicate.com/p/1"}}),
        FakeResponse(json_data={"status": "succeeded", "output": ["https://cdn/img.png"]}),
        FakeResponse(content=PNG),
    ]
    result = providers.generate_image("replicate", "black-forest-labs/flux-schnell", "p", 42, "r8_x")
    assert result.data == PNG and result.seed == 42
    method, url, kwargs = calls["requests"][0]
    assert url.endswith("/models/black-forest-labs/flux-schnell/predictions")
    assert kwargs["json"]["input"] == {"prompt": "p", "aspect_ratio": "16:9", "seed": 42, "output_format": "png"}
    assert kwargs["headers"]["Authorization"] == "Bearer r8_x"


def test_replicate_versioned_model_and_string_output(calls):
    calls["responses"] = [
        FakeResponse(json_data={"status": "succeeded", "output": "https://cdn/img.png"}),
        FakeResponse(content=PNG),
    ]
    providers.generate_image("replicate", "me/model:abc123", "p", 1, "t")
    _, url, kwargs = calls["requests"][0]
    assert url == "https://api.replicate.com/v1/predictions"
    assert kwargs["json"]["version"] == "abc123"


def test_replicate_failed_prediction(calls):
    calls["responses"] = [FakeResponse(json_data={"status": "failed", "error": "NSFW"})]
    with pytest.raises(providers.ProviderError, match="NSFW"):
        providers.generate_image("replicate", "black-forest-labs/flux-schnell", "p", 1, "t")


def test_fal(calls):
    calls["responses"] = [
        FakeResponse(json_data={"images": [{"url": "https://fal/img.png"}], "seed": 7}),
        FakeResponse(content=PNG),
    ]
    result = providers.generate_image("fal", "fal-ai/flux/schnell", "p", 7, "key")
    assert result.data == PNG and result.seed == 7
    _, url, kwargs = calls["requests"][0]
    assert url == "https://fal.run/fal-ai/flux/schnell"
    assert kwargs["headers"]["Authorization"] == "Key key"
    assert kwargs["json"]["image_size"] == "landscape_16_9"


def test_fal_data_uri(calls):
    data_uri = "data:image/png;base64," + base64.b64encode(PNG).decode()
    calls["responses"] = [FakeResponse(json_data={"images": [{"url": data_uri}]})]
    assert providers.generate_image("fal", "fal-ai/flux/dev", "p", 1, "k").data == PNG


def test_openai_uses_model_size_and_medium_quality(calls):
    calls["responses"] = [FakeResponse(json_data={"data": [{"b64_json": base64.b64encode(PNG).decode()}]})]
    result = providers.generate_image("openai", "gpt-image-2", "p", 1, "sk-x")
    assert result.data == PNG and result.seed is None
    body = calls["requests"][0][2]["json"]
    assert body["size"] == "1536x1024" and body["quality"] == "medium"


def test_google_inline_data(calls):
    payload = {"candidates": [{"content": {"parts": [{"text": "hi"},
                                                     {"inlineData": {"data": base64.b64encode(PNG).decode()}}]}}]}
    calls["responses"] = [FakeResponse(json_data=payload)]
    result = providers.generate_image("google", "gemini-2.5-flash-image", "p", 1, "AIza")
    assert result.data == PNG
    _, url, kwargs = calls["requests"][0]
    assert url.endswith("/models/gemini-2.5-flash-image:generateContent")
    assert kwargs["json"]["generationConfig"]["imageConfig"]["aspectRatio"] == "16:9"


def test_google_blocked(calls):
    calls["responses"] = [FakeResponse(json_data={"promptFeedback": {"blockReason": "SAFETY"}})]
    with pytest.raises(providers.ProviderError, match="SAFETY"):
        providers.generate_image("google", "gemini-2.5-flash-image", "p", 1, "AIza")


@pytest.mark.parametrize("status, body, message", [
    (401, {}, "invalid token"),
    (400, {"error": {"message": "API key not valid. Please pass a valid API key."}}, "invalid token"),
    (404, {}, "unknown model"),
    (429, {}, "quota"),
    (500, {}, "provider error 500"),
])
def test_error_mapping(calls, status, body, message):
    calls["responses"] = [FakeResponse(status, body)]
    with pytest.raises(providers.ProviderError, match=message):
        providers.generate_image("openai", "gpt-image-2", "p", 1, "sk")


def test_network_errors(calls):
    calls["responses"] = [requests.Timeout()]
    with pytest.raises(providers.ProviderError, match="timeout"):
        providers.generate_image("fal", "fal-ai/flux/dev", "p", 1, "k")
    calls["responses"] = [requests.ConnectionError()]
    with pytest.raises(providers.ProviderError, match="network"):
        providers.generate_image("fal", "fal-ai/flux/dev", "p", 1, "k")


def test_custom_model_retries_once_with_prompt_only(calls):
    calls["responses"] = [
        FakeResponse(422, {"detail": "unexpected aspect_ratio"}),
        FakeResponse(json_data={"status": "succeeded", "output": "https://cdn/x.png"}),
        FakeResponse(content=PNG),
    ]
    result = providers.generate_image("replicate", "someone/model", "p", 3, "t", custom=True)
    assert result.data == PNG and result.seed is None
    assert calls["requests"][1][2]["json"]["input"] == {"prompt": "p"}


def test_preset_model_does_not_retry(calls):
    calls["responses"] = [FakeResponse(422, {"detail": "bad"})]
    with pytest.raises(providers.InvalidParams):
        providers.generate_image("replicate", "black-forest-labs/flux-schnell", "p", 3, "t")
    assert len(calls["requests"]) == 1


@pytest.mark.parametrize("provider", list(providers.PROVIDERS))
def test_verify_uses_get_only(calls, provider):
    calls["responses"] = [FakeResponse(json_data={})]
    providers.verify_token(provider, "tok")
    assert calls["requests"][0][0] == "GET"
