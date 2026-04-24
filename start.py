from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parent
    ai_layer_dir = project_root / "ai_layer"

    if not ai_layer_dir.exists():
        print("Error: ai_layer directory not found.", file=sys.stderr)
        return 1

    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "ai_layer.main:app",
        "--reload",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]

    return subprocess.call(command, cwd=project_root)


if __name__ == "__main__":
    raise SystemExit(main())
