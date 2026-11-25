"""Build the four SVG previews from Mermaid nodes, links and layout comments."""
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

DIAGRAMS = Path(__file__).resolve().parents[1] / "diagrams"
INK, MUTED, TEAL = "#173445", "#415d6b", "#0d615c"


def element(parent, tag, **attributes):
    return ET.SubElement(parent, tag, {k.replace("_", "-"): str(v) for k, v in attributes.items()})


def text(svg, x, y, value, size=17, color=INK, anchor="middle", bold=False, halo=False):
    node = element(svg, "text", x=x, y=y, font_size=size, fill=color, text_anchor=anchor,
                   font_weight="bold" if bold else "normal")
    if halo:
        node.attrib.update({"paint-order": "stroke", "stroke": "#fff", "stroke-width": "6",
                            "stroke-linejoin": "round"})
    node.text = value
    if halo:
        element(svg, "text", x=x, y=y, font_size=size, fill=color, text_anchor=anchor,
                font_weight="bold" if bold else "normal").text = value


def draw_node(svg, record):
    name, lines, geometry = record
    kind, x, y, w, h = geometry
    group = element(svg, "g", id=name)
    element(group, "title").text = " · ".join(lines)
    left, top = x - w / 2, y - h / 2
    if kind in {"start", "end"}:
        element(group, "circle", cx=x, cy=y, r=w/2, fill="#fff", stroke=TEAL,
                stroke_width=4 if kind == "end" else 2)
        text(group, x+w/2+11, y+5, lines[0], 15, anchor="start")
        return
    if kind == "gate":
        points = [(x, top), (left+w, y), (x, top+h), (left, y)]
        element(group, "polygon", points=" ".join(f"{a},{b}" for a,b in points),
                fill="#fff1cf", stroke="#95651c", stroke_width=2)
        text(group, x, y+6, "×", 23, "#785010", bold=True)
        text(group, x+23, y-24, lines[0], 15, anchor="start", bold=True, halo=True)
        return
    colors = {"primary": (TEAL, "#084b48"), "external": ("#edf2f6", "#778e9c"),
              "person": ("#263f57", "#173445"), "task": ("#fff", "#63858d")}
    fill, border = colors.get(kind, ("#deefed", "#477a78"))
    element(group, "rect", x=left, y=top, width=w, height=h, rx=12 if kind=="task" else 6,
            fill=fill, stroke=border, stroke_width=1.6)
    for i, line in enumerate(lines):
        dark = kind in {"primary", "person"}
        text(group, x, y+6+(i-(len(lines)-1)/2)*22, line, 18 if i==0 else 15,
             "#fff" if dark else INK, bold=(i==0 and kind!="task"))


def render(path):
    source = path.read_text().splitlines()
    title = json.loads(source[1].split(": ",1)[1])
    areas, nodes, edges, notes = [], [], [], []
    for i, line in enumerate(source):
        if not line.strip().startswith("%% "):
            continue
        tag, data = line.strip()[3:].split(" ", 1)
        data = json.loads(data)
        statement = source[i-1].strip()
        if tag == "canvas":
            width, height, subtitle = data
        elif tag == "area":
            areas.append((statement.split('"')[1], data))
        elif tag == "box":
            name = re.match(r"\w+", statement).group()
            nodes.append((name, statement.split('"')[1].split("<br/>"), data))
        elif tag == "line":
            label = statement.split('"')[1] if '"' in statement else ""
            edges.append((label, *data))
        elif tag == "note":
            notes.append(data)
    svg = ET.Element("svg", {"xmlns":"http://www.w3.org/2000/svg", "width":str(width),
                            "height":str(height), "viewBox":f"0 0 {width} {height}",
                            "font-family":"DejaVu Sans, Arial, sans-serif", "role":"img",
                            "aria-labelledby":"diagram-title"})
    element(svg, "title", id="diagram-title").text = title
    element(svg, "rect", width=width, height=height, fill="#fff")
    text(svg, 36, 39, subtitle, 16, TEAL, anchor="start", bold=True)
    text(svg, 36, 82, title, 31, anchor="start", bold=True)
    for label, (x,y,w,h) in areas:
        element(svg, "rect", x=x,y=y,width=w,height=h,rx=8,fill="#f6f9fa",stroke="#9cb1b8")
        text(svg, x+16, y+26, label, 16, MUTED, anchor="start", bold=True)
    for _, points, _ in edges:
        element(svg, "polyline", points=" ".join(f"{x},{y}" for x,y in points),
                fill="none", stroke=MUTED, stroke_width=2, stroke_linejoin="round")
        (x0,y0),(x,y) = points[-2:]
        length = math.hypot(x-x0,y-y0)
        dx,dy = (x-x0)/length,(y-y0)/length
        head = [(x,y),(x-11*dx-4.3*dy,y-11*dy+4.3*dx),(x-11*dx+4.3*dy,y-11*dy-4.3*dx)]
        element(svg, "polygon", points=" ".join(f"{a},{b}" for a,b in head), fill=MUTED)
    for record in nodes:
        draw_node(svg, record)
    for label, _, at in edges:
        if label and at:
            text(svg, *at, label, 14, MUTED, halo=True)
    for x,y,label in notes:
        text(svg,x,y,label,14,MUTED,anchor="start")
    ET.indent(svg)
    path.with_suffix(".svg").write_bytes(ET.tostring(svg, encoding="utf-8", xml_declaration=True))


if __name__ == "__main__":
    for source_file in sorted(DIAGRAMS.glob("*.mmd")):
        render(source_file)
