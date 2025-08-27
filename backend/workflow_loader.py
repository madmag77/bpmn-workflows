from pathlib import Path
from typing import List, Dict

WORKFLOWS_DIR = Path(__file__).resolve().parent.parent / "workflows"


def list_templates() -> List[Dict[str, str]]:
    templates: List[Dict[str, str]] = []
    for awsl in WORKFLOWS_DIR.glob("**/*.awsl"):
        templates.append({"id": awsl.stem, "name": awsl.stem, "path": str(awsl)})
    return templates


def get_template(identifier: str | None) -> Dict[str, str] | None:
    if not identifier:
        return None
    for tpl in list_templates():
        if tpl["id"] == identifier or tpl["name"] == identifier:
            return tpl
    return None
