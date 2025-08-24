import os
import sys
import re
import time
import argparse
import subprocess
import platform
from colorama import Fore, Style, init
from ddp_config import create_xml_5_1, create_xml_5_1_atmos, create_xml_7_1_atmos

init(autoreset=True)

# -------------------- Constants -------------------- #
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(SCRIPT_DIR, "binaries")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "ddp_encode")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# -------------------- Utility Functions -------------------- #

def get_executable_name(name):
    exe_name = f"{name}.exe" if platform.system().lower() == "windows" else name
    return os.path.join(BIN_DIR, exe_name)

def check_tool(executable_path, display_name):
    if not os.path.isfile(executable_path):
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Missing tool: {display_name}")
        sys.exit(1)
    return executable_path

def safe_rename(src, dst):
    if os.path.exists(dst):
        os.remove(dst)
    os.rename(src, dst)

def build_path(filename, folder=OUTPUT_DIR):
    return os.path.join(folder, filename)

def remove_files(folder, extensions):
    for f in os.listdir(folder):
        if f.endswith(extensions):
            os.remove(build_path(f, folder))

def format_time(seconds):
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02}:{m:02}:{s:02}"

def estimate_remaining(elapsed, progress):
    if progress <= 0:
        return 0
    total = elapsed / (progress / 100)
    return int(total - elapsed)

def show_progress(progress, elapsed=0, remaining=0, extra_info=None, length=40):
    filled = int(length * progress // 100)
    bar = '■' * filled + '-' * (length - filled)
    details = f"elapsed: {format_time(elapsed)}, remaining: {format_time(remaining)}"
    if extra_info:
        details += f", {extra_info}"
    sys.stdout.write(f"\r[{bar}] {progress:5.1f}% ({details})")
    sys.stdout.flush()

def finish_progress(start_time, extra_info=None, length=40):
    bar = '■' * length
    elapsed = time.time() - start_time
    details = f"elapsed: {format_time(elapsed)}, remaining: 00:00:00"
    if extra_info:
        details += f", {extra_info}"
    sys.stdout.write(f"\r[{bar}] 100.0% ({details})\n")
    sys.stdout.flush()

# -------------------- Process Functions -------------------- #

def run_dee(xml_file):
    xml_full = build_path(xml_file)
    dee_exec = check_tool(get_executable_name("dee"), "DEE Encoder")
    command = [dee_exec, "-x", xml_full]

    start_time = time.time()
    dialnorm_value = None
    progress = 0.0

    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in process.stdout:
            match = re.search(r"Overall progress: (\d+\.\d+)", line)
            if match:
                progress = float(match.group(1))
                elapsed = time.time() - start_time
                remaining = estimate_remaining(elapsed, progress)
                extra_info = f"dialnorm_Average: {dialnorm_value} dB" if dialnorm_value is not None else None
                show_progress(progress, elapsed, remaining, extra_info)

            if dialnorm_value is None:
                loudness_match = re.search(r"\[Source loudness\].*measured_loudness=(-?\d+\.\d+)", line)
                if loudness_match:
                    loudness = float(loudness_match.group(1))
                    dialnorm_value = int(round(loudness))
                    elapsed = time.time() - start_time
                    remaining = estimate_remaining(elapsed, progress)
                    show_progress(progress, elapsed, remaining, f"dialnorm_Average: {dialnorm_value} dB")

        process.wait()
        extra_info = f"dialnorm_Average: {dialnorm_value} dB" if dialnorm_value is not None else None
        finish_progress(start_time, extra_info)

    except Exception as e:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to run DEE: {e}")
    finally:
        try:
            process.terminate()
        except:
            pass

def run_ffmpeg_with_progress(input_file, output_file):
    ffmpeg_exec = check_tool(get_executable_name("ffmpeg"), "FFmpeg")
    ffprobe_exec = check_tool(get_executable_name("ffprobe"), "FFprobe")

    total_duration = float(subprocess.run([ffprobe_exec,
                                           "-v", "error",
                                           "-show_entries", "format=duration",
                                           "-of", "default=noprint_wrappers=1:nokey=1",
                                           input_file],
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                           text=True).stdout.strip())

    cmd = [
        ffmpeg_exec,
        "-nostdin",
        "-loglevel", "error",
        "-stats",
        "-y",
        "-i", input_file,
        "-c:a", "pcm_s32le",
        "-filter_complex", "[a:0]aresample=resampler=soxr",
        "-ar", "48000",
        "-precision", "28",
        "-cutoff", "1",
        "-dither_scale", "0",
        "-rf64", "always",
        output_file
    ]

    start_time = time.time()
    process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")
    for line in process.stderr:
        match = time_pattern.search(line)
        if match:
            hours, minutes, seconds = match.groups()
            current_time = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            progress = min(100, (current_time / total_duration) * 100)
            elapsed = time.time() - start_time
            remaining = estimate_remaining(elapsed, progress)
            show_progress(progress, elapsed, remaining)

    process.wait()
    finish_progress(start_time)

# -------------------- Argument Parsing -------------------- #

parser = argparse.ArgumentParser(description="TrueHD to DDP encoder with Atmos support")
parser.add_argument("-i", "--input", required=True, help="Input TrueHD (.thd) file path")
parser.add_argument("-bd", "--bitrate-ddp", type=int, choices=[256,384,448,640,1024], default=1024, help="Bitrate for DDP 5.1 (default: 1024)")
parser.add_argument("-ba", "--bitrate-atmos-5-1", type=int, choices=[384,448,576,640,768,1024], default=1024, help="Bitrate for Atmos 5.1 (default: 1024)")
parser.add_argument("-b7", "--bitrate-atmos-7-1", type=int, choices=[1152,1280,1536,1664], default=1536, help="Bitrate for Atmos 7.1 (default: 1536)")
parser.add_argument("-am", "--atmos-mode", choices=["5.1","7.1","both"], default="both", help="Select Atmos output mode")
parser.add_argument("-w", "--warp-mode", choices=["normal","warping","prologiciix","loro"], default="normal", help="Warp mode (default: normal)")
parser.add_argument("-bc", "--bed-conform", action="store_true", default=True, help="Enable bed conform for Atmos (default: enabled)")
args = parser.parse_args()

input_file = os.path.abspath(args.input)
input_name = os.path.basename(input_file)

print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Input file: {input_name}")
if not os.path.isfile(input_file):
    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} File does not exist: {input_name}")
    sys.exit(1)

# -------------------- Tool Checks -------------------- #

truehdd_path = check_tool(get_executable_name("truehdd"), "TrueHDD Decoder")

# -------------------- Analyze Stream -------------------- #

print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Analyzing TrueHD stream...")
atmos_flag = None
last_presentation_num = None

try:
    result = subprocess.run([truehdd_path, "info", input_file], capture_output=True, text=True, check=True)
    lines = result.stdout.splitlines()

    for line in lines:
        if "Dolby Atmos" in line:
            atmos_flag = line.split()[-1].lower()
            break

    if atmos_flag == "true":
        print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} Dolby Atmos detected.")
    elif atmos_flag == "false":
        print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} Dolby Atmos not present.")
        for line in lines:
            if line.strip().startswith("Presentation "):
                try:
                    last_presentation_num = int(line.strip().split()[1])
                except:
                    continue
        if last_presentation_num:
            print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Last Presentation found: {last_presentation_num}")
    else:
        print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} Atmos information unavailable.")

except subprocess.CalledProcessError as e:
    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Info command failed: {e}")
    sys.exit(1)

# -------------------- Settings -------------------- #

print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Selected bitrates and warp mode:")
if atmos_flag != "true":
    print(f"  DDP 5.1 bitrate: {args.bitrate_ddp} kbps")
else:
    if args.atmos_mode in ["5.1", "both"]:
        print(f"  Atmos 5.1 bitrate: {args.bitrate_atmos_5_1} kbps")
    if args.atmos_mode in ["7.1", "both"]:
        print(f"  Atmos 7.1 bitrate: {args.bitrate_atmos_7_1} kbps")
    print(f"  Warp mode: {args.warp_mode}")

# -------------------- Decoding -------------------- #

decode_cmd = [truehdd_path,
              "decode",
              "--loglevel", "off",
              "--progress", input_file,
              "--output-path", OUTPUT_DIR]

if atmos_flag == "true":
    decode_cmd.extend(["--warp-mode", args.warp_mode])
    if args.bed_conform:
        decode_cmd.append("--bed-conform")
else:
    decode_cmd.extend(["--format", "w64",
                       "--presentation", str(last_presentation_num)])

print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Starting decoding...")
decode_result = subprocess.run(decode_cmd)
if decode_result.returncode != 0:
    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Decoding failed.")
    sys.exit(1)

# -------------------- File Organization -------------------- #
decoded_audio_file = None
decoded_atmos_file = None
decoded_mp4_file_5_1 = None
decoded_mp4_file_7_1 = None

for f in os.listdir(SCRIPT_DIR):
    f_path = os.path.join(SCRIPT_DIR, f)
    f_lower = f.lower()
    
    # Skip files already in OUTPUT_DIR
    if os.path.commonpath([f_path, OUTPUT_DIR]) == OUTPUT_DIR:
        continue

    # WAV files
    if f_lower.endswith(".wav"):
        new_name = "ddp_encode.wav"
        target = os.path.join(OUTPUT_DIR, new_name)
        if os.path.exists(target):
            os.remove(target)
        os.rename(f_path, target)
        decoded_audio_file = new_name
        print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} WAV moved to {os.path.basename(OUTPUT_DIR)}/{new_name}")

    # Atmos files
    elif f_lower.endswith((".atmos", ".atmos.metadata", ".atmos.audio")):
        if ".atmos" in f_lower:
            suffix = f_lower.split("atmos", 1)[1]
            new_name = f"ddp_encode.atmos{suffix}"
        else:
            new_name = "ddp_encode.atmos"
        target = os.path.join(OUTPUT_DIR, new_name)
        if os.path.exists(target):
            os.remove(target)
        os.rename(f_path, target)
        if new_name == "ddp_encode.atmos":
            decoded_atmos_file = new_name
        print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} Atmos file moved to {os.path.basename(OUTPUT_DIR)}/{new_name}")

# -------------------- Encoding -------------------- #
base_name = os.path.splitext(os.path.basename(input_file))[0]

if atmos_flag == "true":
    if decoded_atmos_file is None:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} No Atmos file found for encoding!")
        sys.exit(1)

    cleanup_targets = []

    if args.atmos_mode in ["5.1", "both"]:
        decoded_mp4_file_5_1 = "ddp_encode_atmos_5_1.mp4"
        xml_5_1 = "ddp_encode_atmos_5_1.xml"
        cleanup_targets.append(xml_5_1)
        print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Creating Atmos 5.1 XML...")
        create_xml_5_1_atmos(OUTPUT_DIR, decoded_atmos_file, decoded_mp4_file_5_1, args.bitrate_atmos_5_1, xml_5_1)
        print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Starting Atmos 5.1 encoding...")
        run_dee(xml_5_1)
        safe_rename(
            os.path.join(OUTPUT_DIR, decoded_mp4_file_5_1),
            os.path.join(OUTPUT_DIR, f"{base_name}_atmos_5_1.mp4")
        )

    if args.atmos_mode in ["7.1", "both"]:
        decoded_mp4_file_7_1 = "ddp_encode_atmos_7_1.mp4"
        xml_7_1 = "ddp_encode_atmos_7_1.xml"
        cleanup_targets.append(xml_7_1)
        print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Creating Atmos 7.1 XML...")
        create_xml_7_1_atmos(OUTPUT_DIR, decoded_atmos_file, decoded_mp4_file_7_1, args.bitrate_atmos_7_1, xml_7_1)
        print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Starting Atmos 7.1 encoding...")
        run_dee(xml_7_1)
        safe_rename(
            os.path.join(OUTPUT_DIR, decoded_mp4_file_7_1),
            os.path.join(OUTPUT_DIR, f"{base_name}_atmos_7_1.mp4")
        )

    remove_files(OUTPUT_DIR, (".atmos", ".atmos.metadata", ".atmos.audio"))
    for x in cleanup_targets:
        os.remove(os.path.join(OUTPUT_DIR, x))

else:
    if decoded_audio_file is None:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} No WAV file found for encoding!")
        sys.exit(1)

    temp_file = os.path.join(OUTPUT_DIR, f"{decoded_audio_file}_temp.wav")
    run_ffmpeg_with_progress(os.path.join(OUTPUT_DIR, decoded_audio_file), temp_file)
    os.replace(temp_file, os.path.join(OUTPUT_DIR, decoded_audio_file))

    decoded_mp4_file_5_1 = "ddp_encode_5_1.mp4"
    xml_5_1 = "ddp_encode_5_1.xml"
    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Creating DDP 5.1 XML...")
    create_xml_5_1(OUTPUT_DIR, decoded_audio_file, decoded_mp4_file_5_1, args.bitrate_ddp, xml_5_1)
    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Starting DDP 5.1 encoding...")
    run_dee(xml_5_1)
    safe_rename(
        os.path.join(OUTPUT_DIR, decoded_mp4_file_5_1),
        os.path.join(OUTPUT_DIR, f"{base_name}_5_1.mp4")
    )
    remove_files(OUTPUT_DIR, (".wav",))
    os.remove(os.path.join(OUTPUT_DIR, xml_5_1))