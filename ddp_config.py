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

def create_xml_eac3_atmos(output_path, atmos_file, ec3_file, data_rate, xml_filename,
                          drc_profile, dialogue_intelligence, dialogue_level,
                          preferred_downmix_mode, use_7_1=False):
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
    ET.SubElement(measure, "dialogue_intelligence").text = str(dialogue_intelligence)
    ET.SubElement(measure, "speech_threshold").text = str(15)
    ET.SubElement(encode, "data_rate").text = str(data_rate)
    ET.SubElement(encode, "timecode_frame_rate").text = "23.976"
    ET.SubElement(encode, "start").text = "first_frame_of_action"
    ET.SubElement(encode, "end").text = "end_of_file"
    ET.SubElement(encode, "time_base").text = "file_position"
    ET.SubElement(encode, "prepend_silence_duration").text = str(0.0)
    ET.SubElement(encode, "append_silence_duration").text = str(0.0)

    drc = ET.SubElement(encode, "drc")
    ET.SubElement(drc, "line_mode_drc_profile").text = drc_profile
    ET.SubElement(drc, "rf_mode_drc_profile").text = drc_profile

    downmix = ET.SubElement(encode, "downmix")
    ET.SubElement(downmix, "loro_center_mix_level").text = str("-3")
    ET.SubElement(downmix, "loro_surround_mix_level").text = str("-3")
    ET.SubElement(downmix, "ltrt_center_mix_level").text = str("-3")
    ET.SubElement(downmix, "ltrt_surround_mix_level").text = str("-3")
    ET.SubElement(downmix, "preferred_downmix_mode").text = str(preferred_downmix_mode)

    trims = ET.SubElement(encode, "custom_trims")
    ET.SubElement(trims, "surround_trim_5_1").text = str(0)
    ET.SubElement(trims, "height_trim_5_1").text = str(-3)

    ET.SubElement(encode, "custom_dialnorm").text = str(dialogue_level)
    if use_7_1:
        ET.SubElement(encode, "encoding_backend").text = "atmosprocessor"
        ET.SubElement(encode, "encoder_mode").text = "bluray"

    # Output
    output_elem = ET.SubElement(root, "output")
    ec3 = ET.SubElement(output_elem, "ec3", version="1")
    ET.SubElement(ec3, "file_name").text = str(ec3_file)
    storage_out = ET.SubElement(ec3, "storage")
    local_out = ET.SubElement(storage_out, "local")
    ET.SubElement(local_out, "path").text = str(output_path)

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
