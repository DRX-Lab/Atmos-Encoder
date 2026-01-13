# Atmos-Encoder

**Atmos-Encoder** converts **Dolby TrueHD Atmos** audio into **Dolby Digital Plus (E-AC-3) Atmos** using **DEE**, preserving Atmos metadata and correcting known 7.1 layout issues.

---

## Scope

* **Atmos-only** workflow
* Input: `.thd` / `.mlp` with Dolby Atmos
* Output: `.eac3`
* Non-Atmos streams are **not supported**

---

## What It Does

* Detects Dolby Atmos automatically
* Decodes Atmos with `truehdd`
* Encodes E-AC-3 Atmos:

  * 5.1
  * 7.1
  * or both
* Fixes incorrect **7.1 channel layout** produced by DEE
* Applies consistent dialogue and downmix settings
* Cleans up intermediate Atmos artifacts automatically

---

## Output

* `<input>_atmos_5_1.eac3`
* `<input>_atmos_7_1.eac3`

---

## Requirements

### Python

* Python ≥ 3.7
* `colorama`

```bash
pip install colorama
```

### Binaries (must be in `binaries/`)

* `truehdd`
* `DEE encoder + required DEE DLLs`
* **`eac3_7.1_atmos_fix.exe`** (required for Atmos 7.1)

Download:
[https://github.com/DRX-Lab/eac3-7.1-atmos-fix/releases/tag/v0.0.2](https://github.com/DRX-Lab/eac3-7.1-atmos-fix/releases/tag/v0.0.2)

This binary fixes a DEE issue where Atmos 7.1 is incorrectly tagged as Top Front channels instead of Rear Surrounds.

---

## Usage

```bash
python main.py -i input.thd
```

### Main Options

| Option | Description               | Default       |
| ------ | ------------------------- | ------------- |
| `-i`   | Input Atmos file          | required      |
| `-am`  | Atmos output mode         | both          |
| `-ba`  | Atmos 5.1 bitrate         | 1024          |
| `-b7`  | Atmos 7.1 bitrate         | 1536          |
| `-d`   | DRC profile               | none          |
| `-di`  | Dialogue Intelligence     | true          |
| `-nd`  | Disable dialogue recovery | false         |
| `-pd`  | Preferred downmix mode    | not_indicated |
| `-w`   | Warp mode                 | normal        |

---

## Internal Notes

* Atmos-only pipeline
* Only one XML generator remains: `create_xml_eac3_atmos`
* Downmix coefficients standardized to **-3 dB**
* Per-run isolated working directories
* Mode-aware cleanup logic

---

## License

Dolby proprietary tools are **not included**.
You must provide licensed binaries yourself.
