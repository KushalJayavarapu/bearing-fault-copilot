"""Run every self-check:  python -m app.api.test_all   (from the repo root)"""
import sys

from . import test_api, test_llm, test_orchestrator

if __name__ == "__main__":
    total = 0
    for mod in (test_api, test_llm, test_orchestrator):
        tests = [(n, f) for n, f in sorted(vars(mod).items()) if n.startswith("test_") and callable(f) and f.__module__ == mod.__name__]
        for name, fn in tests:
            fn()
        total += len(tests)
        print(f"{mod.__name__.split('.')[-1]:<18} {len(tests)} checks passed")
    print(f"ALL {total} checks passed")
    sys.exit(0)
