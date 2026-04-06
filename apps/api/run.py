from __future__ import annotations

import importlib.util
import os
import subprocess
import sys


def has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def run() -> int:
    python = sys.executable
    env = dict(os.environ)
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    host = env.get("API_HOST", "0.0.0.0")
    port = env.get("API_PORT", "8000")

    if has_module("fastapi") and has_module("uvicorn"):
        command = [python, "-m", "uvicorn", "app.main:app", "--host", host, "--port", port]
    else:
        command = [python, "-m", "app.local_server"]

    return subprocess.call(command, cwd=os.path.dirname(__file__), env=env)


if __name__ == "__main__":
    raise SystemExit(run())
