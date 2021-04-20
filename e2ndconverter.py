import os
import re
import sys
from collections import defaultdict
from distutils.dir_util import copy_tree

import pandas as pd
from datauri import DataURI
from jinja2 import Template
from graphviz import Source


__all__ = ["convert"]


CONNECTION_COLOR_MAPPING = {
    "FC 6G": "b6f542",
    "FC 16G": "42d7f5",
    "FC 32G": "f542d4",
    "QSFP-40/100-SRBD": "FF0000",
    "QSFP-40/100G-SRBD": "FF0000",
    "QSFP-40/100-SRBD": "FF0000",
    "QSFP-40G-SR-BD": "FF0000",
    "QSFP-100G-SR4": "26fc4a",
    "100GE FG-TRAN-QSFP28-SR4": "26fc4a",
    "100G Cisco SR": "26fc4a",
    "QSFP-100G-SR4-S": "ff0033",
    "QSFP-100G-LR4-S": "FFC000",
    "QSFP-100G-LR4": "FFC000",
    "100G Cisco LR": "FFC000",
    "QSFP-40G-LR4": "933A32",
    "QSFP-40G-SR4": "4BACC6",
    "40G Cisco SR": "4BACC6",
    "QSFP-40G-SR4-S": "4BACC6",
    "QSFP-40G-SR4-S+": "4BACC6",
    "40GE FN-TRAN-QSFP+SR": "4BACC6",
    "FET10G": "0000FF",
    "SFP-10G-SR": "000000",
    "Cisco 10G-SR": "000000",
    "10G Cisco SR": "000000",
    "GX-MM": "FF33E6",
    "GLC-SX-MM": "FF33E6",
    "569023 - 1G - SR": "FF33E6",
    "SFP-10/25G-CRS-S": "FF5733",
    "10/25GE FN-TRAN-SFP28-SR": "FF5733",
    "10GE FG-TRAN-SFP+SR": "000000",
    "FG-TRAN-SFP+SR": "000000",
    "GLC-SX-MMD": "FF33E6",
    "Cisco GLC-T": "7030A0",
    "1G RJ45": "7030A0",
    "1GE RJ45": "7030A0",
    " 1GE RJ45": "7030A0",
    "1G 1GE RJ45": "7030A0",
    "RJ45": "7030A0",
    "DB9-RJ45": "7030A0",
    "DB9-1GE RJ45": "7030A0",
    "GLC-T": "7030A0",
    "GLC-TE": "7030A0",
    "QSFP-100G-SR4-S+": "ff0033",
    "Cisco GLC-SX-MM": "FF33E6",
    "1GE SR": "FF33E6",
    "(CVR)SFP-10G-SR": "000000",
    "": "799540",
    "Other use NOTES": "799540",
}
INPUT_ERROR_MESSAGE = "You must determine a correct input file path, output file path and svg output file path!"
RAW_TEMPLATE = """
digraph {

label=<
     <table border="0" cellborder="1" cellspacing="0">
        <tr><td bgcolor="#FFFFFFF"><font color="#000000" point-size="16" ><b>Connection Types</b></font></td></tr>
        <tr><td bgcolor="#FFFFFFF"><font color="#26fc4a" point-size="14" ><b>100G-SR4</b></font></td></tr>
        <tr><td bgcolor="#FFFFFFF"><font color="#FFC000" point-size="14" ><b>100G-LR4</b></font></td></tr>
        <tr><td bgcolor="#FFFFFFF"><font color="#0000FF" point-size="14" ><b>FET10G</b></font></td></tr>
        <tr><td bgcolor="#FFFFFFF"><font color="#FF0000" point-size="14" ><b>40/100-SRBD</b></font></td></tr>
        <tr><td bgcolor="#FFFFFFF"><font color="#4BACC6" point-size="14" ><b>40G-SR4</b></font></td></tr>
        <tr><td bgcolor="#FFFFFFF"><font color="#933A32" point-size="14" ><b>40G-LR4</b></font></td></tr>
        <tr><td bgcolor="#FFFFFFF"><font color="#FF5733" point-size="14" ><b>10/25G SR</b></font></td></tr>
        <tr><td bgcolor="#FFFFFFF"><font color="#000000" point-size="14" ><b>10G-SR</b></font></td></tr>
        <tr><td bgcolor="#FFFFFFF"><font color="#FF33E6" point-size="14" ><b>SX-MM</b></font></td></tr>
        <tr><td bgcolor="#FFFFFFF"><font color="#7030A0" point-size="14" ><b>GLC-TE/UTP/RJ45</b></font></td></tr>
        <tr><td bgcolor="#FFFFFFF"><font color="#b6f542" point-size="14" ><b>FC 8G</b></font></td></tr>
        <tr><td bgcolor="#FFFFFFF"><font color="#42d7f5" point-size="14" ><b>FC 16G</b></font></td></tr>
        <tr><td bgcolor="#FFFFFFF"><font color="#f542d4" point-size="14" ><b>FC 32G</b></font></td></tr>
        <tr><td bgcolor="#FFFFFFF"><font color="#799540" point-size="14" ><b>Other</b></font></td></tr>


     </table>>

    graph [splines=curved rankdir = "{{ rankdir }}"];
    node [shape = polygon, sides = 7, width = 7, fontsize = 14, color = "#000000" ];

{% for item in dots %}
subgraph cluster_{{ item["cluster"] }} {
    {% for module, port in item["modules"] -%}
    "{{ item["device_name"] }}.{{ module }}/{{ port }}" [label="{{ module }}/{{ port }}"];
    {% endfor -%}
    label = <{{ item["device_name"] }} <br/> {{ item["model"] }} <br/> {{ item["asset"] }} <br/> {{ item["serial"] }} <br/> {{ item["row"] }}-{{ item["rack"] }} {{ item["rack-u"] }} <br/> {{ item["ip"] }}>;
  }
{% endfor %}

{% for item in connections -%}
{"{{ item["start_name"] }}" -> "{{ item["end_name"] }}" [penwidth=2.5, color="#{{ item["color"] }}"]} #ConnectionType {{ item[
"type"] }} = {{ item["color"] }}
{% endfor %}


}
"""


def format_device_name(name):
    return re.sub("[^a-zA-Z0-9 ]", "", name).replace(" ", "_")


def format_port(port):
    if isinstance(port, float):
        return int(port)

    return port


format_module = format_port


def get_modules(frame):
    modules = defaultdict(list)

    for _, line in frame[frame.Action == "Connect"].iterrows():
        modules[line["Device Name"]].append((format_module(line["Module"]), format_port(line["Port"])))
        modules[line["Device Name.1"]].append((format_module(line["Module.1"]), format_port(line["Port.1"])))

    return modules


def get_items(frame):
    data = []
    added_devices = set()
    modules = get_modules(frame)

    for _, line in frame[frame.Action == "Rack"].iterrows():
        added_devices.add(line["Device Name"])
        data.append({
            "device_name": line["Device Name"],
            "cluster": format_device_name(line["Device Name"]),
            "asset": line["Asset Tag #"],
            "model": line["Make/Model"],
            "serial": line["Serial #"],
            "row": line["Row"],
            "rack": line["Rack"],
            "rack-u": line["U"],
            "ip": line.get("IP Address", ""),
            "modules": modules[line["Device Name"]]
        })

    # Some production sources don't contain the rack statement for many devices
    # therefore we need to check the connect statements too
    for _, line in frame[frame.Action == "Connect"].iterrows():
        if line["Device Name"] not in added_devices:
            added_devices.add(line["Device Name"])
            data.append({
                "device_name": line["Device Name"],
                "cluster": format_device_name(line["Device Name"]),
                "asset": line["Asset Tag #"],
                "model": line["Make/Model"],
                "serial": line["Serial #"],
                "row": line["Row"],
                "rack": line["Rack"],
                "rack-u": line["U"],
                "ip": line.get("IP Address", ""),
                "modules": modules[line["Device Name"]]
            })
        if line["Device Name.1"] not in added_devices:
            added_devices.add(line["Device Name.1"])
            data.append({
                "device_name": line["Device Name.1"],
                "cluster": format_device_name(line["Device Name.1"]),
                "asset": line["Asset Tag #.1"],
                "model": line["Make/Model.1"],
                "serial": line["Serial #.1"],
                "row": line["Row.1"],
                "rack": line["Rack.1"],
                "rack-u": line["U.1"],
                "ip": line.get("IP Address", ""),
                "modules": modules[line["Device Name.1"]]
            })

    return data


def get_connections(frame):
    connections = []

    for _, line in frame[frame.Action == "Connect"].iterrows():
        connections.append({
            "start_name": f'{line["Device Name"]}.{format_module(line["Module"])}/{format_port(line["Port"])}',
            "end_name": f'{line["Device Name.1"]}.{format_module(line["Module.1"])}/{format_port(line["Port.1"])}',
            "type": line.get("SFP Type", "Other").strip(),
            "color": CONNECTION_COLOR_MAPPING.get(line.get("SFP Type", "").strip(), CONNECTION_COLOR_MAPPING[""]),
        })

    return connections


def convert(input_path, output_path, output_svg_path, rankdir):
    compiled_template = Template(RAW_TEMPLATE)
    frame = pd.read_excel(input_path)
    frame = frame.where(pd.notnull(frame), "")

    output = compiled_template.render(dots=get_items(frame), connections=get_connections(frame), rankdir=rankdir)

    with open(output_path, 'w') as fp:
        fp.write(output)

    Source(output).render(output_svg_path, format="svg")


def main():
    if len(sys.argv) < 2 or not os.path.exists(sys.argv[1]):
        raise ValueError(INPUT_ERROR_MESSAGE)

    input_path = sys.argv[1]
    input_name = os.path.basename(input_path).rsplit(".", 1)[0]
    input_dirname = os.path.dirname(input_path)

    try:
        output_path = sys.argv[2]
    except:
        output_path = os.path.join(input_dirname, input_name + ".dot")

    try:
        output_svg_path = sys.argv[3][:-4] if sys.argv[3].endswith(".svg") else sys.argv[3]
    except:
        output_svg_path = os.path.join(input_dirname, input_name)

    output_dirname = os.path.dirname(output_path)
    output_svg_dirname = os.path.dirname(output_svg_path)

    if len(sys.argv) == 5 and sys.argv[4] not in ("LR", "TB"):
        raise ValueError("Rankdir must be 'LR' or 'TB'")

    rankdir = sys.argv[4] if len(sys.argv) == 5 else "LR"

    if output_dirname and not os.path.exists(output_dirname):
        raise ValueError(INPUT_ERROR_MESSAGE)
    if output_svg_dirname and not os.path.exists(output_svg_dirname):
        raise ValueError(INPUT_ERROR_MESSAGE)

    convert(input_path, output_path, output_svg_path, rankdir=rankdir)

    with open("static/template.html") as fp:
        template = fp.read().replace("{{ svg_file }}", str(DataURI.from_file(output_svg_path + ".svg")))

    with open(os.path.join(output_svg_dirname, input_name + ".html"), "w") as fp:
        fp.write(template)

    result_static_path = os.path.join(output_svg_dirname, "static")

    if output_svg_dirname.replace(".", ""):
        copy_tree("static", result_static_path)
        os.remove(os.path.join(result_static_path, "template.html"))


if __name__ == '__main__':
    main()
