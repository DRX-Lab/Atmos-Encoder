import os
import sys
import re
import time
import argparse
import subprocess
import platform
from colorama import Fore, Style, init
from atmos_editor import transform_atmos_file_inplace
from ddp_config import create_xml_eac3, create_xml_eac3_atmos, create_xml_mlp_atmos

init(autoreset=True)

# -------------------- Constants -------------------- #
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(SCRIPT_DIR, "binaries")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "ddp_encode")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# -------------------- Utility Functions -------------------- #

def check_same_disk(input_path: str, output_path: str):
    system = platform.system().lower()

    input_abs = os.path.abspath(input_path)
    output_abs = os.path.abspath(output_path)

    if system == "windows":
        input_drive = os.path.splitdrive(input_abs)[0].upper()
        output_drive = os.path.splitdrive(output_abs)[0].upper()
        if input_drive != output_drive:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Input and output are on different drives. Please place them on the same drive.")
            sys.exit(1)
    else:
        if os.stat(input_abs).st_dev != os.stat(output_abs).st_dev:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Input and output are on different disks. Please place them on the same disk.")
            sys.exit(1)

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

# -------------------- Processing Functions -------------------- #
def run_dee(xml_file, dee_exec, last_dialogue_level=0):
    xml_full = build_path(xml_file)
    command = [dee_exec, "-x", xml_full]

    start_time = time.time()
    dialnorm_value = None
    progress = 0.0

    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            for line in process.stdout:
                match = re.search(r"Overall progress: (\d+\.\d+)", line)
                if match:
                    progress = float(match.group(1))
                    elapsed = time.time() - start_time
                    remaining = estimate_remaining(elapsed, progress)

                    if last_dialogue_level != 0:
                        extra_info = f"dialnorm_Average: {last_dialogue_level} dB"
                    elif dialnorm_value is not None:
                        extra_info = f"dialnorm_Average: {dialnorm_value} dB"
                    else:
                        extra_info = None

                    show_progress(progress, elapsed, remaining, extra_info)

                if dialnorm_value is None:
                    loudness_match = re.search(r"\[Source loudness\].*measured_loudness=(-?\d+\.\d+)", line)
                    if loudness_match:
                        loudness = float(loudness_match.group(1))
                        dialnorm_value = int(round(loudness))
                        if last_dialogue_level == 0:
                            elapsed = time.time() - start_time
                            remaining = estimate_remaining(elapsed, progress)
                            show_progress(progress, elapsed, remaining, f"dialnorm_Average: {dialnorm_value} dB")

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}[CANCELED]{Style.RESET_ALL} Canceled by user")
            sys.exit(1)
            process.terminate()
            return

        process.wait()
        final_value = last_dialogue_level if last_dialogue_level != 0 else dialnorm_value
        finish_progress(start_time, f"dialnorm_Average: {final_value} dB")

    except Exception as e:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Failed to run DEE: {e}")
    finally:
        try:
            process.terminate()
        except:
            pass
        
def run_adm_to_atmos(input_file, admtoatmos_exec, ffprobe_exec):
    duration_sec = None
    estimated_size_bytes = None
    try:
        result = subprocess.run([ffprobe_exec,
                                 "-v", "error",
                                 "-show_entries", "format=duration",
                                 "-of", "default=noprint_wrappers=1:nokey=1",
                                 input_file],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                check=True)
        if result.stdout.strip():
            duration_sec = float(result.stdout.strip())
    except Exception as e:
        print(f"{Fore.YELLOW}[WARN]{Style.RESET_ALL} ffprobe duration check failed: {e}")

    if duration_sec:
        bitrate_mbps = 28.8
        size_mib = (bitrate_mbps * duration_sec) / 8 / (1024 * 1024 / 1_000_000)
        estimated_size_bytes = size_mib * 1024 * 1024
        print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Duration: {duration_sec:.0f}s | Estimated size: {size_mib:.0f} MiB")
    else:
        print(f"{Fore.YELLOW}[WARN]{Style.RESET_ALL} Duration not available, relying only on stdout progress")

    cmd = [
        admtoatmos_exec,
        "-i", input_file,
        "-f", "atmos",
        "--source_fps", "24",
        "--target_sample_rate", "48000"
    ]

    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Starting ADM to Atmos conversion...")
    start_time = time.time()
    output_audio = "output.atmos.audio"

    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as proc:
        try:
            while True:
                line = proc.stdout.readline()
                if not line:
                    if proc.poll() is not None:
                        break
                    continue

                line = line.strip()
                match = re.search(r'Progress\s*-\s*(\d+)\s*%', line)
                reached_100_stdout = match and int(match.group(1)) == 100
                percent_size = 0
                if estimated_size_bytes and os.path.exists(output_audio):
                    current_size = os.path.getsize(output_audio)
                    percent_size = min(100, (current_size / estimated_size_bytes) * 100)
                elapsed_sec = int(time.time() - start_time)
                remaining_sec = int((elapsed_sec / percent_size * (100 - percent_size)) if percent_size > 0 else 0)
                show_progress(percent_size, elapsed_sec, remaining_sec)
                if percent_size >= 100 or reached_100_stdout:
                    break

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}[CANCELED]{Style.RESET_ALL} Canceled by user")
            proc.terminate()
            sys.exit(1)

        proc.wait()

    finish_progress(start_time)
    if os.path.exists(output_audio):
        final_size_mib = os.path.getsize(output_audio) / (1024 * 1024)
        print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Final size: {final_size_mib:.0f} MiB")
        if estimated_size_bytes:
            estimated_size_mib = estimated_size_bytes / (1024 * 1024)
            print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Estimated size: {estimated_size_mib:.0f} MiB")


def run_ffmpeg_with_progress(input_file, output_file, ffmpeg_exec, ffprobe_exec):
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
    try:
        for line in process.stderr:
            match = time_pattern.search(line)
            if match:
                hours, minutes, seconds = match.groups()
                current_time = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                progress = min(100, (current_time / total_duration) * 100)
                elapsed = time.time() - start_time
                remaining = estimate_remaining(elapsed, progress)
                show_progress(progress, elapsed, remaining)
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[CANCELED]{Style.RESET_ALL} Canceled by user")
        sys.exit(1)
        process.terminate()
        return

    process.wait()
    finish_progress(start_time)

# -------------------- Argument Parsing -------------------- #

parser = argparse.ArgumentParser(description="TrueHD to DDP encoder with Atmos support")
parser.add_argument("-am", "--atmos-mode", choices=["5.1", "7.1", "both"], default="both", help="Select Atmos output mode (default: both)")
parser.add_argument("-ba", "--bitrate-atmos-5-1", type=int, choices=[384, 448, 576, 640, 768, 1024], default=1024, help="Bitrate for Atmos 5.1 (default: 1024)")
parser.add_argument("-b7", "--bitrate-atmos-7-1", type=int, choices=[1152, 1280, 1536, 1664], default=1536, help="Bitrate for Atmos 7.1 (default: 1536)")
parser.add_argument("-bd", "--bitrate-ddp", type=int, choices=[256, 384, 448, 640, 1024], default=1024, help="Bitrate for DDP 5.1 (default: 1024)")
parser.add_argument("-d", "--drc", choices=["film_standard", "film_light", "music_standard", "music_light", "speech", "none"], default="none", help="Dynamic Range Control profile (default: none)")
parser.add_argument("-di", "--dialogue-intelligence", choices=["true", "false"], default="true", help="Enable Dialogue Intelligence (default: true)")
parser.add_argument("-i", "--input", required=True, help="Input TrueHD (.thd) file path")
parser.add_argument("-nd", "--disable-dbfs", action="store_true", help="Disable retrieving Dialogue Level from TrueHD (default: use 0 if disabled)")
parser.add_argument("-pd", "--preferred-downmix-mode", choices=["loro", "ltrt", "ltrt-pl2", "not_indicated"], default="not_indicated", help="Preferred downmix mode (default: not_indicated)")
parser.add_argument("-sc", "--spatial-clusters", type=int, choices=[12, 14, 16], default=12, help="Number of spatial clusters (default: 12, allowed: 12, 14, 16)")
parser.add_argument("-t", "--truehd-atmos", action="store_true", help="Enable TrueHD Atmos mode (if enabled, the script will run a different process)")
parser.add_argument("-w", "--warp-mode", choices=["normal", "warping", "prologiciix", "loro"], default="normal", help="Warp mode (default: normal)")
args = parser.parse_args()

# -------------------- Tool Checks (All at start) -------------------- #
required_tools = [
    ("truehdd", "TrueHDD Decoder"),
    ("ffmpeg", "FFmpeg"),
    ("ffprobe", "FFprobe"),
    ("dee", "DEE Encoder"),
    ("cmdline_atmos_conversion_tool", "ADM to Atmos Tool")
]

tools_paths = {}
print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Verifying required binaries...")
for exe_name, display_name in required_tools:
    path = check_tool(get_executable_name(exe_name), display_name)
    tools_paths[exe_name] = path
    if exe_name == "dee":
        try:
            result = subprocess.run([path], capture_output=True, text=True)
            version_pattern = r"Version\s+([\d\.]+)"
            match = re.search(version_pattern, result.stdout)
            if match:
                version = match.group(1)
                print(f"{Fore.YELLOW}[VERSION]{Style.RESET_ALL} {display_name}: {version}")
            else:
                print(f"{Fore.RED}[WARN]{Style.RESET_ALL} Could not determine {display_name} version")
        except Exception:
            print(f"{Fore.RED}[WARN]{Style.RESET_ALL} Could not run {display_name} to get version")

print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} All required binaries found.")

# -------------------- TrueHD Atmos Workflow -------------------- #
if args.truehd_atmos:
    if not os.path.exists(args.input):
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Input path does not exist: {args.input}")
        sys.exit(1)

    base_name = os.path.splitext(os.path.basename(args.input.rstrip(os.sep)))[0]
    cleanup_targets = []

    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Starting TrueHD Atmos conversion...")

    input_files = []
    run_conversion = False

    if os.path.isfile(args.input):
        input_files.append(args.input)
        run_conversion = True
    elif os.path.isdir(args.input):
        input_path_abs = os.path.abspath(args.input)

        check_same_disk(input_path_abs, OUTPUT_DIR)

        for f in os.listdir(args.input):
            if f.lower().endswith((".atmos", ".atmos.metadata", ".atmos.audio")):
                input_files.append(os.path.join(args.input, f))
    else:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Input is neither a file nor a folder: {args.input}")
        sys.exit(1)

    if run_conversion:
        for file_path in input_files:
            run_adm_to_atmos(file_path, tools_paths["cmdline_atmos_conversion_tool"], tools_paths["ffprobe"])

        generated_atmos_files = [
            f for f in os.listdir('.') 
            if f.lower().endswith((".atmos", ".atmos.metadata", ".atmos.audio"))
        ]
        input_files = generated_atmos_files

    decoded_atmos_file = None
    for file_path in input_files:
        file_name = os.path.basename(file_path)
        is_generated_atmos = file_name.lower().endswith((".atmos", ".atmos.metadata", ".atmos.audio"))
        if is_generated_atmos:
            target = os.path.join(OUTPUT_DIR, file_name)
            if os.path.exists(target):
                os.remove(target)
            os.rename(file_path, target)
            print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} Atmos file moved to {os.path.basename(OUTPUT_DIR)}/{file_name}")
            if file_name.lower().endswith(".atmos"):
                decoded_atmos_file = file_name
        else:
            print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} Non-Atmos file left in place: {file_name}")

    if decoded_atmos_file is not None:
        full_path = os.path.join(OUTPUT_DIR, decoded_atmos_file)
        if os.path.exists(full_path):
            success = transform_atmos_file_inplace(full_path, args.warp_mode)

            if success:
                print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} The Atmos file was successfully transformed.")
            else:
                print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} No changes were made to the Atmos file.")
        else:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Main .atmos file not found at expected path: {full_path}")
            sys.exit(1)
    else:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} No main .atmos file found after conversion.")
        sys.exit(1)

    # -------------------- Settings Info -------------------- #
    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Selected TrueHD Atmos settings:")
    print(f"{Fore.CYAN}{'Dialogue Intelligence':25} → {args.dialogue_intelligence}{Style.RESET_ALL}")
    drc_profile = "film_light" if args.drc == "none" else args.drc
    print(f"{Fore.CYAN}{'DRC profile':25} → {drc_profile}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'Spatial Clusters':25} → {args.spatial_clusters}{Style.RESET_ALL}")

    # -------------------- Create XML -------------------- #
    decoded_mp4_file_mlp = "mlp_encode_atmos_7_1.mlp"
    xml_mlp_7_1 = "mlp_encode_atmos_7_1.xml"
    cleanup_targets.append(xml_mlp_7_1)

    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Creating Atmos 7.1 XML...")
    create_xml_mlp_atmos(OUTPUT_DIR,
                         decoded_atmos_file,
                         decoded_mp4_file_mlp,
                         xml_mlp_7_1,
                         drc_profile,
                         args.dialogue_intelligence,
                         args.spatial_clusters)

    # -------------------- Run DEE -------------------- #
    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Starting MLP Atmos 7.1 encoding...")
    run_dee(xml_mlp_7_1, tools_paths["dee"], -31)

    # -------------------- Rename MLP -------------------- #
    final_mlp = os.path.join(OUTPUT_DIR, f"{base_name}_atmos_7_1.mlp")
    safe_rename(os.path.join(OUTPUT_DIR, decoded_mp4_file_mlp), final_mlp)
    print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} Final MLP saved as {os.path.basename(final_mlp)}")

    # -------------------- Cleanup temporary files -------------------- #
    remove_files(
        OUTPUT_DIR,
        (
            ".atmos",
            ".atmos.metadata",
            ".atmos.audio",
            f"{decoded_mp4_file_mlp}.log",
            f"{decoded_mp4_file_mlp}.mll",
            *cleanup_targets
        )
    )

else:
    input_path_abs = os.path.abspath(args.input)
    input_name = os.path.basename(input_path_abs)

    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Input: {input_name}")

    input_is_folder = os.path.isdir(input_path_abs)
    atmos_or_wav_files = []

    if input_is_folder:
        for f in os.listdir(input_path_abs):
            f_lower = f.lower()
            if f_lower.endswith((".wav", ".atmos", ".atmos.metadata", ".atmos.audio")):
                atmos_or_wav_files.append(os.path.join(input_path_abs, f))
        if not atmos_or_wav_files:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} No WAV or Atmos files found in folder: {input_name}")
            sys.exit(1)
    else:
        if not input_name.lower().endswith((".thd", ".mlp")):
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Unsupported file type: {input_name}")
            sys.exit(1)
        atmos_or_wav_files.append(input_path_abs) 
    check_same_disk(input_path_abs, OUTPUT_DIR)

    # -------------------- Analyze Stream -------------------- #
    atmos_flag = None
    last_presentation_num = None
    last_dialogue_level = None

    if not input_is_folder and any(f.lower().endswith(".atmos") for f in atmos_or_wav_files) == False:
        print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Analyzing TrueHD stream...")
        try:
            result = subprocess.run([tools_paths["truehdd"], "info", input_path_abs],
                                    capture_output=True, text=True, check=True)
            lines = result.stdout.splitlines()

            for line in lines:
                if "Dolby Atmos" in line:
                    atmos_flag = line.split()[-1].lower()
                    break

            current_presentation = None
            for i, line in enumerate(lines):
                if line.strip().startswith("Presentation "):
                    try:
                        current_presentation = int(line.strip().split()[1])
                    except:
                        continue
                if "Dialogue Level" in line and current_presentation is not None and not args.disable_dbfs:
                    last_presentation_num = current_presentation
                    try:
                        parts = line.split()
                        level_value = int(parts[-2])
                        if level_value < -31:
                            level_value = -31
                        last_dialogue_level = str(level_value)
                    except:
                        last_dialogue_level = 0

            if args.disable_dbfs:
                last_dialogue_level = 0

        except subprocess.CalledProcessError as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Info command failed: {e}")
            sys.exit(1)
    else:
        atmos_flag = "true" if any(f.lower().endswith(".atmos") for f in atmos_or_wav_files) else "false"
        last_dialogue_level = "-31"

    # -------------------- Settings -------------------- #
    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Selected audio settings:")

    if atmos_flag == "true":
        if args.atmos_mode in ["5.1", "both"]:
            print(f"{Fore.CYAN}{'Atmos 5.1 bitrate':25} → {args.bitrate_atmos_5_1} kbps{Style.RESET_ALL}")
        if args.atmos_mode in ["7.1", "both"]:
            print(f"{Fore.CYAN}{'Atmos 7.1 bitrate':25} → {args.bitrate_atmos_7_1} kbps{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'Dialogue Level':25} → {last_dialogue_level} dB{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'Dialogue Intelligence':25} → {args.dialogue_intelligence}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'DRC profile':25} → {args.drc}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'Preferred Downmix Mode':25} → {args.preferred_downmix_mode}{Style.RESET_ALL}")
        if last_presentation_num:
            print(f"{Fore.CYAN}{'Last Presentation':25} → {last_presentation_num}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'Warp mode':25} → {args.warp_mode}{Style.RESET_ALL}")

    else:
        print(f"{Fore.CYAN}{'Dialogue Level':25} → {last_dialogue_level} dB{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'Dialogue Intelligence':25} → {args.dialogue_intelligence}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'DDP 5.1 bitrate':25} → {args.bitrate_ddp} kbps{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'DRC profile':25} → {args.drc}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'Preferred Downmix Mode':25} → {args.preferred_downmix_mode}{Style.RESET_ALL}")
        if last_presentation_num:
            print(f"{Fore.CYAN}{'Last Presentation':25} → {last_presentation_num}{Style.RESET_ALL}")

    # -------------------- Decoding -------------------- #
    if not input_is_folder:
        if atmos_flag == "true":
            decode_cmd = [tools_paths["truehdd"], "decode",
                          "--loglevel", "off",
                          "--progress", input_path_abs,
                          "--output-path", OUTPUT_DIR,
                          "--bed-conform"]
            if args.warp_mode:
                decode_cmd.extend(["--warp-mode", args.warp_mode])
            if last_presentation_num:
                decode_cmd.extend(["--presentation", str(last_presentation_num)])
            print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Starting decoding Atmos...")
            decode_result = subprocess.run(decode_cmd)
            if decode_result.returncode != 0:
                print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Decoding failed.")
                sys.exit(1)
        else:
            decode_cmd = [tools_paths["truehdd"], "decode",
                          "--loglevel", "off",
                          "--progress", input_path_abs,
                          "--format", "w64",
                          "--presentation", str(last_presentation_num),
                          "--output-path", OUTPUT_DIR]
            print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Starting decoding WAV...")
            decode_result = subprocess.run(decode_cmd)
            if decode_result.returncode != 0:
                print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Decoding failed.")
                sys.exit(1)

    # -------------------- File Organization -------------------- #
    decoded_audio_file = None
    decoded_atmos_file = None
    decoded_mp4_file_5_1 = None
    decoded_mp4_file_7_1 = None

    search_dirs = []
    if input_is_folder:
        search_dirs = [input_path_abs, SCRIPT_DIR]
    else:
        search_dirs = [SCRIPT_DIR]

    for search_dir in search_dirs:
        for f in os.listdir(search_dir):
            f_path = os.path.join(search_dir, f)
            f_lower = f.lower()

            if f_lower.endswith((".wav", ".atmos", ".atmos.metadata", ".atmos.audio")):
                if f_lower.endswith(".wav") and decoded_audio_file is None:
                    new_name = "ddp_encode.wav"
                    target = os.path.join(OUTPUT_DIR, new_name)
                    if os.path.exists(target):
                        os.remove(target)
                    os.rename(f_path, target)
                    decoded_audio_file = new_name
                    print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} WAV moved to {os.path.basename(OUTPUT_DIR)}/{new_name}")
                else:
                    target = os.path.join(OUTPUT_DIR, f)
                    if os.path.exists(target):
                        os.remove(target)
                    os.rename(f_path, target)
                    print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} Atmos Moved {f} to {os.path.basename(OUTPUT_DIR)}")

                    if f_lower.endswith(".atmos") and decoded_atmos_file is None:
                        decoded_atmos_file = f
    if decoded_atmos_file is not None:

        success = transform_atmos_file_inplace(os.path.join(OUTPUT_DIR, decoded_atmos_file), args.warp_mode)

        if success:
            print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} The Atmos file was successfully transformed.")
        else:
            print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} No changes were made to the Atmos file.")
    else:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} No main .atmos file found for editing.")
        sys.exit(1)

    # -------------------- Encoding -------------------- #
    base_name = input_name if input_is_folder else os.path.splitext(input_name)[0]

    if atmos_flag == "true":
        if decoded_atmos_file is None:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} No Atmos file found for encoding!")
            sys.exit(1)

        cleanup_targets = []
        common_args = (args.drc,
                       args.dialogue_intelligence,
                       last_dialogue_level,
                       args.preferred_downmix_mode)

        if args.atmos_mode in ["5.1", "both"]:
            decoded_mp4_file_5_1 = "ddp_encode_atmos_5_1.mp4"
            xml_5_1 = "ddp_encode_atmos_5_1.xml"
            cleanup_targets.append(xml_5_1)
            print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Creating Atmos 5.1 XML...")
            create_xml_eac3_atmos(OUTPUT_DIR,
                                  decoded_atmos_file,
                                  decoded_mp4_file_5_1,
                                  args.bitrate_atmos_5_1,
                                  xml_5_1,
                                  *common_args,
                                  use_7_1=False)
            print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Starting Atmos 5.1 encoding...")
            run_dee(xml_5_1, tools_paths["dee"], last_dialogue_level)
            safe_rename(os.path.join(OUTPUT_DIR, decoded_mp4_file_5_1),
                        os.path.join(OUTPUT_DIR, f"{base_name}_atmos_5_1.mp4"))

        if args.atmos_mode in ["7.1", "both"]:
            decoded_mp4_file_7_1 = "ddp_encode_atmos_7_1.mp4"
            xml_7_1 = "ddp_encode_atmos_7_1.xml"
            cleanup_targets.append(xml_7_1)
            print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Creating Atmos 7.1 XML...")
            create_xml_eac3_atmos(OUTPUT_DIR,
                                  decoded_atmos_file,
                                  decoded_mp4_file_7_1,
                                  args.bitrate_atmos_7_1,
                                  xml_7_1,
                                  *common_args,
                                  use_7_1=True,)
            print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Starting Atmos 7.1 encoding...")
            run_dee(xml_7_1, tools_paths["dee"], last_dialogue_level)
            safe_rename(os.path.join(OUTPUT_DIR, decoded_mp4_file_7_1),
                        os.path.join(OUTPUT_DIR, f"{base_name}_atmos_7_1.mp4"))

        remove_files(OUTPUT_DIR, (".atmos", ".atmos.metadata", ".atmos.audio"))
        for x in cleanup_targets:
            os.remove(os.path.join(OUTPUT_DIR, x))

    else:
        if decoded_audio_file is None:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} No WAV file found for encoding!")
            sys.exit(1)

        temp_file = os.path.join(OUTPUT_DIR, f"{decoded_audio_file}_temp.wav")
        run_ffmpeg_with_progress(os.path.join(OUTPUT_DIR, decoded_audio_file),
                                 temp_file, tools_paths["ffmpeg"], tools_paths["ffprobe"])
        os.replace(temp_file, os.path.join(OUTPUT_DIR, decoded_audio_file))

        decoded_mp4_file_5_1 = "ddp_encode_5_1.mp4"
        xml_5_1 = "ddp_encode_5_1.xml"
        print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Creating DDP 5.1 XML...")
        create_xml_eac3(OUTPUT_DIR,
                        decoded_audio_file,
                        decoded_mp4_file_5_1,
                        args.bitrate_ddp,
                        xml_5_1,
                        args.drc,
                        args.dialogue_intelligence,
                        last_dialogue_level,
                        args.preferred_downmix_mode)
        print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Starting DDP 5.1 encoding...")
        run_dee(xml_5_1, tools_paths["dee"], last_dialogue_level)
        safe_rename(os.path.join(OUTPUT_DIR, decoded_mp4_file_5_1),
                    os.path.join(OUTPUT_DIR, f"{base_name}_5_1.mp4"))
        remove_files(OUTPUT_DIR, (".wav",))
        os.remove(os.path.join(OUTPUT_DIR, xml_5_1))