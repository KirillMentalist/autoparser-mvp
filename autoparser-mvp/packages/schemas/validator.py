import json, os
from jsonschema import validate, Draft202012Validator
from jsonschema.exceptions import ValidationError

SCHEMAS_DIR = os.path.dirname(__file__)

def _load(name: str) -> dict:
    path = os.path.join(SCHEMAS_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def validate_stage(stage: str, data: dict) -> tuple[bool, str | None]:
    mapping = {
        "E1": "e1.json", "E2": "e2.json", "E3": "e3.json",
        "E4": "e4.json", "E5": "e5.json", "E6": "e6.json", "E7": "e7.json"
    }
    if stage not in mapping:
        return True, None
    schema = _load(mapping[stage])
    try:
        Draft202012Validator(schema).validate(data)
        return True, None
    except ValidationError as e:
        return False, str(e)
