# Atmos-Encoder

**Atmos-Encoder** is a Python tool that converts Dolby TrueHD audio into Dolby Digital Plus (E-AC3) format while preserving Dolby Atmos metadata when available.

---

## ⚠️ Important Notice

> This project uses test files adapted from the **truehdd** project. Source material has been modified to enable conversion to Dolby Digital Plus Atmos format.

---

## Overview

The encoder automatically detects whether the input `.thd` file contains Atmos audio and produces:

* Dolby Digital Plus 5.1 with Atmos (`_atmos_5_1.mp4`)
* Dolby Digital Plus 7.1 with Atmos (`_atmos_7_1.mp4`)
* Or both, depending on the chosen mode.

If no Atmos is detected, it creates a standard 5.1 DDP file. For non-Atmos streams, **FFmpeg/FFprobe are used to resample the decoded WAV to 48 kHz PCM** for DEE compatibility.

---

## Features

* Automatic Atmos detection using [`truehdd`](https://github.com/truehdd/truehdd)
* Converts TrueHD Atmos to DDP Atmos (5.1, 7.1, or both)
* Configurable bitrates for Atmos 5.1, Atmos 7.1, and fallback DDP
* Warp mode support (`normal`, `warping`, `prologiciix`, `loro`)
* Optional bed conform for Atmos streams (enabled by default)
* Cross-platform support (Windows/Linux/macOS)
* Live progress bars for both DEE and FFmpeg processing
* Automatic file organization and cleanup in `ddp_encode` output folder
* FFmpeg/FFprobe required only for non-Atmos streams
* Recommended DEE version: **5.2.1**

---

## Requirements

* `truehdd.exe` / `truehdd` (placed in `binaries/`)
* `dee.exe` / `dee` and other Dolby Encoding Engine binaries (**not included** due to licensing)
* `ffmpeg` / `ffprobe` (only required for non-Atmos streams)
* Python 3.7+
* Python module `colorama` (`pip install colorama`)

---

## Usage

Run the encoder with:

```bash
python main.py -i input_file.thd -ba 1024 -b7 1536 -am both -w normal -bc
```

### Main Parameters

| Parameter                        | Description                                   | Default | Allowed Values                                                           |
| -------------------------------- | --------------------------------------------- | ------- | ------------------------------------------------------------------------ |
| `-i`, `--input`                  | Input `.thd` file path                        | *req.*  | Any `.thd` file                                                          |
| `-bd`, `--bitrate-ddp`           | Bitrate for fallback DDP 5.1                  | 1024    | 256, 384, 448, 640, 1024                                                 |
| `-ba`, `--bitrate-atmos-5-1`     | Bitrate for Atmos 5.1                         | 1024    | 384, 448, 576, 640, 768, 1024                                            |
| `-b7`, `--bitrate-atmos-7-1`     | Bitrate for Atmos 7.1                         | 1536    | 1152, 1280, 1536, 1664                                                   |
| `-am`, `--atmos-mode`            | Select Atmos output mode                      | both    | 5.1, 7.1, both                                                           |
| `-w`, `--warp-mode`              | Warp mode                                     | normal  | normal, warping, prologiciix, loro                                       |
| `-bc`, `--bed-conform`           | Enable bed conform (Atmos only)               | enabled | toggle (default enabled)                                                 |
| `-d`, `--drc`                    | Dynamic Range Control profile                 | none    | film\_standard, film\_light, music\_standard, music\_light, speech, none |
| `-di`, `--dialogue-intelligence` | Enable Dialogue Intelligence                  | true    | true, false                                                              |
| `-nd`, `--disable-dbfs`          | Disable retrieving Dialogue Level from TrueHD | false   | toggle                                                                   |

---

## Example Run

### 1️⃣ Atmos Stream Example

```text
[INFO] Input file: input_atmos.thd
[INFO] Verifying required binaries...
[VERSION] DEE Encoder: 5.2.1
[OK] All required binaries found.
[INFO] Analyzing TrueHD stream...
[INFO] Selected audio settings:
Atmos 5.1 bitrate         → 1024 kbps
Atmos 7.1 bitrate         → 1536 kbps
Dialogue Level            → -31 dB
Dialogue Intelligence     → true
DRC profile               → none
Last Presentation         → 3
Warp mode                 → normal
[INFO] Starting decoding...
████████████████████████████████ 2971927/2971927 frames (100%)
speed: 20.2x | timestamp: 00:00:00.000 | elapsed: 00:00:00
[OK] Atmos file moved to ddp_encode/ddp_encode.atmos
[OK] Atmos file moved to ddp_encode/ddp_encode.atmos.audio
[OK] Atmos file moved to ddp_encode/ddp_encode.atmos.metadata
[INFO] Creating Atmos 5.1 XML...
[OK] XML written to: ddp_encode_atmos_5_1.xml
[INFO] Starting Atmos 5.1 encoding...
[■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■] 100.0% (elapsed: 00:00:00, remaining: 00:00:00, dialnorm_Average: -27 dB)
[INFO] Creating Atmos 7.1 XML...
[OK] XML written to: ddp_encode_atmos_7_1.xml
[INFO] Starting Atmos 7.1 encoding...
[■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■] 100.0% (elapsed: 00:00:00, remaining: 00:00:00, dialnorm_Average: -28 dB)
```

### 2️⃣ Non-Atmos Stream Example

```text
[INFO] Input file: input_non_atmos.thd
[INFO] Verifying required binaries...
[VERSION] DEE Encoder: 5.2.1
[OK] All required binaries found.
[INFO] Analyzing TrueHD stream...
[INFO] Selected audio settings:
Dialogue Level            → -31 dB
Dialogue Intelligence     → true
DDP 5.1 bitrate           → 1024 kbps
DRC profile               → none
Last Presentation         → 2
[INFO] Starting decoding...
████████████████████████████████████████ 7831200/7831200 frames (100%)
speed: 20.2x | timestamp: 00:00:00.000 | elapsed: 00:00:00
[OK] WAV moved to ddp_encode/ddp_encode.wav
[■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■] 100.0% (elapsed: 00:00:00, remaining: 00:00:00)
[INFO] Creating DDP 5.1 XML...
[OK] XML written to: ddp_encode_5_1.xml
[INFO] Starting DDP 5.1 encoding...
[■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■] 100.0% (elapsed: 00:00:00, remaining: 00:00:00, dialnorm_Average: -28 dB)
```

---

## Included Files

### Python scripts

* `main.py` — Primary execution script
* `ddp_config.py` — Generates XML configuration files for DEE encoding

### Third-party tools

* `truehdd` — For audio analysis and decoding

### Dolby Encoding Engine (DEE) package

> **Recommended version:** 5.2.1
> *Note: Proprietary binaries are not included due to licensing restrictions.*

* `dee.exe` / `dee`
* `license.lic`
* `Mediainfo.dll`
* `Mediainfo.exe`
* `mp4muxer.exe`
* `atmos_info.exe`
* `dee_audio_filter_cod.dll`
* `dee_audio_filter_convert_atmos_mezz.dll`
* `dee_audio_filter_ddp.dll`
* `dee_audio_filter_ddp_atmos.dll`
* `dee_audio_filter_ddp_single_pass.dll`
* `dee_audio_filter_ddp_transcode.dll`
* `dee_audio_filter_dthd.dll`
* `dee_audio_filter_edit_ddp.dll`
* `dee_plugin_mp4_mux_base.dll`

---
