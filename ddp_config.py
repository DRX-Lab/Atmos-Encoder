import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from colorama import Fore, Style, init

init(autoreset=True)

def print_saved_xml(path):
    print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} XML written to: {os.path.basename(path)}")

def prettify(elem):
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def create_xml_5_1_atmos(output_path, atmos_file, mp4_file, data_rate, xml_filename):
    root = ET.Element("job_config")

    # Input
    input_elem = ET.SubElement(root, "input")
    audio_in = ET.SubElement(input_elem, "audio")
    atmos = ET.SubElement(audio_in, "atmos_mezz", version="1")
    ET.SubElement(atmos, "file_name").text = str(atmos_file)
    ET.SubElement(atmos, "timecode_frame_rate").text = "23.976"
    ET.SubElement(atmos, "offset").text = "auto"
    ET.SubElement(atmos, "ffoa").text = "auto"
    storage = ET.SubElement(atmos, "storage")
    local = ET.SubElement(storage, "local")
    ET.SubElement(local, "path").text = str(output_path)

    # Filter
    filter_elem = ET.SubElement(root, "filter")
    audio_filter = ET.SubElement(filter_elem, "audio")
    encode = ET.SubElement(audio_filter, "encode_to_atmos_ddp", version="1")
    loudness = ET.SubElement(encode, "loudness")
    measure = ET.SubElement(loudness, "measure_only")
    ET.SubElement(measure, "metering_mode").text = "1770-4"
    ET.SubElement(measure, "dialogue_intelligence").text = "false"
    ET.SubElement(measure, "speech_threshold").text = str(80)
    ET.SubElement(encode, "data_rate").text = str(data_rate)
    ET.SubElement(encode, "timecode_frame_rate").text = "23.976"
    ET.SubElement(encode, "start").text = "first_frame_of_action"
    ET.SubElement(encode, "end").text = "end_of_file"
    ET.SubElement(encode, "time_base").text = "file_position"
    ET.SubElement(encode, "prepend_silence_duration").text = str(0.0)
    ET.SubElement(encode, "append_silence_duration").text = str(0.0)

    drc = ET.SubElement(encode, "drc")
    ET.SubElement(drc, "line_mode_drc_profile").text = "film_light"
    ET.SubElement(drc, "rf_mode_drc_profile").text = "film_light"

    downmix = ET.SubElement(encode, "downmix")
    ET.SubElement(downmix, "loro_center_mix_level").text = str(0)
    ET.SubElement(downmix, "loro_surround_mix_level").text = str(-1.5)
    ET.SubElement(downmix, "ltrt_center_mix_level").text = str(0)
    ET.SubElement(downmix, "ltrt_surround_mix_level").text = str(-1.5)
    ET.SubElement(downmix, "preferred_downmix_mode").text = "loro"

    trims = ET.SubElement(encode, "custom_trims")
    ET.SubElement(trims, "surround_trim_5_1").text = str(0)
    ET.SubElement(trims, "height_trim_5_1").text = str(-3)

    ET.SubElement(encode, "custom_dialnorm").text = str(0)

    # Output
    output_elem = ET.SubElement(root, "output")
    mp4 = ET.SubElement(output_elem, "mp4", version="1")
    ET.SubElement(mp4, "output_format").text = "mp4"
    ET.SubElement(mp4, "override_frame_rate").text = "no"
    ET.SubElement(mp4, "file_name").text = str(mp4_file)
    storage_out = ET.SubElement(mp4, "storage")
    local_out = ET.SubElement(storage_out, "local")
    ET.SubElement(local_out, "path").text = str(output_path)
    plugin = ET.SubElement(mp4, "plugin")
    ET.SubElement(plugin, "base")

    # Misc
    misc = ET.SubElement(root, "misc")
    temp_dir = ET.SubElement(misc, "temp_dir")
    ET.SubElement(temp_dir, "clean_temp").text = "true"
    ET.SubElement(temp_dir, "path").text = str(output_path)

    # Write XML
    xml_str = prettify(root)
    xml_file_path = os.path.join(output_path, xml_filename)
    with open(xml_file_path, "w", encoding="utf-8") as f:
        f.write(xml_str)

    print_saved_xml(xml_file_path)

def create_xml_7_1_atmos(output_path, atmos_file, mp4_file, data_rate, xml_filename):
    root = ET.Element("job_config")

    # Input
    input_elem = ET.SubElement(root, "input")
    audio_in = ET.SubElement(input_elem, "audio")
    atmos = ET.SubElement(audio_in, "atmos_mezz", version="1")
    ET.SubElement(atmos, "file_name").text = str(atmos_file)
    ET.SubElement(atmos, "timecode_frame_rate").text = "23.976"
    ET.SubElement(atmos, "offset").text = "auto"
    ET.SubElement(atmos, "ffoa").text = "auto"
    storage = ET.SubElement(atmos, "storage")
    local = ET.SubElement(storage, "local")
    ET.SubElement(local, "path").text = str(output_path)

    # Filter
    filter_elem = ET.SubElement(root, "filter")
    audio_filter = ET.SubElement(filter_elem, "audio")
    encode = ET.SubElement(audio_filter, "encode_to_atmos_ddp", version="1")

    loudness = ET.SubElement(encode, "loudness")
    measure = ET.SubElement(loudness, "measure_only")
    ET.SubElement(measure, "metering_mode").text = "1770-4"
    ET.SubElement(measure, "dialogue_intelligence").text = "false"
    ET.SubElement(measure, "speech_threshold").text = str(100)

    ET.SubElement(encode, "data_rate").text = str(data_rate)
    ET.SubElement(encode, "timecode_frame_rate").text = "23.976"
    ET.SubElement(encode, "start").text = "first_frame_of_action"
    ET.SubElement(encode, "end").text = "end_of_file"
    ET.SubElement(encode, "time_base").text = "file_position"
    ET.SubElement(encode, "prepend_silence_duration").text = str(0.0)
    ET.SubElement(encode, "append_silence_duration").text = str(0.0)

    drc = ET.SubElement(encode, "drc")
    ET.SubElement(drc, "line_mode_drc_profile").text = "film_light"
    ET.SubElement(drc, "rf_mode_drc_profile").text = "film_light"

    downmix = ET.SubElement(encode, "downmix")
    ET.SubElement(downmix, "loro_center_mix_level").text = str(0)
    ET.SubElement(downmix, "loro_surround_mix_level").text = str(-1.5)
    ET.SubElement(downmix, "ltrt_center_mix_level").text = str(0)
    ET.SubElement(downmix, "ltrt_surround_mix_level").text = str(-1.5)
    ET.SubElement(downmix, "preferred_downmix_mode").text = "loro"

    trims = ET.SubElement(encode, "custom_trims")
    ET.SubElement(trims, "surround_trim_5_1").text = str(0)
    ET.SubElement(trims, "height_trim_5_1").text = str(-3)

    ET.SubElement(encode, "custom_dialnorm").text = str(0)
    ET.SubElement(encode, "encoding_backend").text = "atmosprocessor"
    ET.SubElement(encode, "encoder_mode").text = "bluray"

    # Output
    output_elem = ET.SubElement(root, "output")
    mp4 = ET.SubElement(output_elem, "mp4", version="1")
    ET.SubElement(mp4, "output_format").text = "mp4"
    ET.SubElement(mp4, "override_frame_rate").text = "no"
    ET.SubElement(mp4, "file_name").text = str(mp4_file)
    storage_out = ET.SubElement(mp4, "storage")
    local_out = ET.SubElement(storage_out, "local")
    ET.SubElement(local_out, "path").text = str(output_path)
    plugin = ET.SubElement(mp4, "plugin")
    ET.SubElement(plugin, "base")

    # Misc
    misc = ET.SubElement(root, "misc")
    temp_dir = ET.SubElement(misc, "temp_dir")
    ET.SubElement(temp_dir, "clean_temp").text = "true"
    ET.SubElement(temp_dir, "path").text = str(output_path)

    # Save XML
    xml_str = prettify(root)
    xml_file_path = os.path.join(output_path, xml_filename)
    with open(xml_file_path, "w", encoding="utf-8") as f:
        f.write(xml_str)

    print_saved_xml(xml_file_path)

def create_xml_5_1(output_path, wav_file, ec3_file, data_rate, xml_filename):
    root = ET.Element("job_config")

    # Input
    input_elem = ET.SubElement(root, "input")
    audio = ET.SubElement(input_elem, "audio")
    wav = ET.SubElement(audio, "wav", version="1")
    ET.SubElement(wav, "file_name").text = str(wav_file)
    ET.SubElement(wav, "timecode_frame_rate").text = "not_indicated"
    ET.SubElement(wav, "offset").text = "auto"
    ET.SubElement(wav, "ffoa").text = "auto"
    storage = ET.SubElement(wav, "storage")
    local = ET.SubElement(storage, "local")
    ET.SubElement(local, "path").text = str(output_path)

    # Filter
    filter_elem = ET.SubElement(root, "filter")
    audio_filter = ET.SubElement(filter_elem, "audio")
    pcm = ET.SubElement(audio_filter, "pcm_to_ddp", version="3")

    # Loudness
    loudness = ET.SubElement(pcm, "loudness")
    measure_only = ET.SubElement(loudness, "measure_only")
    ET.SubElement(measure_only, "metering_mode").text = "1770-3"
    ET.SubElement(measure_only, "dialogue_intelligence").text = "true"
    ET.SubElement(measure_only, "speech_threshold").text = "20"

    # Encoder settings
    ET.SubElement(pcm, "encoder_mode").text = "ddp"
    ET.SubElement(pcm, "bitstream_mode").text = "complete_main"
    ET.SubElement(pcm, "downmix_config").text = "off"
    ET.SubElement(pcm, "data_rate").text = str(data_rate)
    ET.SubElement(pcm, "timecode_frame_rate").text = "not_indicated"
    ET.SubElement(pcm, "start").text = "first_frame_of_action"
    ET.SubElement(pcm, "end").text = "end_of_file"
    ET.SubElement(pcm, "time_base").text = "file_position"
    ET.SubElement(pcm, "prepend_silence_duration").text = "0.0"
    ET.SubElement(pcm, "append_silence_duration").text = "0.0"
    ET.SubElement(pcm, "lfe_on").text = "true"
    ET.SubElement(pcm, "dolby_surround_mode").text = "not_indicated"
    ET.SubElement(pcm, "dolby_surround_ex_mode").text = "no"
    ET.SubElement(pcm, "user_data").text = "-1"

    # DRC
    drc = ET.SubElement(pcm, "drc")
    ET.SubElement(drc, "line_mode_drc_profile").text = "music_light"
    ET.SubElement(drc, "rf_mode_drc_profile").text = "music_light"

    # Extra
    ET.SubElement(pcm, "custom_dialnorm").text = "0"
    ET.SubElement(pcm, "lfe_lowpass_filter").text = "true"
    ET.SubElement(pcm, "surround_90_degree_phase_shift").text = "false"
    ET.SubElement(pcm, "surround_3db_attenuation").text = "false"

    # Downmix
    downmix = ET.SubElement(pcm, "downmix")
    ET.SubElement(downmix, "loro_center_mix_level").text = "-3"
    ET.SubElement(downmix, "loro_surround_mix_level").text = "-3"
    ET.SubElement(downmix, "ltrt_center_mix_level").text = "-3"
    ET.SubElement(downmix, "ltrt_surround_mix_level").text = "-3"
    ET.SubElement(downmix, "preferred_downmix_mode").text = "loro"

    ET.SubElement(pcm, "allow_hybrid_downmix").text = "false"

    # Embedded timecodes
    emb = ET.SubElement(pcm, "embedded_timecodes")
    ET.SubElement(emb, "starting_timecode").text = "off"
    ET.SubElement(emb, "frame_rate").text = "auto"
    # Output
    output_elem = ET.SubElement(root, "output")
    mp4 = ET.SubElement(output_elem, "mp4", version="1")
    ET.SubElement(mp4, "output_format").text = "mp4"
    ET.SubElement(mp4, "override_frame_rate").text = "no"
    ET.SubElement(mp4, "file_name").text = str(ec3_file)
    storage_out = ET.SubElement(mp4, "storage")
    local_out = ET.SubElement(storage_out, "local")
    ET.SubElement(local_out, "path").text = str(output_path)
    plugin = ET.SubElement(mp4, "plugin")
    ET.SubElement(plugin, "base")

    # Misc
    misc = ET.SubElement(root, "misc")
    temp_dir = ET.SubElement(misc, "temp_dir")
    ET.SubElement(temp_dir, "clean_temp").text = "true"
    ET.SubElement(temp_dir, "path").text = str(output_path)

    # Save XML
    xml_str = prettify(root)
    xml_path = os.path.join(output_path, xml_filename)
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(xml_str)

    print_saved_xml(xml_path)