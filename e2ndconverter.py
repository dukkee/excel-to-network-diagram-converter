import os
import re
import sys
from collections import defaultdict

import pandas as pd
from jinja2 import Template
from graphviz import Source


__all__ = ["convert"]


CONNECTION_COLOR_MAPPING = {
    "FC 16G": "ff0000",
    "FC 32G": "1f4800",
    "QSFP-40/100-SRBD": "026ff0",
    "QSFP-40/100G-SRBD": "026ff0",
    " QSFP-40/100-SRBD": "026ff0",
    "QSFP-100G-SR4": "ff00FF",
    "QSFP-40G-SR4": "A52A2A",
    "FET10G": "0000FF",
    "SFP-10G-SR": "FFA500",
    "GX-MM": "800000",
    "SFP-10/25G-CRS-S": "FF5733",
    "Cisco GLC-T": "33ACFF",
    "QSFP-100G-SR4-S+": "9C33FF",
    "Cisco GLC-SX-MM": "FF33E6",
    "": "FF3352",
    "Other use NOTES": "FF3352",
}
INPUT_ERROR_MESSAGE = "You must determine a correct input file path, output file path and svg output file path!"
RAW_TEMPLATE = """
graph {

label=<
     <table border="0" cellborder="1" cellspacing="0">
       <tr><td bgcolor="#FFFFFFF"><font color="#000000" point-size="8" ><b>Connection Types</b></font></td></tr>
       <tr><td bgcolor="#FFFFFFF"><font color="#ff0000" point-size="8" ><b>FC 16G</b></font></td></tr>
       <tr><td bgcolor="#FFFFFFF"><font color="#1f4800" point-size="8" ><b>FC 32G</b></font></td></tr>
       <tr><td bgcolor="#FFFFFFF"><font color="#026ff0" point-size="8" ><b>SFP-40/100-SRBD</b></font></td></tr>
       <tr><td bgcolor="#FFFFFFF"><font color="#A52A2A" point-size="8" ><b>QSFP-40G-SR4</b></font></td></tr>
       <tr><td bgcolor="#FFFFFFF"><font color="#ff00FF" point-size="8" ><b>QSFP-100G-SR4</b></font></td></tr>
       <tr><td bgcolor="#FFFFFFF"><font color="#0000FF" point-size="8" ><b>FET10G</b></font></td></tr>
       <tr><td bgcolor="#FFFFFFF"><font color="#FFA500" point-size="8" ><b>SFP-10G-SR</b></font></td></tr>
       <tr><td bgcolor="#FFFFFFF"><font color="#800000" point-size="8" ><b>GX-MM</b></font></td></tr>
       <tr><td bgcolor="#FFFFFFF"><font color="#33ACFF" point-size="8" ><b>GLC-T</b></font></td></tr>
       <tr><td bgcolor="#FFFFFFF"><font color="#9C33FF" point-size="8" ><b>QSFP-100G-SR4-S+</b></font></td></tr>
       <tr><td bgcolor="#FFFFFFF"><font color="#FF33E6" point-size="8" ><b>GLC-SX-MM</b></font></td></tr>
       
     </table>>

    graph [splines=curved rankdir = "{{ rankdir }}"];
    node [shape = polygon, sides = 7, width = 4, fontsize = 14, color = "#000000" ];

{% for item in dots %}
subgraph cluster_{{ item["cluster"] }} {
    {% for module, port in item["modules"] -%}
    "{{ item["device_name"] }}.{{ module }}/{{ port }}" [label="{{ module }}/{{ port }}"];
    {% endfor -%}
    label = <{{ item["device_name"] }} <br/> {{ item["model"] }} <br/> {{ item["asset"] }} <br/> {{ item["serial"] }} <br/> {{ item["rack"] }} {{ item["rack-u"] }} <br/> {{ item["ip"] }}>;
  }
{% endfor %}

{% for item in connections -%}
{"{{ item["start_name"] }}" -- "{{ item["end_name"] }}" [color="#{{ item["color"] }}"]} #ConnectionType {{ item[
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
            "type": line["SFP Type"],
            "color": CONNECTION_COLOR_MAPPING[line["SFP Type"]],
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
    if len(sys.argv) < 4 or not os.path.exists(sys.argv[1]):
        raise ValueError(INPUT_ERROR_MESSAGE)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    output_svg_path = sys.argv[3][:-4] if sys.argv[3].endswith(".svg") else sys.argv[3]
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


if __name__ == '__main__':
    main()
