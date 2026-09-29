"""Offline tests for groq_client request building + fallback (urlopen mocked)."""
import io
import json
import os
import sys
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../lambda/ai_analyzer"))
import groq_client  # noqa: E402


def _with_key(fn):
    """Run fn with a fake key, restoring the environment afterwards."""
    def wrapper():
        old = os.environ.get("GROQ_API_KEY")
        os.environ["GROQ_API_KEY"] = "gsk_test"
        try:
            fn()
        finally:
            if old is None:
                os.environ.pop("GROQ_API_KEY", None)
            else:
                os.environ["GROQ_API_KEY"] = old
    wrapper.__name__ = fn.__name__
    return wrapper


class FakeResp:
    def __init__(self, obj): self._b = json.dumps(obj).encode()
    def read(self): return self._b
    def __enter__(self): return self
    def __exit__(self, *a): return False


def _ok(content):
    return FakeResp({"choices": [{"message": {"content": content}}], "usage": {"total_tokens": 10}})


@_with_key
def test_default_models_and_gpt_oss_params():
    sent = []
    orig = groq_client.urllib.request.urlopen
    groq_client.urllib.request.urlopen = lambda req, timeout=0: (
        sent.append(json.loads(req.data)), _ok('{"summary":"s","root_cause":"r","severity":"low","immediate_actions":["a"]}'))[1]
    try:
        out = groq_client.invoke("hi")
    finally:
        groq_client.urllib.request.urlopen = orig
    assert sent[0]["model"] == "openai/gpt-oss-120b"
    assert sent[0]["reasoning_effort"] == "low"
    assert sent[0]["response_format"] == {"type": "json_object"}
    assert out["severity"] == "LOW"


@_with_key
def test_falls_back_to_second_model_on_404():
    calls = []

    def fake(req, timeout=0):
        m = json.loads(req.data)["model"]
        calls.append(m)
        if m == "openai/gpt-oss-120b":
            raise urllib.error.HTTPError("u", 404, "nf", {}, io.BytesIO(b'{"error":"model_not_found"}'))
        return _ok('{"summary":"s","root_cause":"r","severity":"HIGH","immediate_actions":["a"]}')

    orig = groq_client.urllib.request.urlopen
    groq_client.urllib.request.urlopen = fake
    try:
        groq_client.invoke("hi")
    finally:
        groq_client.urllib.request.urlopen = orig
    assert calls == ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]


if __name__ == "__main__":
    test_default_models_and_gpt_oss_params()
    test_falls_back_to_second_model_on_404()
    print("Results: 2 passed, 0 failed")
