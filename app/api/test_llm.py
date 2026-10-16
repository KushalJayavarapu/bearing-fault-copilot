"""Self-check for the LLM client and the .env loader (no network, no key):  python -m app.api.test_llm"""
import os
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import httpx

from .envfile import load_env
from .llm import LLMClient, LLMError

KEY = "sk-test-SECRET-123"


def _ok(text="hi", model="m1"):
    return httpx.Response(200, json={"model": model, "choices": [{"message": {"content": text}}],
                                     "usage": {"total_tokens": 5}})


def _client(handler, **kw):
    sleeps = []
    c = LLMClient("http://llm.test/v1/", KEY, "m1", transport=httpx.MockTransport(handler), sleep=sleeps.append, **kw)
    return c, sleeps


@contextmanager
def _env(**values):
    old = {k: os.environ.get(k) for k in values}
    for k, v in values.items():
        os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
    try:
        yield
    finally:
        for k, v in old.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)


def test_success_request_shape():
    seen = {}

    def handler(req):
        seen["url"], seen["auth"], seen["body"] = str(req.url), req.headers["authorization"], req.read()
        return _ok("answer")
    c, _ = _client(handler)
    r = c.chat([{"role": "user", "content": "x"}])
    assert seen["url"] == "http://llm.test/v1/chat/completions" and seen["auth"] == f"Bearer {KEY}"
    assert b'"model":"m1"' in seen["body"].replace(b" ", b"") and b"response_format" in seen["body"]
    assert (r.text, r.model, r.attempts, r.usage) == ("answer", "m1", 1, {"total_tokens": 5})
    assert KEY not in repr(c) and KEY not in str(vars(r))


def test_retries_429_and_honors_retry_after():
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(429, headers={"Retry-After": "2"}) if len(calls) == 1 else _ok()
    c, sleeps = _client(handler)
    assert c.chat([{"role": "user", "content": "x"}]).attempts == 2 and sleeps == [2.0]


def test_backoff_grows_and_gives_up():
    c, sleeps = _client(lambda req: httpx.Response(503, text="busy"), max_retries=3)
    try:
        c.chat([{"role": "user", "content": "x"}])
        raise AssertionError("should have failed")
    except LLMError as e:
        assert e.status == 503
    assert len(sleeps) == 3
    assert 0.75 <= sleeps[0] <= 1.25 and 1.5 <= sleeps[1] <= 2.5 and 3.0 <= sleeps[2] <= 5.0


def test_long_retry_after_fails_fast_then_cools_down():
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(429, headers={"Retry-After": "60"}) if len(calls) <= 2 else _ok()
    c, sleeps = _client(handler)
    for expected_calls in (1, 1):  # the second call must not even reach the server
        try:
            c.chat([{"role": "user", "content": "x"}])
            raise AssertionError("should have failed")
        except LLMError as e:
            assert e.status == 429 and "wait" in str(e)
        assert len(calls) == expected_calls and sleeps == []
    c._blocked_until = 0.0  # the cooldown is over
    try:
        c.chat([{"role": "user", "content": "x"}])
        raise AssertionError("second 429 expected")
    except LLMError as e:
        assert e.status == 429 and len(calls) == 2
    c._blocked_until = 0.0
    assert c.chat([{"role": "user", "content": "x"}]).text == "hi"


def test_usage_endpoint():
    c, _ = _client(lambda req: httpx.Response(200, json={"remaining": 5}) if req.url.path == "/v1/usage" else httpx.Response(404))
    assert c.usage() == {"remaining": 5}


def test_auth_error_is_not_retried_and_hides_key():
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(401, text=f"invalid key {KEY}")
    c, sleeps = _client(handler)
    try:
        c.chat([{"role": "user", "content": "x"}])
        raise AssertionError("should have failed")
    except LLMError as e:
        assert e.status == 401 and KEY not in str(e) and "***" in str(e)
    assert len(calls) == 1 and sleeps == []


def test_network_errors_are_retried():
    calls = []

    def handler(req):
        calls.append(1)
        if len(calls) < 3:
            raise httpx.ConnectError("refused")
        return _ok()
    c, sleeps = _client(handler)
    assert c.chat([{"role": "user", "content": "x"}]).attempts == 3 and len(sleeps) == 2


def test_network_error_message_shows_the_reason():
    def handler(req):
        raise httpx.ConnectError("getaddrinfo failed")
    c, _ = _client(handler, max_retries=0)
    try:
        c.chat([{"role": "user", "content": "x"}])
        raise AssertionError("should have failed")
    except LLMError as e:
        assert "ConnectError" in str(e) and "getaddrinfo failed" in str(e) and e.status is None


def test_json_mode_fallback_is_remembered():
    bodies = []

    def handler(req):
        bodies.append(req.read())
        return httpx.Response(400, text="response_format not supported") if b"response_format" in bodies[-1] else _ok()
    c, sleeps = _client(handler)
    c.chat([{"role": "user", "content": "x"}])
    c.chat([{"role": "user", "content": "x"}])
    assert c.json_mode is False and sleeps == []
    assert [b"response_format" in b for b in bodies] == [True, False, False]


def test_bad_response_shape():
    c, _ = _client(lambda req: httpx.Response(200, json={"oops": 1}))
    try:
        c.chat([{"role": "user", "content": "x"}])
        raise AssertionError("should have failed")
    except LLMError as e:
        assert "unexpected response" in str(e)


def test_concurrency_is_capped():
    state, lock = {"now": 0, "max": 0}, threading.Lock()

    def handler(req):
        with lock:
            state["now"] += 1
            state["max"] = max(state["max"], state["now"])
        time.sleep(0.05)
        with lock:
            state["now"] -= 1
        return _ok()
    c, _ = _client(handler, max_concurrent=1)
    threads = [threading.Thread(target=c.chat, args=([{"role": "user", "content": "x"}],)) for _ in range(4)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert state["max"] == 1


def test_from_env():
    names = dict(LLM_BASE_URL=None, LLM_API_KEY=None, LLM_MODEL=None, LLM_MAX_CONCURRENT=None)
    with _env(**names):
        try:
            LLMClient.from_env()
            raise AssertionError("should have failed")
        except LLMError as e:
            assert all(n in str(e) for n in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"))
    with _env(**{**names, "LLM_BASE_URL": "http://x/v1", "LLM_API_KEY": "replace-me", "LLM_MODEL": "m"}):
        try:
            LLMClient.from_env()
            raise AssertionError("placeholder key must be rejected")
        except LLMError as e:
            assert "LLM_API_KEY" in str(e) and "LLM_MODEL" not in str(e)
    with _env(**{**names, "LLM_BASE_URL": "<the API base URL from the page>", "LLM_API_KEY": "<your key>", "LLM_MODEL": "<model>"}):
        try:
            LLMClient.from_env()
            raise AssertionError("template placeholders must be rejected")
        except LLMError as e:
            assert all(n in str(e) for n in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"))
    with _env(**{**names, "LLM_BASE_URL": "api.example.com/v1", "LLM_API_KEY": KEY, "LLM_MODEL": "m"}):
        try:
            LLMClient.from_env()
            raise AssertionError("a URL without http(s) must be rejected")
        except LLMError as e:
            assert "http://" in str(e)
    with _env(**{**names, "LLM_BASE_URL": "http://x/v1/", "LLM_API_KEY": KEY, "LLM_MODEL": "m"}):
        c = LLMClient.from_env()
        assert (c.base_url, c.model) == ("http://x/v1", "m") and KEY not in repr(c)


def test_env_file_loader():
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / ".env"
        f.write_text('# comment\n\nA_TEST_ONE=1\nA_TEST_TWO="two words"\nA_TEST_THREE=\'x\'\nA_TEST_KEEP=from-file\nbroken line\n',
                     encoding="utf-8")
        with _env(A_TEST_ONE=None, A_TEST_TWO=None, A_TEST_THREE=None, A_TEST_KEEP="from-env"):
            assert load_env(f) is True
            assert os.environ["A_TEST_ONE"] == "1" and os.environ["A_TEST_TWO"] == "two words"
            assert os.environ["A_TEST_THREE"] == "x" and os.environ["A_TEST_KEEP"] == "from-env"
            for k in ("A_TEST_ONE", "A_TEST_TWO", "A_TEST_THREE"):
                os.environ.pop(k, None)
        assert load_env(Path(d) / "missing.env") is False


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for name, fn in tests:
        fn()
        print("ok  ", name)
    print(f"{len(tests)} checks passed")
