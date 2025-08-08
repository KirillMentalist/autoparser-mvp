import os, json, datetime
from typing import Dict, Any, Tuple, List
from jinja2 import Template

PROMPTS_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../prompts"))
SCHEMAS_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../packages/schemas"))

def _prompt_path(name: str, ext: str) -> str:
    if not name.endswith(ext):
        name = f"{name}{ext}"
    return os.path.join(PROMPTS_BASE, name)

def prompt_path(name: str) -> str:
    return _prompt_path(name, ".md")

def vars_path(name: str) -> str:
    return _prompt_path(name, ".vars.json")

def required_path() -> str:
    return os.path.join(PROMPTS_BASE, "required.json")

def load_prompt(name: str) -> str:
    path = prompt_path(name)
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()

def save_prompt(name: str, content: str) -> None:
    path = prompt_path(name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)

def load_sample_vars(name: str) -> Dict[str, Any]:
    path = vars_path(name)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return {}

def _geodir() -> Dict[str, str]:
    path = os.path.join(SCHEMAS_BASE, "geodir.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return {"92": "Республика Татарстан"}

def default_vars() -> Dict[str, Any]:
    today = datetime.datetime.now().strftime("%d.%m.%Y")
    code = os.getenv("REGION_DEFAULT_CODE", "92")
    geodir = _geodir()
    name = geodir.get(code, "Регион не задан")
    return {
        "TODAY": today,
        "msr_geocde": code,
        "msr_geonme": name,
        "msr_prglvl": "REG",
        "msr_srclnk": "",
        "SOURCE_TEXT": ""
    }

def merge_vars(user_vars: Dict[str, Any], sample_vars: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(defaults)
    merged.update(sample_vars or {})
    merged.update(user_vars or {})
    return merged

def load_required(name: str) -> list:
    path = required_path()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            req = json.load(fh)
            return req.get(name, [])
    return []

def find_missing(name: str, variables: Dict[str, Any]) -> List[str]:
    required = load_required(name)
    return [k for k in required if (k not in variables) or (variables.get(k) in (None, ""))]

def render_prompt(name: str, variables: Dict[str, Any], allow_missing: bool = False) -> Dict[str, Any]:
    # Merge: user > sample > defaults
    merged = merge_vars(variables or {}, load_sample_vars(name), default_vars())
    missing = find_missing(name, merged)
    source = load_prompt(name)
    tpl = Template(source)
    if missing and not allow_missing:
        # Render anyway for preview, but note missing
        rendered = tpl.render(**merged)
        return {"rendered": rendered, "missing": missing, "ok": False}
    rendered = tpl.render(**merged)
    return {"rendered": rendered, "missing": missing, "ok": True}
