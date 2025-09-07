# Atmos-Encoder

**Atmos-Encoder** is a Python tool that converts Dolby TrueHD audio into **Dolby Digital Plus (E-AC3)** format while preserving Dolby Atmos metadata when available.

---

## ⚠️ Important Notice

* The **TrueHD Atmos** feature is in **beta** and may change or be removed in future updates.
* `.atmos` files must reside on the **same drive** as the script execution directory (applies to both DDP and TrueHD Atmos).
* **ADM files** are supported exclusively by **TrueHD Atmos** and require the **Dolby Atmos Conversion Tool** (Windows) located at:
  `C:\Program Files\Dolby\Dolby Atmos Conversion Tool`

---

## Overview

* Automatic detection of Atmos content in `.thd` files.
* Outputs:

  * Dolby Digital Plus 5.1 with Atmos (`_atmos_5_1.mp4`)
  * Dolby Digital Plus 7.1 with Atmos (`_atmos_7_1.mp4`)
  * Or both, depending on the selected mode
* Non-Atmos streams are converted to standard DDP 5.1 using **FFmpeg/FFprobe** for resampling to 48 kHz PCM (DEE compatibility).

---

## Features

* Automatic Atmos detection via [`truehdd`](https://github.com/truehdd/truehdd)
* Converts TrueHD Atmos to DDP Atmos (5.1, 7.1, or both)
* Configurable bitrates and warp modes (`normal`, `warping`, `prologiciix`, `loro`)
* Optional bed conform for Atmos streams (default: enabled)
* Cross-platform support: Windows, Linux, macOS
* Live progress display for DEE and FFmpeg
* Automatic file organization and cleanup
* **Recommended DEE version:** 5.2.1
* FFmpeg/FFprobe required only for non-Atmos streams

---

## Requirements

* Python ≥ 3.7
* Python module: `colorama` (`pip install colorama`)
* Required binaries and tools:

  * **Python scripts:** `main.py`, `ddp_config.py`, `atmos_editor.py`
  * **Third-party tools:** `truehdd`, `ffmpeg`, `ffprobe`, `cmdline_atmos_conversion_tool`, `dee`

---

## Usage

### 1️⃣ DDP Atmos (from TrueHD `.thd` file)

```bash
python main.py -i input_file.thd -ba 1024 -b7 1536 -am both -w normal -bc
```

### 2️⃣ TrueHD Atmos (from ADM WAV)

```bash
python main.py -i input_adm.wav -t
```

*Use `-t` to enable the TrueHD Atmos workflow. Only ADM WAV files are supported for TrueHD Atmos; standard 5.1 WAV files will be converted to DDP only.*

### 3️⃣ TrueHD Atmos from `.atmos` folder

```bash
python main.py -i input_folder -t
```

*The folder must contain:*

* `*.atmos`
* `*.atmos.metadata`
* `*.atmos.audio`

*Use `-t` to activate TrueHD Atmos; if `-t` is not used, the encoder will process as DDP Atmos.*

---

**Main Parameters (summary):**

| Parameter | Description               | Default        | Values                                     |
| --------- | ------------------------- | -------------- | ------------------------------------------ |
| `-i`      | Input `.thd` file         | Required       | `.thd` only                                |
| `-am`     | Atmos output mode         | both           | 5.1, 7.1, both                             |
| `-ba`     | Atmos 5.1 bitrate         | 1024           | 384–1024 kbps                              |
| `-b7`     | Atmos 7.1 bitrate         | 1536           | 1152–1664 kbps                             |
| `-bd`     | DDP fallback bitrate      | 1024           | 256–1024 kbps                              |
| `-d`      | DRC profile               | none           | film\_standard, music\_light, speech, none |
| `-di`     | Dialogue Intelligence     | true           | true, false                                |
| `-nd`     | Disable dialogue recovery | false          | toggle                                     |
| `-pd`     | Preferred downmix         | not\_indicated | loro, ltrt, ltrt-pl2                       |
| `-sc`     | Spatial clusters          | 12             | 12, 14, 16                                 |
| `-t`      | Enable TrueHD Atmos       | false          | toggle                                     |
| `-w`      | Warp mode                 | normal         | normal, warping, prologiciix, loro         |

---

## Included Files

### Python Scripts

* `main.py` — Main execution script
* `ddp_config.py` — DEE XML configuration
* `atmos_editor.py` — Atmos editing utilities

### Third-party Tools

* `truehdd` — Audio analysis and decoding
* `ffmpeg`, `ffprobe` — Required for non-Atmos streams
* `cmdline_atmos_conversion_tool` — Required for ADM files

### DEE Package

> **Recommended version:** 5.2.1
> *Proprietary binaries are not included due to licensing restrictions.*

**Executables:**
`dee.exe`, `mp4muxer.exe`, `atmos_info.exe`, `Mediainfo.exe`

**Audio filter DLLs:**
`dee_audio_filter_cod.dll`, `dee_audio_filter_convert_atmos_mezz.dll`, `dee_audio_filter_ddp.dll`, `dee_audio_filter_ddp_atmos.dll`, `dee_audio_filter_ddp_single_pass.dll`, `dee_audio_filter_ddp_transcode.dll`, `dee_audio_filter_dthd.dll`, `dee_audio_filter_edit_ddp.dll`, `dee_plugin_mp4_mux_base.dll`

**License:** `license.lic`

---

### ADM / Dolby Atmos Conversion Tool (Windows)

**Executable:** `cmdline_atmos_conversion_tool.exe`

**Required DLLs:**
`atmos_storage.dll`, `atmos_storage_adm_bwf.dll`, `atmos_storage_damf.dll`, `atmos_storage_damf_create.dll`, `atmos_storage_iab.dll`, `atmos_storage_rpl.dll`, `atmos_storage_composite.dll`, `atmos_storage_composite_xml.dll`

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
[■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■] 100.0% (elapsed: 00:00:00, remaining: 00:00:00, dialnorm_Average: -31 dB)
[INFO] Creating Atmos 7.1 XML...
[OK] XML written to: ddp_encode_atmos_7_1.xml
[INFO] Starting Atmos 7.1 encoding...
[■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■] 100.0% (elapsed: 00:00:00, remaining: 00:00:00, dialnorm_Average: -31 dB)
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
[■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■] 100.0% (elapsed: 00:00:00, remaining: 00:00:00, dialnorm_Average: -31 dB)
```

### 3️⃣ TrueHD Atmos Stream Example

```text
[INFO] Starting TrueHD Atmos conversion...
[INFO] Duration: 180s | Estimated size: 618 MiB
[INFO] Starting ADM to Atmos conversion...
[■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■] 100.0% (elapsed: 00:00:00, remaining: 00:00:00)
[INFO] Final size: 618 MiB
[INFO] Estimated size: 618 MiB
[OK] Atmos file moved to ddp_encode/output.atmos
[OK] Atmos file moved to ddp_encode/output.atmos.audio
[OK] Atmos file moved to ddp_encode/output.atmos.metadata
[INFO] No changes were made to the Atmos file.
[INFO] Selected TrueHD Atmos settings:
Dialogue Intelligence     → true
DRC profile               → film_light
Spatial Clusters          → 12
[INFO] Creating Atmos 7.1 XML...
[OK] XML written to: mlp_encode_atmos_7_1.xml
[INFO] Starting MLP Atmos 7.1 encoding...
[■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■] 100.0% (elapsed: 00:00:00, remaining: 00:00:00, dialnorm_Average: -31 dB)
```
