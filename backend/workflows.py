from pathlib import Path
from typing import List, Dict

WORKFLOWS_DIR = Path(__file__).resolve().parent.parent / "workflows"


def list_templates() -> List[Dict[str, str]]:
    templates: List[Dict[str, str]] = []
    for xml in WORKFLOWS_DIR.glob("**/*.xml"):
        templates.append({"id": xml.stem, "name": xml.stem, "path": str(xml)})
    return templates


def get_template(identifier: str | None) -> Dict[str, str] | None:
    if not identifier:
        return None
    for tpl in list_templates():
        if tpl["id"] == identifier or tpl["name"] == identifier:
            return tpl
    return None
