"""Local Beat Saber map utilities for ALLINAGENT.

The standard-library fallback analyzes 16-bit PCM WAV files. Installing the
optional audio extra enables librosa-based analysis for MP3, FLAC, OGG, and
other supported formats. Generated maps use the broadly compatible v2 format.
All analysis is local; maps must be playtested before sharing.
"""
from __future__ import annotations

import argparse
import array
import json
import math
import os
import re
import shutil
import statistics
import sys
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class AudioAnalysis:
    duration: float
    bpm: float
    event_times: tuple[float, ...]
    method: str
    warnings: tuple[str, ...] = ()


def _steam_roots() -> list[Path]:
    """Find likely Steam roots without launching Steam or changing the PC."""
    roots: list[Path] = []
    for key in ("STEAM_DIR", "STEAM_PATH"):
        if os.environ.get(key):
            roots.append(Path(os.environ[key]).expanduser())
    for key in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
        value = os.environ.get(key)
        if value:
            base = Path(value)
            roots.extend((base / "Steam", base / "Programs" / "Steam"))
    roots.extend((
        Path.home() / ".steam" / "steam",
        Path.home() / ".local" / "share" / "Steam",
        Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam",
    ))
    expanded = list(roots)
    for root in roots:
        try:
            text = (root / "steamapps" / "libraryfolders.vdf").read_text(
                encoding="utf-8", errors="ignore"
            )
        except OSError:
            continue
        for raw in re.findall(r'"path"\s+"([^"]+)"', text):
            expanded.append(Path(raw.replace("\\\\", "\\")))
    unique: list[Path] = []
    seen: set[str] = set()
    for root in expanded:
        key = str(root.resolve(strict=False)).casefold()
        if key not in seen:
            seen.add(key)
            unique.append(root)
    return unique


def detect_beat_saber_installations(extra_paths: Iterable[str | Path] = ()) -> list[Path]:
    """Find recognizable Beat Saber PC install folders in common Steam libraries."""
    candidates = [Path(p).expanduser() for p in extra_paths]
    candidates.extend(root / "steamapps" / "common" / "Beat Saber" for root in _steam_roots())
    found: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        try:
            path = candidate.resolve(strict=True)
        except OSError:
            continue
        if not path.is_dir():
            continue
        recognized = (path / "Beat Saber_Data").is_dir()
        if os.name == "nt":
            recognized = recognized or any(
                (path / name).is_file() for name in ("Beat Saber.exe", "BeatSaber.exe")
            )
        if recognized and str(path).casefold() not in seen:
            seen.add(str(path).casefold())
            found.append(path)
    return found


def _estimate_bpm(times: Iterable[float]) -> float | None:
    ordered = sorted(times)
    intervals = [b - a for a, b in zip(ordered, ordered[1:]) if 0.22 <= b - a <= 1.5]
    if not intervals:
        return None
    bpm = 60.0 / statistics.median(intervals)
    while bpm < 70:
        bpm *= 2
    while bpm > 180:
        bpm /= 2
    return round(bpm, 2) if 60 <= bpm <= 200 else None


def _wav_analysis(path: Path) -> AudioAnalysis:
    """Dependency-free onset detection for uncompressed 16-bit PCM WAV."""
    with wave.open(str(path), "rb") as wav:
        channels, width, rate, count = (
            wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getnframes()
        )
        if wav.getcomptype() != "NONE" or width != 2:
            raise ValueError(
                "Built-in analysis supports uncompressed 16-bit PCM WAV. "
                'For MP3/FLAC/OGG or other encodings, install: python -m pip install -e ".[audio]"'
            )
        if channels < 1 or rate < 1 or count < 1:
            raise ValueError("The WAV file contains no readable audio frames.")
        raw = wav.readframes(count)
    samples = array.array("h")
    samples.frombytes(raw)
    if sys.byteorder != "little":
        samples.byteswap()
    if channels > 1:
        mono = [sum(samples[i:i + channels]) / channels for i in range(0, len(samples), channels)]
    else:
        mono = list(samples)
    duration = count / rate
    hop = max(256, int(rate * 0.025))
    rms: list[float] = []
    times: list[float] = []
    for start in range(0, len(mono), hop):
        chunk = mono[start:start + hop]
        if chunk:
            rms.append(math.sqrt(sum(x * x for x in chunk) / len(chunk)))
            times.append(start / rate)
    if len(rms) < 4:
        raise ValueError("Audio is too short to analyze; provide a longer song.")
    flux = [0.0] + [max(0.0, rms[i] - rms[i - 1]) for i in range(1, len(rms))]
    mean = statistics.fmean(flux)
    threshold = max(statistics.median(flux) + math.sqrt(
        statistics.fmean((x - mean) ** 2 for x in flux)
    ) * 0.8, max(flux) * 0.12)
    peaks: list[float] = []
    for i in range(1, len(flux) - 1):
        if flux[i] >= threshold and flux[i] >= flux[i - 1] and flux[i] > flux[i + 1]:
            if not peaks or times[i] - peaks[-1] >= 0.18:
                peaks.append(times[i])
    bpm = _estimate_bpm(peaks)
    warnings: list[str] = []
    if len(peaks) < 4:
        warnings.append("Few clear transients detected; note timing may need manual adjustment.")
    if bpm is None:
        bpm = 120.0
        warnings.append("Tempo could not be estimated reliably; using 120 BPM. Pass --bpm to set it.")
    return AudioAnalysis(duration, bpm, tuple(peaks), "built-in WAV energy analysis", tuple(warnings))


def analyze_audio(audio_path: str | Path, bpm_override: float | None = None) -> AudioAnalysis:
    """Analyze a local audio file; librosa is optional and never uses a cloud API."""
    path = Path(audio_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Audio file not found: {path}")
    if path.stat().st_size == 0:
        raise ValueError("Audio file is empty.")
    try:
        import librosa  # type: ignore[import-not-found]
        import numpy as np  # type: ignore[import-not-found]

        signal, rate = librosa.load(str(path), sr=None, mono=True)
        if signal.size == 0 or rate <= 0:
            raise ValueError("Audio file contains no decodable samples.")
        tempo, beat_frames = librosa.beat.beat_track(y=signal, sr=rate, units="frames")
        tempo_values = np.asarray(tempo).reshape(-1)
        bpm = float(tempo_values[0]) if tempo_values.size else 0.0
        onset_frames = librosa.onset.onset_detect(y=signal, sr=rate, units="frames")
        beat_times = librosa.frames_to_time(beat_frames, sr=rate)
        onset_times = librosa.frames_to_time(onset_frames, sr=rate)
        combined = sorted(float(t) for t in list(beat_times) + list(onset_times)
                          if 0 <= t < len(signal) / rate)
        events: list[float] = []
        for value in combined:
            if not events or value - events[-1] >= 0.12:
                events.append(value)
        if not 40 <= bpm <= 240:
            bpm = _estimate_bpm(events) or 120.0
        result = AudioAnalysis(len(signal) / rate, round(bpm, 2), tuple(events),
                               "librosa local audio analysis")
    except ImportError:
        if path.suffix.lower() != ".wav":
            raise ValueError(
                "This audio format needs optional local audio support. "
                'Install it with: python -m pip install -e ".[audio]"'
            )
        result = _wav_analysis(path)
    if bpm_override is not None:
        if not 40 <= bpm_override <= 240:
            raise ValueError("BPM override must be between 40 and 240.")
        result = AudioAnalysis(result.duration, float(bpm_override), result.event_times,
                               result.method, result.warnings)
    return result


def _frange(start: float, stop: float, step: float) -> Iterable[float]:
    value = start
    while value <= stop:
        yield value
        value += step


def _notes_for(analysis: AudioAnalysis, difficulty: str) -> list[dict[str, Any]]:
    stride = {"Easy": 3, "Normal": 2, "Hard": 1, "Expert": 1, "ExpertPlus": 1}[difficulty]
    events = list(analysis.event_times)
    if len(events) < 4:
        events = list(_frange(0.5, analysis.duration - 0.15, 60.0 / analysis.bpm))
    if stride > 1:
        events = events[::stride]
    notes: list[dict[str, Any]] = []
    last_beat = -1.0
    last_lane = -1
    for index, seconds in enumerate(events):
        beat = round(seconds * analysis.bpm / 60.0 * 4) / 4
        if beat < 0 or beat >= analysis.duration * analysis.bpm / 60.0:
            continue
        if beat - last_beat < 0.24:
            continue
        lane = (index * 2 + index // 3) % 4
        if lane == last_lane:
            lane = (lane + 1) % 4
        notes.append({
            "_time": beat,
            "_lineIndex": lane,
            "_lineLayer": (index // 4) % 2,
            "_type": index % 2,
            "_cutDirection": index % 4,
        })
        last_beat, last_lane = beat, lane
    return notes


def create_map(
    audio_path: str | Path,
    output_dir: str | Path,
    title: str | None = None,
    difficulty: str = "ExpertPlus",
    bpm_override: float | None = None,
) -> Path:
    """Create a new custom level folder without overwriting existing content."""
    ranks = {"Easy": 1, "Normal": 3, "Hard": 5, "Expert": 7, "ExpertPlus": 9}
    if difficulty not in ranks:
        raise ValueError(f"Unsupported difficulty: {difficulty}")
    audio = Path(audio_path).expanduser().resolve()
    output = Path(output_dir).expanduser().resolve()
    if not audio.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio}")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise FileExistsError(f"Output already exists and is not empty: {output}")
    analysis = analyze_audio(audio, bpm_override)
    output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(audio, output / audio.name)
    song_title = (title or audio.stem).strip() or audio.stem
    info = {
        "_version": "2.1.0",
        "_songName": song_title,
        "_songSubName": "",
        "_songAuthorName": "Unknown",
        "_levelAuthorName": "ALLINAGENT",
        "_beatsPerMinute": analysis.bpm,
        "_songTimeOffset": 0,
        "_shuffle": 0,
        "_shufflePeriod": 0,
        "_previewStartTime": 0,
        "_previewDuration": min(10, analysis.duration),
        "_songFilename": audio.name,
        "_coverImageFilename": "",
        "_environmentName": "DefaultEnvironment",
        "_allDirectionsEnvironmentName": "GlassDesertEnvironment",
        "_difficultyBeatmapSets": [{
            "_beatmapCharacteristicName": "Standard",
            "_difficultyBeatmaps": [{
                "_difficulty": difficulty,
                "_difficultyRank": ranks[difficulty],
                "_beatmapFilename": f"{difficulty}.dat",
                "_noteJumpMovementSpeed": 12 if difficulty in ("Easy", "Normal") else 16,
                "_noteJumpStartBeatOffset": 0,
                "_customData": {},
            }],
        }],
    }
    beatmap = {
        "_version": "2.6.0",
        "_notes": _notes_for(analysis, difficulty),
        "_obstacles": [],
        "_events": [],
        "_waypoints": [],
        "_customData": {},
    }
    (output / "Info.dat").write_text(json.dumps(info, indent=2), encoding="utf-8")
    (output / f"{difficulty}.dat").write_text(json.dumps(beatmap, indent=2), encoding="utf-8")
    errors = validate_level(output)
    if errors:
        raise ValueError("Generated map failed validation: " + "; ".join(errors))
    return output


def validate_level(level_dir: str | Path) -> list[str]:
    """Check core metadata, audio reference, note fields, and playfield bounds."""
    folder = Path(level_dir).expanduser().resolve()
    info_path = folder / "Info.dat"
    if not info_path.is_file():
        return [f"Missing Info.dat in {folder}"]
    try:
        info = json.loads(info_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"Info.dat is not valid JSON: {exc}"]
    sets = info.get("_difficultyBeatmapSets")
    if not isinstance(sets, list) or not sets:
        return ["Info.dat must contain a non-empty _difficultyBeatmapSets array."]
    errors: list[str] = []
    audio_name = info.get("_songFilename")
    if not isinstance(audio_name, str) or not audio_name or not (folder / audio_name).is_file():
        errors.append("The audio file named by _songFilename is missing.")
    for beatmap_set in sets:
        for difficulty in beatmap_set.get("_difficultyBeatmaps", []):
            filename = difficulty.get("_beatmapFilename")
            if not isinstance(filename, str) or not filename:
                errors.append("A difficulty entry has no _beatmapFilename.")
                continue
            map_path = folder / filename
            if not map_path.is_file():
                errors.append(f"Missing beatmap file: {filename}")
                continue
            try:
                data = json.loads(map_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"{filename} is not valid JSON: {exc}")
                continue
            notes = data.get("_notes")
            if not isinstance(notes, list):
                errors.append(f"{filename} must contain an _notes array.")
                continue
            for index, note in enumerate(notes):
                if not isinstance(note, dict):
                    errors.append(f"{filename} note {index} is not an object.")
                    continue
                try:
                    beat, lane, row = float(note["_time"]), int(note["_lineIndex"]), int(note["_lineLayer"])
                    hand, direction = int(note["_type"]), int(note["_cutDirection"])
                except (KeyError, TypeError, ValueError):
                    errors.append(f"{filename} note {index} is missing valid note fields.")
                    continue
                if beat < 0 or not math.isfinite(beat):
                    errors.append(f"{filename} note {index} has invalid beat time.")
                if lane not in range(4) or row not in range(3):
                    errors.append(f"{filename} note {index} is outside the playfield.")
                if hand not in (0, 1) or direction not in range(9):
                    errors.append(f"{filename} note {index} has invalid hand or cut direction.")
    return errors


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="allinagent-beat-saber",
        description="Create and validate local Beat Saber custom maps.")
    sub = parser.add_subparsers(dest="command", required=True)
    detect = sub.add_parser("detect", help="Detect a PC Beat Saber installation")
    detect.add_argument("--path", action="append", default=[], help="Check an additional install folder")
    create = sub.add_parser("create", help="Analyze audio and generate a custom map")
    create.add_argument("audio", help="Local audio path (WAV built in; other formats need [audio])")
    create.add_argument("--output", required=True, help="New output folder; non-empty folders are never overwritten")
    create.add_argument("--title", help="Song title; defaults to the filename")
    create.add_argument("--difficulty", choices=["Easy", "Normal", "Hard", "Expert", "ExpertPlus"], default="ExpertPlus")
    create.add_argument("--bpm", type=float, help="Override detected tempo (40-240 BPM)")
    create.add_argument("--allow-uninstalled", action="store_true", help="Export even if Beat Saber is not detected on this PC")
    validate = sub.add_parser("validate", help="Validate an exported level folder")
    validate.add_argument("level_folder", help="Folder containing Info.dat and a beatmap")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "detect":
            installs = detect_beat_saber_installations(args.path)
            if not installs:
                print("Beat Saber was not detected on this PC.")
                return 1
            print("Beat Saber installation(s) detected:")
            for install in installs:
                print(f"  {install}")
            return 0
        if args.command == "create":
            installs = detect_beat_saber_installations()
            if not installs and not args.allow_uninstalled:
                print("Beat Saber was not detected on this PC; map creation stopped.")
                print("Install the PC version, or use --allow-uninstalled to export a map anyway.")
                return 2
            result = create_map(args.audio, args.output, args.title, args.difficulty, args.bpm)
            analysis = analyze_audio(args.audio, args.bpm)
            beatmap = json.loads((result / f"{args.difficulty}.dat").read_text(encoding="utf-8"))
            print(f"Created map folder: {result}")
            print(f"Tempo: {analysis.bpm:.2f} BPM | Duration: {analysis.duration:.1f}s")
            print(f"Audio analysis: {analysis.method} | Notes: {len(beatmap['_notes'])}")
            for warning in analysis.warnings:
                print("WARNING: " + warning)
            if installs:
                print(f"Detected Beat Saber at: {installs[0]}")
            print("Playtest in Beat Saber; generated patterns are a starting point, not a guarantee of quality.")
            return 0
        if args.command == "validate":
            errors = validate_level(args.level_folder)
            if errors:
                print("Map validation failed:")
                for error in errors:
                    print(f"  - {error}")
                return 1
            print("Map structure looks valid. Playtesting is still required.")
            return 0
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
