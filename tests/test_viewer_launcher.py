"""Launcher is opt-in, local-file-only and does not edit a real browser profile."""
import importlib.util
from pathlib import Path
import subprocess

import pytest


@pytest.fixture
def launcher():
    source = Path(__file__).resolve().parents[1]/"examples/open_interactive_viewer.py"
    spec = importlib.util.spec_from_file_location("viewer_launcher",source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_normal_open_has_no_graphics_flags_and_does_not_spawn_a_process(launcher,tmp_path,monkeypatch):
    html = tmp_path/"my viewer.html"; html.write_text("<html></html>",encoding="utf-8")
    opened = []
    monkeypatch.setattr(launcher.webbrowser,"open_new_tab",lambda url: opened.append(url) or True)
    monkeypatch.setattr(launcher.subprocess,"run",lambda *a,**k: pytest.fail("Normal mode must not set browser flags"))
    assert launcher.main([str(html)]) == 0
    assert opened == [html.as_uri()]


def test_software_mode_is_explicit_isolated_and_keeps_the_sandbox(launcher,tmp_path,monkeypatch,capsys):
    html = tmp_path/"viewer.html"; html.write_text("<html></html>",encoding="utf-8")
    executable = tmp_path/"chrome"; executable.touch()
    monkeypatch.setattr(launcher,"_chrome_executable",lambda: str(executable))
    commands = []

    def run(command,check):
        assert check is False
        commands.append(command)
        profile = Path(next(arg.split("=",1)[1] for arg in command if arg.startswith("--user-data-dir=")))
        assert profile.is_dir() and profile.name.startswith("wrf-viewer-chrome-")
        assert "--no-sandbox" not in command and "--disable-web-security" not in command
        return subprocess.CompletedProcess(command,0)

    monkeypatch.setattr(launcher.subprocess,"run",run)
    assert launcher.main([str(html),"--software-webgl"]) == 0
    command = commands[0]
    assert "--enable-unsafe-swiftshader" in command and "--use-angle=swiftshader" in command
    assert command[-1] == html.as_uri()
    profile = Path(next(arg.split("=",1)[1] for arg in command if arg.startswith("--user-data-dir=")))
    assert not profile.exists()
    assert "trusted local files only" in capsys.readouterr().out


@pytest.mark.parametrize("arguments", [["missing.html"],["https://example.invalid/viewer.html"],["--chrome","chrome"]])
def test_invalid_input_fails_without_opening_anything(launcher,arguments,monkeypatch):
    monkeypatch.setattr(launcher.webbrowser,"open_new_tab",lambda *a: pytest.fail("Must not launch"))
    monkeypatch.setattr(launcher.subprocess,"run",lambda *a,**k: pytest.fail("Must not launch"))
    with pytest.raises(SystemExit):
        launcher.main(arguments)
