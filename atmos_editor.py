import os
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedSeq

def transform_atmos_file_inplace(file_path, warp_mode="normal"):
    """
    Transforms an Atmos YAML file in place, but only if the scBedConfiguration
    is exactly [0, 1, 2, 3, 6, 7, 4, 5].

    Changes applied:
    - scBedConfiguration -> [3]
    - creationToolVersion -> "0.4.0"
    - warpMode -> value passed from main.py
    - bedInstances channels -> only LFE
    - objects -> IDs 10 to 20
    """
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 4096
    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.load(f)
    presentations = data.get("presentations", [])
    if not presentations:
        return False
    presentation = presentations[0]
    sc_config = presentation.get("scBedConfiguration", [])
    if sc_config == [0, 1, 2, 3, 6, 7, 4, 5]:
        seq = CommentedSeq([3])
        seq.fa.set_flow_style()
        presentation["scBedConfiguration"] = seq
        presentation["creationTool"] = "DRX-Lab"
        presentation["creationToolVersion"] = "0.4.0"
        presentation["warpMode"] = warp_mode
        if "bedInstances" in presentation and len(presentation["bedInstances"]) > 0:
            presentation["bedInstances"][0]["channels"] = [{"channel": "LFE", "ID": 3}]
        presentation["objects"] = [{"ID": i} for i in range(10, 21)]
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f)
        return True
    else:
        return False