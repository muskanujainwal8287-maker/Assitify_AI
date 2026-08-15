from __future__ import annotations

import argparse
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent

SERVICES: dict[str, dict[str, Any]] = {
    "ai": {
        "kind": "uvicorn",
        "app": "ai_layer.main:app",
        "port": "8000",
        "required_dir": "ai_layer",
        "url": "http://127.0.0.1:8000",
    },
    "backend": {
        "kind": "uvicorn",
        "app": "backend.app.main:app",
        "port": "8001",
        "required_dir": "backend",
        "url": "http://127.0.0.1:8001",
    },
    "frontend": {
        "kind": "npm",
        "port": "5173",
        "required_dir": "frontend",
        "script": "dev",
        "url": "http://localhost:5173",
    },
}


def _uvicorn_command(app: str, port: str, reload_dir: str) -> list[str]:
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


def _resolve_npm() -> str | None:
    return shutil.which("npm") or shutil.which("npm.cmd")


def _ensure_frontend_ready(project_root: Path) -> int:
    frontend_dir = project_root / "frontend"
    package_json = frontend_dir / "package.json"
    if not package_json.exists():
        print("Error: frontend/package.json not found.", file=sys.stderr)
        return 1

    npm = _resolve_npm()
    if not npm:
        print(
            "Error: npm not found. Install Node.js 20+ from https://nodejs.org/ "
            "and reopen the terminal.",
            file=sys.stderr,
        )
        return 1

    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        print("frontend/node_modules missing — running npm install...")
        code = subprocess.call([npm, "install"], cwd=frontend_dir)
        if code != 0:
            print("Error: npm install failed.", file=sys.stderr)
            return code

    return 0


def _build_service_command(name: str, project_root: Path) -> tuple[list[str], Path]:
    config = SERVICES[name]
    if config["kind"] == "uvicorn":
        return (
            _uvicorn_command(config["app"], config["port"], config["required_dir"]),
            project_root,
        )

    npm = _resolve_npm()
    if not npm:
        raise RuntimeError("npm not found")
    return [npm, "run", config["script"]], project_root / config["required_dir"]


def _popen_kwargs() -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    return kwargs


def _stop_process(name: str, process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    print(f"Stopping {name}...")
    if sys.platform == "win32":
        # Kill npm/vite child processes as a tree on Windows.
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def _validate_service(name: str, project_root: Path) -> int:
    config = SERVICES[name]
    required = project_root / config["required_dir"]
    if not required.exists():
        print(f"Error: {config['required_dir']} directory not found.", file=sys.stderr)
        return 1
    if config["kind"] == "npm":
        return _ensure_frontend_ready(project_root)
    return 0


def _start_one(name: str, project_root: Path) -> int:
    code = _validate_service(name, project_root)
    if code != 0:
        return code

    config = SERVICES[name]
    command, cwd = _build_service_command(name, project_root)
    print(f"Starting {name} on {config['url']}")
    return subprocess.call(command, cwd=cwd)


def _start_many(names: list[str], project_root: Path) -> int:
    for name in names:
        code = _validate_service(name, project_root)
        if code != 0:
            return code

    processes: list[tuple[str, subprocess.Popen[str]]] = []
    for name in names:
        config = SERVICES[name]
        command, cwd = _build_service_command(name, project_root)
        print(f"Starting {name} on {config['url']}")
        process = subprocess.Popen(command, cwd=cwd, **_popen_kwargs())
        processes.append((name, process))

    print()
    print("Assitify is starting:")
    for name in names:
        print(f"  - {name}: {SERVICES[name]['url']}")
    if "frontend" in names:
        print()
        print("Open the app: http://localhost:5173")
    print("Press Ctrl+C to stop.")
    print()

    def _shutdown(*_args: object) -> None:
        for name, process in processes:
            _stop_process(name, process)

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
    parser = argparse.ArgumentParser(
        description="Start Assitify services (AI, backend, and Vite frontend).",
    )
    parser.add_argument(
        "service",
        nargs="?",
        default="all",
        choices=["all", "ai", "backend", "frontend"],
        help="Service to start (default: all)",
    )
    args = parser.parse_args()
    project_root = PROJECT_ROOT

    if args.service == "all":
        return _start_many(["ai", "backend", "frontend"], project_root)
    return _start_one(args.service, project_root)


if __name__ == "__main__":
    raise SystemExit(main())
