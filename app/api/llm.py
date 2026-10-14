"""Client for an OpenAI-compatible chat endpoint (AMD Token Factory, or our own vLLM server).

Plain httpx, no SDK. The whole team shares ONE key, so 429 (rate limit) is expected under load:
- 429 and 5xx are retried with exponential backoff and jitter, honoring Retry-After
- at most LLM_MAX_CONCURRENT calls run at once from this app (default 2)
- the API key is only ever sent in the Authorization header: never logged, printed, or put in an error message
"""
import os
import random
import threading
import time
from dataclasses import dataclass, field

import httpx

RETRY_STATUS = {429, 500, 502, 503, 504}
MAX_WAIT_S = 20.0


class LLMError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


@dataclass
class LLMReply:
    text: str
    model: str
    latency_ms: int
    attempts: int
    usage: dict = field(default_factory=dict)


class LLMClient:
    def __init__(self, base_url, api_key, model, *, timeout=60.0, max_retries=3, max_concurrent=2,
                 transport=None, sleep=time.sleep):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.max_retries = max_retries
        self._key = api_key
        self._sleep = sleep
        self._http = httpx.Client(timeout=timeout, transport=transport)
        self._slots = threading.BoundedSemaphore(max(1, max_concurrent))
        self.json_mode = True  # turned off for good if the server rejects response_format

    def __repr__(self):
        return f"LLMClient(base_url={self.base_url!r}, model={self.model!r})"

    @classmethod
    def from_env(cls, **kwargs):
        values = {n: os.environ.get(n, "").strip() for n in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL")}
        missing = [n for n, v in values.items() if not v or v == "replace-me"]
        if missing:
            raise LLMError("LLM not configured: set " + ", ".join(missing) + " (copy .env.example to .env).")
        return cls(values["LLM_BASE_URL"], values["LLM_API_KEY"], values["LLM_MODEL"],
                   max_concurrent=int(os.environ.get("LLM_MAX_CONCURRENT", "2")), **kwargs)

    def _headers(self):
        return {"Authorization": f"Bearer {self._key}"}

    def _clean(self, text):
        return text.replace(self._key, "***")[:200]

    def _delay(self, retries, retry_after):
        if retry_after is not None:
            return min(retry_after, MAX_WAIT_S)
        return min(MAX_WAIT_S, 2 ** (retries - 1)) * (0.75 + 0.5 * random.random())

    def list_models(self):
        """Best effort: ids from GET /models (not every server offers it)."""
        r = self._http.get(f"{self.base_url}/models", headers=self._headers())
        r.raise_for_status()
        return [m.get("id") for m in r.json().get("data", [])]

    def chat(self, messages, *, temperature=0.2, max_tokens=900, json_mode=True) -> LLMReply:
        payload = {"model": self.model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
        use_json = json_mode and self.json_mode
        if use_json:
            payload["response_format"] = {"type": "json_object"}
        start, calls, retries = time.perf_counter(), 0, 0
        with self._slots:
            while True:
                calls += 1
                try:
                    r = self._http.post(f"{self.base_url}/chat/completions", json=payload, headers=self._headers())
                except httpx.TransportError as e:  # timeout, connection refused, DNS ...
                    err, retry_after = LLMError(f"network error: {type(e).__name__}"), None
                else:
                    if r.status_code == 200:
                        return self._reply(r, start, calls)
                    if r.status_code == 400 and use_json:  # server may not know response_format: try without it
                        use_json = self.json_mode = False
                        payload.pop("response_format", None)
                        continue
                    err = LLMError(f"HTTP {r.status_code}: {self._clean(r.text)}", r.status_code)
                    if r.status_code not in RETRY_STATUS:
                        raise err
                    try:
                        retry_after = float(r.headers["Retry-After"])
                    except (KeyError, ValueError):
                        retry_after = None
                if retries >= self.max_retries:
                    raise err
                retries += 1
                self._sleep(self._delay(retries, retry_after))

    def _reply(self, r, start, calls):
        try:
            data = r.json()
            text = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise LLMError("unexpected response shape from the LLM server") from None
        if not isinstance(text, str):
            raise LLMError("the LLM server returned no text")
        return LLMReply(text=text, model=str(data.get("model") or self.model),
                        latency_ms=round((time.perf_counter() - start) * 1000), attempts=calls,
                        usage=data.get("usage") or {})
