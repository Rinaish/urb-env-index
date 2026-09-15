import json
from pathlib import Path

STATE_FILE = Path(__file__).parent / '.state.json'

def save_state(region) -> None:
    STATE_FILE.write_text(json.dumps({"region": region},  ensure_ascii=False), encoding='utf-8')

def load_region(default: str = "study_area") -> str:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text()).get("region", default)
        except (json.JSONDecodeError, OSError):
            return default
    return default