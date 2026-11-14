"""Tests for choosing the save folder. The native picker is mocked."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app as ytapp  # noqa: E402


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setitem(ytapp.state, "folder", tmp_path / "default")
    monkeypatch.setattr(ytapp, "SETTINGS_FILE", tmp_path / "settings" / "settings.json")
    return ytapp.app.test_client()


def test_choose_folder_sets_new_folder(client, monkeypatch, tmp_path):
    monkeypatch.setattr(ytapp, "pick_folder", lambda start: str(tmp_path))
    res = client.post("/api/folder", json={})
    assert res.status_code == 200
    assert res.json["folder"] == str(tmp_path)
    assert ytapp.state["folder"] == tmp_path


def test_cancel_keeps_current_folder(client, monkeypatch):
    before = ytapp.state["folder"]
    monkeypatch.setattr(ytapp, "pick_folder", lambda start: None)
    res = client.post("/api/folder", json={})
    assert res.status_code == 200
    assert res.json["folder"] == str(before)
    assert ytapp.state["folder"] == before


def test_rejects_missing_folder(client, monkeypatch, tmp_path):
    before = ytapp.state["folder"]
    monkeypatch.setattr(ytapp, "pick_folder", lambda start: str(tmp_path / "nope"))
    res = client.post("/api/folder", json={})
    assert res.status_code == 400
    assert ytapp.state["folder"] == before


def test_picker_failure_returns_error(client, monkeypatch):
    def boom(start):
        raise RuntimeError("Choosing a folder isn't supported here.")
    monkeypatch.setattr(ytapp, "pick_folder", boom)
    res = client.post("/api/folder", json={})
    assert res.status_code == 500
    assert "supported" in res.json["error"]


def test_download_uses_folder_at_start(client, monkeypatch, tmp_path):
    started = {}

    class FakeThread:
        def __init__(self, target, args, daemon):
            started["args"] = args
        def start(self):
            pass

    monkeypatch.setattr(ytapp.threading, "Thread", FakeThread)
    monkeypatch.setitem(ytapp.state, "folder", tmp_path)
    res = client.post("/api/download", json={"url": "https://example.com/v", "preset": "mp3"})
    assert res.status_code == 200
    assert started["args"][-1] == tmp_path  # job keeps this folder even if the user changes it later


def test_chosen_folder_is_remembered(client, monkeypatch, tmp_path):
    chosen = tmp_path / "videos"
    chosen.mkdir()
    monkeypatch.setattr(ytapp, "pick_folder", lambda start: str(chosen))
    assert client.post("/api/folder", json={}).status_code == 200
    assert ytapp.load_folder() == chosen  # what the next launch would use


def test_load_without_settings_uses_default(client):
    assert ytapp.load_folder() == ytapp.DOWNLOAD_DIR


def test_load_falls_back_when_saved_folder_is_gone(client, tmp_path):
    ytapp.save_folder(tmp_path / "unplugged-drive")
    assert ytapp.load_folder() == ytapp.DOWNLOAD_DIR


def test_load_falls_back_on_corrupt_settings(client):
    ytapp.SETTINGS_FILE.parent.mkdir(parents=True)
    ytapp.SETTINGS_FILE.write_text("{not json")
    assert ytapp.load_folder() == ytapp.DOWNLOAD_DIR


def test_save_failure_keeps_old_folder(client, monkeypatch, tmp_path):
    before = ytapp.state["folder"]
    monkeypatch.setattr(ytapp, "pick_folder", lambda start: str(tmp_path))
    def fail(folder):
        raise OSError("disk full")
    monkeypatch.setattr(ytapp, "save_folder", fail)
    res = client.post("/api/folder", json={})
    assert res.status_code == 500
    assert "disk full" in res.json["error"]
    assert ytapp.state["folder"] == before
