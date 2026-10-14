"""Test the LLM connection:  python -m app.api.llm_smoke

Reads LLM_BASE_URL, LLM_API_KEY and LLM_MODEL from .env or the environment. Prints a block to post in the team chat.
The API key is never printed.
"""
import json
import sys

from .envfile import load_env
from .llm import LLMClient, LLMError

HINTS = {401: "The key was rejected: check LLM_API_KEY.", 403: "The key was rejected: check LLM_API_KEY.",
         404: "Not found: check LLM_BASE_URL (with or without /v1) and LLM_MODEL.",
         429: "Rate limited: the whole team shares one key. Wait a minute and retry."}


def main() -> int:
    load_env()
    try:
        llm = LLMClient.from_env()
    except LLMError as e:
        print(e)
        return 1
    print(f"Server: {llm.base_url}\nModel:  {llm.model}\nKey:    set (not shown)\n")
    try:
        ids = llm.list_models()
        print(f"Models offered ({len(ids)}): {', '.join(ids[:15])}\n")
    except Exception as e:  # not every server has /models
        print(f"(model list not available: {type(e).__name__})\n")
    try:
        r = llm.chat([{"role": "system", "content": "You are a bearing maintenance assistant."},
                      {"role": "user", "content": "In one sentence, what causes outer race bearing faults?"}],
                     json_mode=False, max_tokens=120)
        print(f"Reply: {r.text.strip()}\nLatency: {r.latency_ms} ms, attempts: {r.attempts}, usage: {r.usage}\n")
        j = llm.chat([{"role": "user", "content": 'Reply with only this JSON: {"ok": true}'}], max_tokens=30)
        try:
            json_ok = json.loads(j.text.strip().strip("`").removeprefix("json").strip()).get("ok") is True
        except ValueError:
            json_ok = False
        print(f"JSON mode: {'accepted' if llm.json_mode else 'rejected by the server (we fall back to prompting)'}; "
              f"valid JSON came back: {json_ok}\n")
    except LLMError as e:
        print(f"FAILED: {e}\n{HINTS.get(e.status, '')}")
        return 1
    print("--- post this in the team chat (no key!) ---")
    print(f"LLM works. base URL: {llm.base_url}  model: {llm.model}  latency: {r.latency_ms} ms  "
          f"JSON mode: {'yes' if llm.json_mode else 'no'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
