from __future__ import annotations

import argparse
import signal
import subprocess
import sys
import time
from pathlib import Path

SERVICES = {
    "ai": {
        "app": "ai_layer.main:app",
        "port": "8000",
        "required_dir": "ai_layer",
    },
    "backend": {
        "app": "backend.app.main:app",
        "port": "8001",
        "required_dir": "backend",
    },
}


def _build_command(app: str, port: str, reload_dir: str) -> list[str]:
    return [
        sys.executable,
        "-m",
        "uvicorn",
        app,
        "--reload",
        "--reload-dir",
        reload_dir,
        "--host",
        "127.0.0.1",
        "--port",
        port,
    ]


def _start_one(name: str, project_root: Path) -> int:
    config = SERVICES[name]
    required = project_root / config["required_dir"]
    if not required.exists():
        print(f"Error: {config['required_dir']} directory not found.", file=sys.stderr)
        return 1

    command = _build_command(config["app"], config["port"], config["required_dir"])
    print(f"Starting {name} on http://127.0.0.1:{config['port']}")
    return subprocess.call(command, cwd=project_root)


def _start_all(project_root: Path) -> int:
    processes: list[tuple[str, subprocess.Popen[str]]] = []

    for name, config in SERVICES.items():
        required = project_root / config["required_dir"]
        if not required.exists():
            print(f"Error: {config['required_dir']} directory not found.", file=sys.stderr)
            return 1

        command = _build_command(config["app"], config["port"], config["required_dir"])
        print(f"Starting {name} on http://127.0.0.1:{config['port']}")
        process = subprocess.Popen(command, cwd=project_root)
        processes.append((name, process))

    def _shutdown(*_args: object) -> None:
        for name, process in processes:
            if process.poll() is None:
                print(f"Stopping {name}...")
                process.terminate()
        for _, process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

    signal.signal(signal.SIGINT, _shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _shutdown)

    try:
        while True:
            for name, process in processes:
                code = process.poll()
                if code is not None:
                    print(f"{name} exited with code {code}", file=sys.stderr)
                    _shutdown()
                    return code or 1
            time.sleep(0.5)
    except KeyboardInterrupt:
        _shutdown()
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Start Assitify services.")
    parser.add_argument(
        "service",
        nargs="?",
        default="all",
        choices=["all", "ai", "backend"],
        help="Service to start (default: all)",
    )
    args = parser.parse_args()
    project_root = Path(__file__).resolve().parent

    if args.service == "all":
        return _start_all(project_root)
    return _start_one(args.service, project_root)


if __name__ == "__main__":
    raise SystemExit(main())
