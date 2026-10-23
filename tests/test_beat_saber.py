"""Tests for the standalone Beat Saber mapping utility."""
from __future__ import annotations

import json
import wave
from array import array
from pathlib import Path

import pytest

from allinagent import beat_saber


def _write_test_wav(path: Path) -> Path:
    rate = 8000
    samples = array("h")
    for i in range(rate * 3):
        phase = i % 4000
        samples.append(12000 if phase < 250 else 0)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(samples.tobytes())
    return path


def test_detection_accepts_explicit_game_folder(tmp_path: Path):
    install = tmp_path / "Beat Saber"
    (install / "Beat Saber_Data").mkdir(parents=True)
    assert beat_saber.detect_beat_saber_installations([install]) == [install.resolve()]


def test_detection_rejects_unrecognizable_folder(tmp_path: Path):
    folder = tmp_path / "not-a-game"
    folder.mkdir()
    assert beat_saber.detect_beat_saber_installations([folder]) == []


def test_create_map_writes_metadata_audio_and_notes(tmp_path: Path, monkeypatch):
    audio = _write_test_wav(tmp_path / "test-song.wav")
    analysis = beat_saber.AudioAnalysis(
        duration=3.0, bpm=120.0, event_times=(0.5, 1.0, 1.5, 2.0),
        method="test", warnings=(),
    )
    monkeypatch.setattr(beat_saber, "analyze_audio", lambda *_args, **_kwargs: analysis)
    output = beat_saber.create_map(audio, tmp_path / "created-map", title="Test Song")
    info = json.loads((output / "Info.dat").read_text(encoding="utf-8"))
    beatmap = json.loads((output / "ExpertPlus.dat").read_text(encoding="utf-8"))
    assert info["_songName"] == "Test Song"
    assert info["_beatsPerMinute"] == 120.0
    assert (output / "test-song.wav").is_file()
    assert beatmap["_notes"]
    assert beat_saber.validate_level(output) == []


def test_create_map_refuses_to_overwrite_nonempty_folder(tmp_path: Path):
    audio = _write_test_wav(tmp_path / "song.wav")
    output = tmp_path / "existing"
    output.mkdir()
    marker = output / "keep.txt"
    marker.write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError):
        beat_saber.create_map(audio, output)
    assert marker.read_text(encoding="utf-8") == "keep"


def test_validator_reports_missing_info(tmp_path: Path):
    assert "Missing Info.dat" in beat_saber.validate_level(tmp_path)[0]


def test_create_command_requires_detected_game_unless_overridden(tmp_path: Path, monkeypatch, capsys):
    audio = _write_test_wav(tmp_path / "song.wav")
    monkeypatch.setattr(beat_saber, "detect_beat_saber_installations", lambda *_args: [])
    result = beat_saber.main(["create", str(audio), "--output", str(tmp_path / "out")])
    assert result == 2
    assert "not detected" in capsys.readouterr().out.lower()
    assert not (tmp_path / "out").exists()
