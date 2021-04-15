# E2NDConverter (ExcelToNetworkDiagramConverter)

Do you need to keep track of all the interfaces that your systems connect to? And also have them available in diagram form? You can use the ExcelToNetworkDiagramConverter (E2NDConverter) to create Scalable Vector Graphics (SVG) files which can be imported directly into Visio and further manipulated directly in Visio as required. This method, of converting an Excel to a Network Diagram can save you hours and hours of work by simply defining in Excel what device and ports you want connected, and having them show up in diagram format! 

As a bonus, you can also keep track of Serial Numbers, IP addresses, device Location and any other asset information that may be specific to your organization, which is built-in to the diagram and Excel file for easy tracking and documentation.

## Usage

```bash
python e2ndconverter.py demo.xlsx demo.dot demo.svg [LR|TB]
```

Most of the above command is self-explanatory. demo.xlsx is the input Excel file which has the connection details. 
See attached example. demo.dot is the Graphviz dot format file, which you can manipulate as required, in case you prefer to work directly with Graphviz, and if you don’t know what Graphviz is, you can simply ignore this file. Demo.svg is the main output of this script, the diagram. The LR option, which is the default, creates diagrams that are vertical and TB option creates diagrams that are horizontal.

## Installation

```bash
$ git clone https://github.com/dukkee/excel-to-network-diagram-converter.git
$ cd excel-to-network-diagram-converter
$ pip install -r requirements.txt
```

## Requirements

Python 2.X/3.X

Converter has a [graphviz](https://graphviz.org/) dependency:
- [Windows](https://forum.graphviz.org/t/new-simplified-installation-procedure-on-windows/224)
- [Linux](https://graphviz.org/download/#linux)
- [Mac](https://graphviz.org/download/#mac)

## Generated webpage

Now with SVG file in the same directory you will get an additional `page.html` file with `static` folder of dependencies. To open this page in your browser without errors, you need to run simple Python or any other web server to serve this page.

To do it with Python you need to open your terminal and make the next commands:

```python
$ cd page/html/file/path
$ python3 -m http.server
```

## Examples

In [examples](https://github.com/dukkee/excel-to-network-diagram-converter/tree/master/examples) directory you will 
find source tables and generated results for the next schemas:
 
![demo-simple](examples/demo-simple/demo-simple.svg)

![demo](examples/demo/demo.svg)
