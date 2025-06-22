from __future__ import annotations
import inspect
import xml.etree.ElementTree as ET
from typing import Any, Callable, Dict, Iterable, List

EXT_NS = "http://your-company.com/bpmn-ext"


def bpmn_op(
    name: str,
    inputs: Dict[str, type] | None = None,
    outputs: Dict[str, type] | None = None
):
    """Decorator to mark a function as a BPMN operation."""

    def decorator(func: Callable):
        func._bpmn_op = {
            "name": name,
            "inputs": list(inputs.keys()) if inputs else [],
            "outputs": list(outputs.keys()) if outputs else [],
        }
        return func

    return decorator


def collect_operations(module: Any) -> List[Dict[str, Any]]:
    """Collect decorated operations from a module."""
    ops = []
    for _, obj in inspect.getmembers(module, inspect.isfunction):
        meta = getattr(obj, "_bpmn_op", None)
        if meta:
            ops.append(meta)
    return ops


def _add_enums(parent: ET.Element, values: Iterable[str]):
    for val in sorted(set(values)):
        ET.SubElement(parent, "xs:enumeration", value=val)


def generate_xsd(ops: List[Dict[str, Any]]) -> str:
    """Generate extension XSD from operation registry."""
    xs = "http://www.w3.org/2001/XMLSchema"
    schema = ET.Element("xs:schema", attrib={
        "xmlns:xs": xs,
        "targetNamespace": EXT_NS,
        "xmlns": EXT_NS,
        "elementFormDefault": "qualified",
    })

    # operation element
    op_el = ET.SubElement(schema, "xs:element", name="operation")
    ct = ET.SubElement(op_el, "xs:complexType")
    seq = ET.SubElement(ct, "xs:sequence")
    ET.SubElement(seq, "xs:element", name="in", minOccurs="0", maxOccurs="unbounded", type="inType")
    ET.SubElement(seq, "xs:element", name="out", minOccurs="0", maxOccurs="unbounded", type="outType")

    attr = ET.SubElement(ct, "xs:attribute", name="name", use="required")
    st = ET.SubElement(attr, "xs:simpleType")
    rest = ET.SubElement(st, "xs:restriction", base="xs:string")
    _add_enums(rest, [op["name"] for op in ops])

    # inType
    in_type = ET.SubElement(schema, "xs:complexType", name="inType")
    attr_in = ET.SubElement(in_type, "xs:attribute", name="name", use="required")
    st_in = ET.SubElement(attr_in, "xs:simpleType")
    rest_in = ET.SubElement(st_in, "xs:restriction", base="xs:string")
    _add_enums(rest_in, [inp for op in ops for inp in op["inputs"]])

    # outType
    out_type = ET.SubElement(schema, "xs:complexType", name="outType")
    attr_out = ET.SubElement(out_type, "xs:attribute", name="name", use="required")
    st_out = ET.SubElement(attr_out, "xs:simpleType")
    rest_out = ET.SubElement(st_out, "xs:restriction", base="xs:string")
    _add_enums(rest_out, [out for op in ops for out in op["outputs"]])

    xml_str = ET.tostring(schema, encoding="unicode")
    try:
        import xml.dom.minidom as minidom
        xml_str = minidom.parseString(xml_str).toprettyxml(indent="  ")
    except Exception:
        pass
    return xml_str


def validate_operations(xml_path: str, ops: List[Dict[str, Any]]) -> None:
    """Validate extension operation usage in BPMN file."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    ns = {
        "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
        "ext": EXT_NS,
    }
    registry = {op["name"]: op for op in ops}
    for st in root.findall(".//bpmn:serviceTask", ns):
        op_el = st.find("bpmn:extensionElements/ext:operation", ns)
        if op_el is None:
            continue
        name = op_el.attrib.get("name")
        if name not in registry:
            raise ValueError(f"Unknown operation '{name}' in serviceTask {st.attrib.get('id')}")
        op_info = registry[name]
        ins = [c.attrib.get("name") for c in op_el.findall("ext:in", ns)]
        outs = [c.attrib.get("name") for c in op_el.findall("ext:out", ns)]
        if sorted(ins) != sorted(op_info["inputs"]):
            raise ValueError(f"Inputs for operation '{name}' do not match registry")
        if sorted(outs) != sorted(op_info["outputs"]):
            raise ValueError(f"Outputs for operation '{name}' do not match registry")
