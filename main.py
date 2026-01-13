#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import os
import platform
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from colorama import Fore, Style, init

from atmos_editor import transform_atmos_file_inplace
from ddp_config import create_xml_eac3_atmos

init(autoreset=True)

# ---------------------------------------------------------------------
# Paths / Constants
# ---------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(SCRIPT_DIR, "binaries")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "ddp_encode")
os.makedirs(OUTPUT_DIR, exist_ok=True)

ATMOS_EXTS = (".atmos", ".atmos.audio", ".atmos.metadata")


# ---------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------

def info(msg: str) -> None:
    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} {msg}")


def ok(msg: str) -> None:
    print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} {msg}")


def warn(msg: str) -> None:
    print(f"{Fore.YELLOW}[WARN]{Style.RESET_ALL} {msg}")


def err(msg: str) -> None:
    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {msg}")


def die(msg: str, code: int = 1) -> None:
    err(msg)
    raise SystemExit(code)


# ---------------------------------------------------------------------
# Progress bar
# ---------------------------------------------------------------------

def format_time(seconds: float) -> str:
    seconds_i = int(max(0, seconds))
    h = seconds_i // 3600
    m = (seconds_i % 3600) // 60
    s = seconds_i % 60
    return f"{h:02}:{m:02}:{s:02}"


def estimate_remaining(elapsed: float, progress_percent: float) -> float:
    if progress_percent <= 0:
        return 0.0
    total = elapsed / (progress_percent / 100.0)
    return max(0.0, total - elapsed)


def show_progress(
    progress_percent: float,
    start_time: float,
    extra_info: Optional[str] = None,
    bar_len: int = 40,
) -> None:
    progress_percent = max(0.0, min(100.0, progress_percent))
    filled = int(bar_len * progress_percent // 100)
    bar = "■" * filled + "-" * (bar_len - filled)

    elapsed = time.time() - start_time
    remaining = estimate_remaining(elapsed, progress_percent)

    details = f"elapsed: {format_time(elapsed)}, remaining: {format_time(remaining)}"
    if extra_info:
        details += f", {extra_info}"

    sys.stdout.write(f"\r[{bar}] {progress_percent:5.1f}% ({details})")
    sys.stdout.flush()


def finish_progress(
    start_time: float,
    extra_info: Optional[str] = None,
    bar_len: int = 40,
) -> None:
    bar = "■" * bar_len
    elapsed = time.time() - start_time
    details = f"elapsed: {format_time(elapsed)}, remaining: 00:00:00"
    if extra_info:
        details += f", {extra_info}"

    sys.stdout.write(f"\r[{bar}] 100.0% ({details})\n")
    sys.stdout.flush()


# ---------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------

def safe_rename(src: str, dst: str) -> None:
    if os.path.exists(dst):
        os.remove(dst)
    os.rename(src, dst)


def safe_copy_or_move(src: str, dst: str) -> None:
    """
    Moves if possible; if cross-device move fails, falls back to copy+remove.
    """
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        os.remove(dst)
    try:
        os.rename(src, dst)
    except OSError:
        import shutil
        shutil.copy2(src, dst)
        try:
            os.remove(src)
        except FileNotFoundError:
            pass


def remove_files(folder: str, extensions: Iterable[str]) -> None:
    exts = tuple(e.lower() for e in extensions)
    for name in os.listdir(folder):
        if name.lower().endswith(exts):
            try:
                os.remove(os.path.join(folder, name))
            except FileNotFoundError:
                pass


def cleanup_atmos_artifacts_if_needed(atmos_mode: str, after: str) -> None:
    """
    Removes Atmos intermediate artifacts depending on the selected mode.

    Rules:
      - atmos_mode == "5.1"  -> remove after 5.1 encode completes
      - atmos_mode == "7.1"  -> remove after 7.1 encode completes
      - atmos_mode == "both" -> remove only after 7.1 encode completes
    """
    if atmos_mode == after or (atmos_mode == "both" and after == "7.1"):
        info("Removing Atmos intermediate files...")
        remove_files(OUTPUT_DIR, ATMOS_EXTS)
        ok("Atmos intermediate files removed.")


# ---------------------------------------------------------------------
# Tool validation
# ---------------------------------------------------------------------

def exe_path(name: str) -> str:
    exe = f"{name}.exe" if platform.system().lower() == "windows" else name
    return os.path.join(BIN_DIR, exe)


def require_tool(tool_name: str, display_name: str) -> str:
    path = exe_path(tool_name)
    if not os.path.isfile(path):
        die(f"Missing tool: {display_name} ({path})")
    return path


def try_print_dee_version(dee_exec: str) -> None:
    try:
        result = subprocess.run([dee_exec], capture_output=True, text=True)
        m = re.search(r"Version\s+([\d\.]+)", result.stdout)
        if m:
            print(f"{Fore.YELLOW}[VERSION]{Style.RESET_ALL} DEE Encoder: {m.group(1)}")
        else:
            warn("Could not determine DEE version.")
    except Exception:
        warn("Could not run DEE to get version.")


@dataclass(frozen=True)
class Tools:
    truehdd: str
    dee: str
    eac3_fix: str  # eac3_7.1_atmos_fix.exe (only used for 7.1)

    @staticmethod
    def load() -> "Tools":
        info("Verifying required binaries...")
        truehdd = require_tool("truehdd", "TrueHDD Decoder")
        dee = require_tool("dee", "DEE Encoder")
        eac3_fix = require_tool("eac3_7.1_atmos_fix", "EAC3 7.1 Atmos Fix Tool")
        try_print_dee_version(dee)
        ok("All required binaries found.")
        return Tools(truehdd=truehdd, dee=dee, eac3_fix=eac3_fix)


# ---------------------------------------------------------------------
# Subprocess runners
# ---------------------------------------------------------------------

def run_dee(xml_abs_path: str, dee_exec: str, forced_dialogue_level: Optional[int] = None) -> None:
    """
    Runs DEE with progress parsing.
    If forced_dialogue_level is set, it is displayed as dialnorm_Average.
    """
    cmd = [dee_exec, "-x", xml_abs_path]
    start = time.time()

    dialnorm_value: Optional[int] = None
    progress = 0.0

    proc: Optional[subprocess.Popen] = None
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        assert proc.stdout is not None
        for line in proc.stdout:
            m = re.search(r"Overall progress: (\d+\.\d+)", line)
            if m:
                progress = float(m.group(1))
                if forced_dialogue_level is not None:
                    extra = f"dialnorm_Average: {forced_dialogue_level} dB"
                elif dialnorm_value is not None:
                    extra = f"dialnorm_Average: {dialnorm_value} dB"
                else:
                    extra = None
                show_progress(progress, start, extra_info=extra)

            if dialnorm_value is None:
                lm = re.search(r"\[Source loudness\].*measured_loudness=(-?\d+\.\d+)", line)
                if lm:
                    loudness = float(lm.group(1))
                    dialnorm_value = int(round(loudness))
                    if forced_dialogue_level is None:
                        show_progress(progress, start, extra_info=f"dialnorm_Average: {dialnorm_value} dB")

        proc.wait()

        final_dn = forced_dialogue_level if forced_dialogue_level is not None else (dialnorm_value or 0)
        finish_progress(start, extra_info=f"dialnorm_Average: {final_dn} dB")

        if proc.returncode != 0:
            die(f"DEE failed with exit code {proc.returncode}")

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[CANCELED]{Style.RESET_ALL} Canceled by user")
        if proc and proc.poll() is None:
            proc.terminate()
        raise SystemExit(1)
    except Exception as e:
        die(f"Failed to run DEE: {e}")
    finally:
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass


def run_eac3_7_1_fix(fix_exec: str, input_abs: str, output_abs: str) -> None:
    cmd = [fix_exec, "-i", input_abs, "-o", output_abs]
    info("Running eac3_7.1_atmos_fix...")
    res = subprocess.run(cmd)
    if res.returncode != 0:
        die("eac3_7.1_atmos_fix failed.")


# ---------------------------------------------------------------------
# TrueHD stream analysis (Atmos required)
# ---------------------------------------------------------------------

@dataclass
class StreamInfo:
    atmos_flag: str  # "true" / "false"
    last_presentation_num: Optional[int]
    last_dialogue_level: int  # capped to >= -31, or 0 if disabled

    @staticmethod
    def from_truehdd_info(truehdd_exec: str, input_path: str, disable_dbfs: bool) -> "StreamInfo":
        info("Analyzing TrueHD stream...")
        result = subprocess.run(
            [truehdd_exec, "info", input_path],
            capture_output=True,
            text=True,
            check=True,
        )
        lines = result.stdout.splitlines()

        atmos_flag: Optional[str] = None
        for line in lines:
            if "Dolby Atmos" in line:
                atmos_flag = line.split()[-1].lower()
                break
        if atmos_flag is None:
            atmos_flag = "false"

        current_presentation: Optional[int] = None
        last_presentation: Optional[int] = None
        last_dialogue_level: int = -31

        for line in lines:
            if line.strip().startswith("Presentation "):
                try:
                    current_presentation = int(line.strip().split()[1])
                except Exception:
                    current_presentation = None
                    continue

            if "Dialogue Level" in line and current_presentation is not None and not disable_dbfs:
                last_presentation = current_presentation
                try:
                    parts = line.split()
                    level_value = int(parts[-2])
                    if level_value < -31:
                        level_value = -31
                    last_dialogue_level = level_value
                except Exception:
                    last_dialogue_level = -31

        if disable_dbfs:
            last_dialogue_level = 0

        return StreamInfo(
            atmos_flag=atmos_flag,
            last_presentation_num=last_presentation,
            last_dialogue_level=last_dialogue_level,
        )


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="TrueHD Atmos → DDP Atmos (DEE workflow)")
    p.add_argument("-i", "--input", required=True, help="Input TrueHD/MLP file (.thd/.mlp) (Atmos required)")
    p.add_argument("-am", "--atmos-mode", choices=["5.1", "7.1", "both"], default="both", help="Select Atmos output mode (default: both)")
    p.add_argument("-ba", "--bitrate-atmos-5-1", type=int, choices=[384, 448, 576, 640, 768, 1024],
                   default=1024, help="Bitrate for Atmos 5.1 (default: 1024)")
    p.add_argument("-b7", "--bitrate-atmos-7-1", type=int, choices=[1152, 1280, 1536, 1664],
                   default=1536, help="Bitrate for Atmos 7.1 (default: 1536)")
    p.add_argument("-d", "--drc",
                   choices=["film_standard", "film_light", "music_standard", "music_light", "speech", "none"],
                   default="none", help="Dynamic Range Control profile (default: none)")
    p.add_argument("-di", "--dialogue-intelligence", choices=["true", "false"], default="true",
                   help="Enable Dialogue Intelligence (default: true)")
    p.add_argument("-nd", "--disable-dbfs", action="store_true",
                   help="Disable retrieving Dialogue Level from TrueHD (uses 0 if enabled)")
    p.add_argument("-pd", "--preferred-downmix-mode",
                   choices=["loro", "ltrt", "ltrt-pl2", "not_indicated"],
                   default="not_indicated", help="Preferred downmix mode (default: not_indicated)")
    p.add_argument("-w", "--warp-mode", choices=["normal", "warping", "prologiciix", "loro"], default="normal",
                   help="Warp mode (default: normal)")
    return p.parse_args()


# ---------------------------------------------------------------------
# Run-id / normalization
# ---------------------------------------------------------------------

def compute_run_ids(input_path: str) -> Tuple[str, str]:
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    hex_id = hashlib.md5(base_name.encode("utf-8")).hexdigest()[:6]
    return base_name, hex_id


def ensure_work_dir(hex_id: str) -> str:
    work_dir = os.path.join(OUTPUT_DIR, hex_id)
    os.makedirs(work_dir, exist_ok=True)
    return work_dir


def _find_first_file_with_ext(folder: str, ext: str) -> Optional[str]:
    if not os.path.isdir(folder):
        return None
    for name in os.listdir(folder):
        if name.lower().endswith(ext):
            return os.path.join(folder, name)
    return None


def normalize_atmos_artifacts_to_hex(hex_id: str, work_dir: str) -> Tuple[str, str, str]:
    targets = {
        ".atmos": os.path.join(OUTPUT_DIR, f"{hex_id}.atmos"),
        ".atmos.audio": os.path.join(OUTPUT_DIR, f"{hex_id}.atmos.audio"),
        ".atmos.metadata": os.path.join(OUTPUT_DIR, f"{hex_id}.atmos.metadata"),
    }

    sources: dict[str, Optional[str]] = {}
    for ext in targets.keys():
        src = _find_first_file_with_ext(work_dir, ext)
        if src is None:
            src = _find_first_file_with_ext(OUTPUT_DIR, ext)
        sources[ext] = src

    missing = [ext for ext, src in sources.items() if src is None]
    if missing:
        die(f"Missing Atmos artifacts: {', '.join(missing)} (searched in: {work_dir} and {OUTPUT_DIR})")

    for ext, src in sources.items():
        assert src is not None
        dst = targets[ext]
        if os.path.abspath(src) != os.path.abspath(dst):
            safe_copy_or_move(src, dst)

    return targets[".atmos"], targets[".atmos.audio"], targets[".atmos.metadata"]


# ---------------------------------------------------------------------
# Settings print
# ---------------------------------------------------------------------

def print_atmos_settings(args: argparse.Namespace, stream: StreamInfo, hex_id: str) -> None:
    info(f"Run ID: {hex_id}")
    info("Selected Atmos settings:")
    if args.atmos_mode in ("5.1", "both"):
        print(f"{Fore.CYAN}{'Atmos 5.1 bitrate':25} → {args.bitrate_atmos_5_1} kbps{Style.RESET_ALL}")
    if args.atmos_mode in ("7.1", "both"):
        print(f"{Fore.CYAN}{'Atmos 7.1 bitrate':25} → {args.bitrate_atmos_7_1} kbps{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'Dialogue Level':25} → {stream.last_dialogue_level} dB{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'Dialogue Intelligence':25} → {args.dialogue_intelligence}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'DRC profile':25} → {args.drc}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'Preferred Downmix Mode':25} → {args.preferred_downmix_mode}{Style.RESET_ALL}")
    if stream.last_presentation_num is not None:
        print(f"{Fore.CYAN}{'Last Presentation':25} → {stream.last_presentation_num}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'Warp mode':25} → {args.warp_mode}{Style.RESET_ALL}")


# ---------------------------------------------------------------------
# Decode / Encode workflows
# ---------------------------------------------------------------------

def decode_truehd_atmos_only(
    tools: Tools,
    input_file: str,
    stream: StreamInfo,
    work_dir: str,
    hex_id: str,
    warp_mode: str,
) -> None:
    if stream.atmos_flag != "true":
        die("Input stream is not Atmos. This script only supports Atmos workflows now.")

    cmd = [
        tools.truehdd, "decode",
        "--loglevel", "off",
        "--progress", input_file,
        "--output-path", hex_id,
        "--bed-conform",
    ]
    if warp_mode:
        cmd.extend(["--warp-mode", warp_mode])
    if stream.last_presentation_num is not None:
        cmd.extend(["--presentation", str(stream.last_presentation_num)])

    info("Starting TrueHDD Atmos decode...")
    res = subprocess.run(cmd, cwd=OUTPUT_DIR)
    if res.returncode != 0:
        die("Decoding failed (Atmos).")

    atmos_abs, _, _ = normalize_atmos_artifacts_to_hex(hex_id, work_dir)

    changed = transform_atmos_file_inplace(atmos_abs, warp_mode)
    if changed:
        ok("The Atmos file was successfully transformed.")
    else:
        info("No changes were made to the Atmos file.")


def encode_atmos_ddp(
    tools: Tools,
    args: argparse.Namespace,
    stream: StreamInfo,
    hex_id: str,
    base_name: str,
) -> None:
    decoded_atmos_name = f"{hex_id}.atmos"

    cleanup_xml: List[str] = []
    common_args = (
        args.drc,
        args.dialogue_intelligence,
        str(stream.last_dialogue_level),
        args.preferred_downmix_mode,
    )

    if args.atmos_mode in ("5.1", "both"):
        out_5_1 = f"{hex_id}_atmos_5_1.eac3"
        xml_5_1_name = f"{hex_id}_encode_atmos_5_1.xml"
        xml_5_1_abs = os.path.join(OUTPUT_DIR, xml_5_1_name)
        cleanup_xml.append(xml_5_1_abs)

        info("Creating Atmos 5.1 XML...")
        create_xml_eac3_atmos(
            OUTPUT_DIR,
            decoded_atmos_name,
            out_5_1,
            args.bitrate_atmos_5_1,
            xml_5_1_abs,
            *common_args,
            use_7_1=False,
        )

        if not os.path.isfile(xml_5_1_abs):
            die(f"XML was not created where expected: {xml_5_1_abs}")

        info("Starting Atmos 5.1 encoding...")
        run_dee(xml_5_1_abs, tools.dee, forced_dialogue_level=stream.last_dialogue_level)
        final_5_1 = f"{base_name}_atmos_5_1.eac3"
        safe_rename(
            os.path.join(OUTPUT_DIR, out_5_1),
            os.path.join(OUTPUT_DIR, final_5_1),
        )
        ok(f"Saved: {final_5_1}")

        # Cleanup Atmos artifacts depending on mode
        cleanup_atmos_artifacts_if_needed(args.atmos_mode, after="5.1")

    if args.atmos_mode in ("7.1", "both"):
        out_7_1 = f"{hex_id}_atmos_7_1.eac3"
        out_7_1_fix = f"{hex_id}_atmos_7_1_fix.eac3"
        xml_7_1_name = f"{hex_id}_encode_atmos_7_1.xml"
        xml_7_1_abs = os.path.join(OUTPUT_DIR, xml_7_1_name)
        cleanup_xml.append(xml_7_1_abs)

        info("Creating Atmos 7.1 XML...")
        create_xml_eac3_atmos(
            OUTPUT_DIR,
            decoded_atmos_name,
            out_7_1,
            args.bitrate_atmos_7_1,
            xml_7_1_abs,
            *common_args,
            use_7_1=True,
        )

        if not os.path.isfile(xml_7_1_abs):
            die(f"XML was not created where expected: {xml_7_1_abs}")

        info("Starting Atmos 7.1 encoding...")
        run_dee(xml_7_1_abs, tools.dee, forced_dialogue_level=stream.last_dialogue_level)

        # Fix step (7.1 only)
        in_abs = os.path.join(OUTPUT_DIR, out_7_1)
        fix_abs = os.path.join(OUTPUT_DIR, out_7_1_fix)
        run_eac3_7_1_fix(tools.eac3_fix, in_abs, fix_abs)

        # Remove original 7.1 before final rename
        try:
            os.remove(in_abs)
        except FileNotFoundError:
            pass

        final_7_1 = f"{base_name}_atmos_7_1.eac3"
        safe_rename(
            os.path.join(OUTPUT_DIR, out_7_1_fix),
            os.path.join(OUTPUT_DIR, final_7_1),
        )
        ok(f"Saved: {final_7_1}")

        # Cleanup Atmos artifacts depending on mode (always after 7.1 for "both")
        cleanup_atmos_artifacts_if_needed(args.atmos_mode, after="7.1")

    for xml_abs in cleanup_xml:
        try:
            os.remove(xml_abs)
        except FileNotFoundError:
            pass


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    tools = Tools.load()

    if not os.path.isfile(args.input):
        die(f"Input must be a file: {args.input}")

    input_name = os.path.basename(args.input)
    if not input_name.lower().endswith((".thd", ".mlp")):
        die("Unsupported file type. Provide .thd or .mlp (Atmos).")

    base_name, hex_id = compute_run_ids(args.input)
    work_dir = ensure_work_dir(hex_id)

    try:
        stream = StreamInfo.from_truehdd_info(tools.truehdd, args.input, args.disable_dbfs)
    except subprocess.CalledProcessError as e:
        die(f"TrueHDD info failed: {e}")

    if stream.atmos_flag != "true":
        die("Input is not Dolby Atmos. Non-Atmos workflow has been removed.")

    print_atmos_settings(args, stream, hex_id)

    decode_truehd_atmos_only(
        tools=tools,
        input_file=args.input,
        stream=stream,
        work_dir=work_dir,
        hex_id=hex_id,
        warp_mode=args.warp_mode,
    )

    encode_atmos_ddp(tools, args, stream, hex_id, base_name)


if __name__ == "__main__":
    main()
