# ALLINAGENT Beat Saber Mapper

This is an early, local-only mapping utility. It creates a new Beat Saber custom
level folder from a local audio file and validates the folder's basic structure.
Generated note patterns are a starting point and must be playtested; this version
does not promise professional-quality choreography or automatically upgrade an
existing map yet.

## Install

From the ALLINAGENT repository root, in PowerShell:

    python -m pip install -e .

For MP3, FLAC, OGG, and other formats supported by librosa, install the optional
audio dependencies. All processing remains local:

    python -m pip install -e ".[audio]"

Without the optional dependencies, built-in analysis supports uncompressed
16-bit PCM WAV files.

## Commands

Detect a PC installation in common Steam libraries:

    allinagent-beat-saber detect

Generate a map from audio (requires the PC version to be detected by default):

    allinagent-beat-saber create "C:\Music\song.wav" --output ".\BeatSaberMaps\MySong" --difficulty ExpertPlus

If you only want to export files on a PC without the game installed:

    allinagent-beat-saber create "C:\Music\song.wav" --output ".\BeatSaberMaps\MySong" --allow-uninstalled

Set the BPM manually if the estimate is inaccurate:

    allinagent-beat-saber create ".\song.wav" --output ".\MySongMap" --bpm 128 --difficulty Expert

Validate the exported folder:

    allinagent-beat-saber validate ".\MySongMap"

The tool does not install maps into the game automatically and never overwrites
a non-empty output folder. It writes a v2-format Info.dat and difficulty file.
Copy/install the exported folder using a custom-level workflow appropriate to
your Beat Saber PC/Quest setup, then test it in-game.

## Current scope

- PC Steam installation detection in common library locations, plus explicit
  paths through the detect --path option.
- Local onset/tempo analysis using librosa when installed, or simple WAV energy
  analysis with the standard library.
- One generated Standard difficulty per export.
- Basic JSON, note-field, and playfield validation.
- No cloud inference, external AI API, or API key.
- Existing-map difficulty upgrades and automatic game-folder installation are
  not implemented in this first version.
