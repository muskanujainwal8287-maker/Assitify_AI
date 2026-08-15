from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import start


def test_uvicorn_command_shape() -> None:
    command = start._uvicorn_command("backend.app.main:app", "8001", "backend")
    assert command[:4] == [sys.executable, "-m", "uvicorn", "backend.app.main:app"]
    assert "--port" in command
    assert command[command.index("--port") + 1] == "8001"
    assert "--reload-dir" in command
    assert command[command.index("--reload-dir") + 1] == "backend"
    assert "--host" in command
    assert command[command.index("--host") + 1] == "127.0.0.1"


def test_services_include_frontend_vite() -> None:
    assert set(start.SERVICES) == {"ai", "backend", "frontend"}
    assert start.SERVICES["frontend"]["kind"] == "npm"
    assert start.SERVICES["frontend"]["script"] == "dev"
    assert start.SERVICES["frontend"]["port"] == "5173"
    assert start.SERVICES["ai"]["kind"] == "uvicorn"
    assert start.SERVICES["backend"]["kind"] == "uvicorn"


def test_build_service_command_uvicorn(tmp_path: Path) -> None:
    command, cwd = start._build_service_command("backend", tmp_path)
    assert cwd == tmp_path
    assert "uvicorn" in command
    assert "backend.app.main:app" in command


def test_build_service_command_frontend(tmp_path: Path) -> None:
    with patch.object(start, "_resolve_npm", return_value="npm.cmd"):
        command, cwd = start._build_service_command("frontend", tmp_path)
    assert command == ["npm.cmd", "run", "dev"]
    assert cwd == tmp_path / "frontend"


def test_build_service_command_frontend_requires_npm(tmp_path: Path) -> None:
    with patch.object(start, "_resolve_npm", return_value=None):
        with pytest.raises(RuntimeError, match="npm not found"):
            start._build_service_command("frontend", tmp_path)


def test_ensure_frontend_ready_missing_package_json(tmp_path: Path) -> None:
    (tmp_path / "frontend").mkdir()
    assert start._ensure_frontend_ready(tmp_path) == 1


def test_ensure_frontend_ready_missing_npm(tmp_path: Path) -> None:
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "package.json").write_text("{}", encoding="utf-8")
    with patch.object(start, "_resolve_npm", return_value=None):
        assert start._ensure_frontend_ready(tmp_path) == 1


def test_ensure_frontend_ready_runs_npm_install(tmp_path: Path) -> None:
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "package.json").write_text("{}", encoding="utf-8")
    with (
        patch.object(start, "_resolve_npm", return_value="npm"),
        patch.object(start.subprocess, "call", return_value=0) as call_mock,
    ):
        assert start._ensure_frontend_ready(tmp_path) == 0
    call_mock.assert_called_once_with(["npm", "install"], cwd=frontend)


def test_ensure_frontend_ready_npm_install_failure(tmp_path: Path) -> None:
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "package.json").write_text("{}", encoding="utf-8")
    with (
        patch.object(start, "_resolve_npm", return_value="npm"),
        patch.object(start.subprocess, "call", return_value=7),
    ):
        assert start._ensure_frontend_ready(tmp_path) == 7


def test_ensure_frontend_ready_skips_install_when_node_modules_exist(tmp_path: Path) -> None:
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "package.json").write_text("{}", encoding="utf-8")
    (frontend / "node_modules").mkdir()
    with (
        patch.object(start, "_resolve_npm", return_value="npm"),
        patch.object(start.subprocess, "call") as call_mock,
    ):
        assert start._ensure_frontend_ready(tmp_path) == 0
    call_mock.assert_not_called()


def test_validate_service_missing_directory(tmp_path: Path) -> None:
    assert start._validate_service("ai", tmp_path) == 1


def test_validate_service_uvicorn_ok(tmp_path: Path) -> None:
    (tmp_path / "ai_layer").mkdir()
    assert start._validate_service("ai", tmp_path) == 0


def test_validate_service_frontend_delegates(tmp_path: Path) -> None:
    (tmp_path / "frontend").mkdir()
    with patch.object(start, "_ensure_frontend_ready", return_value=0) as ensure:
        assert start._validate_service("frontend", tmp_path) == 0
    ensure.assert_called_once_with(tmp_path)


def test_start_one_returns_validation_error(tmp_path: Path) -> None:
    with patch.object(start, "_validate_service", return_value=3):
        assert start._start_one("backend", tmp_path) == 3


def test_start_one_runs_subprocess(tmp_path: Path) -> None:
    with (
        patch.object(start, "_validate_service", return_value=0),
        patch.object(
            start,
            "_build_service_command",
            return_value=(["echo", "ok"], tmp_path),
        ),
        patch.object(start.subprocess, "call", return_value=0) as call_mock,
    ):
        assert start._start_one("ai", tmp_path) == 0
    call_mock.assert_called_once_with(["echo", "ok"], cwd=tmp_path)


def test_start_many_stops_on_validation_failure(tmp_path: Path) -> None:
    with (
        patch.object(start, "_validate_service", side_effect=[0, 2]),
        patch.object(start.subprocess, "Popen") as popen_mock,
    ):
        assert start._start_many(["ai", "backend"], tmp_path) == 2
    popen_mock.assert_not_called()


def test_start_many_shuts_down_when_child_exits(tmp_path: Path) -> None:
    fake_process = MagicMock()
    fake_process.poll.side_effect = [None, 9]

    with (
        patch.object(start, "_validate_service", return_value=0),
        patch.object(
            start,
            "_build_service_command",
            return_value=(["echo", "ok"], tmp_path),
        ),
        patch.object(start.subprocess, "Popen", return_value=fake_process),
        patch.object(start, "_popen_kwargs", return_value={}),
        patch.object(start, "_stop_process") as stop_mock,
        patch.object(start.time, "sleep"),
        patch.object(start.signal, "signal"),
    ):
        assert start._start_many(["ai"], tmp_path) == 9

    stop_mock.assert_called()


def test_start_many_keyboard_interrupt(tmp_path: Path) -> None:
    fake_process = MagicMock()
    fake_process.poll.return_value = None

    with (
        patch.object(start, "_validate_service", return_value=0),
        patch.object(
            start,
            "_build_service_command",
            return_value=(["echo", "ok"], tmp_path),
        ),
        patch.object(start.subprocess, "Popen", return_value=fake_process),
        patch.object(start, "_popen_kwargs", return_value={}),
        patch.object(start, "_stop_process") as stop_mock,
        patch.object(start.time, "sleep", side_effect=KeyboardInterrupt),
        patch.object(start.signal, "signal"),
    ):
        assert start._start_many(["frontend"], tmp_path) == 0

    stop_mock.assert_called_once()


def test_stop_process_skips_already_exited() -> None:
    process = MagicMock()
    process.poll.return_value = 0
    with patch.object(start.subprocess, "run") as run_mock:
        start._stop_process("ai", process)
    run_mock.assert_not_called()
    process.terminate.assert_not_called()


def test_stop_process_windows_uses_taskkill() -> None:
    process = MagicMock()
    process.poll.return_value = None
    process.pid = 4242
    with (
        patch.object(start.sys, "platform", "win32"),
        patch.object(start.subprocess, "run") as run_mock,
    ):
        start._stop_process("frontend", process)
    run_mock.assert_called_once()
    args = run_mock.call_args.args[0]
    assert args == ["taskkill", "/F", "/T", "/PID", "4242"]
    process.terminate.assert_not_called()


def test_stop_process_unix_terminates() -> None:
    process = MagicMock()
    process.poll.return_value = None
    with (
        patch.object(start.sys, "platform", "linux"),
        patch.object(start.subprocess, "run") as run_mock,
    ):
        start._stop_process("backend", process)
    run_mock.assert_not_called()
    process.terminate.assert_called_once()
    process.wait.assert_called_once_with(timeout=5)


def test_stop_process_unix_kills_on_timeout() -> None:
    process = MagicMock()
    process.poll.return_value = None
    process.wait.side_effect = subprocess.TimeoutExpired(cmd="x", timeout=5)
    with patch.object(start.sys, "platform", "linux"):
        start._stop_process("backend", process)
    process.kill.assert_called_once()


def test_popen_kwargs_windows() -> None:
    with patch.object(start.sys, "platform", "win32"):
        kwargs = start._popen_kwargs()
    assert kwargs["creationflags"] == subprocess.CREATE_NEW_PROCESS_GROUP


def test_popen_kwargs_non_windows() -> None:
    with patch.object(start.sys, "platform", "linux"):
        assert start._popen_kwargs() == {}


def test_main_all_starts_three_services() -> None:
    with (
        patch.object(sys, "argv", ["start.py"]),
        patch.object(start, "_start_many", return_value=0) as many_mock,
    ):
        assert start.main() == 0
    many_mock.assert_called_once_with(
        ["ai", "backend", "frontend"],
        start.PROJECT_ROOT,
    )


def test_main_single_service() -> None:
    with (
        patch.object(sys, "argv", ["start.py", "frontend"]),
        patch.object(start, "_start_one", return_value=0) as one_mock,
    ):
        assert start.main() == 0
    one_mock.assert_called_once_with("frontend", start.PROJECT_ROOT)


def test_resolve_npm_prefers_npm_then_npm_cmd() -> None:
    with patch.object(start.shutil, "which", side_effect=lambda name: "C:/npm" if name == "npm" else None):
        assert start._resolve_npm() == "C:/npm"

    with patch.object(
        start.shutil,
        "which",
        side_effect=lambda name: "C:/npm.cmd" if name == "npm.cmd" else None,
    ):
        assert start._resolve_npm() == "C:/npm.cmd"

    with patch.object(start.shutil, "which", return_value=None):
        assert start._resolve_npm() is None
