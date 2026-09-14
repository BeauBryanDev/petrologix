
import json
import re
from functools import lru_cache
from pathlib import Path

# Representative physical properties of common rock types.

DATA_PATH = Path(__file__).resolve().parent.parent / "utils" / "rock_properties.json"

# Other names people use for a rock in the table.
_ALIASES = {
    "dolostone": "Dolomite",
    "rock salt": "Halite",
    "salt": "Halite",
    "shaly sand": "Sandstone/Shale",
    "shaly sandstone": "Sandstone/Shale",
    "dirty sand": "Sandstone/Shale",
    "dirty sandstone": "Sandstone/Shale",
    "sand/shale": "Sandstone/Shale",
    "crystalline basement": "Basement",
    "basement rock": "Basement",
    "sand": "Sandstone",
}

# Numeric fields only, for comparing many rocks without the prose.
COMPARE_FIELDS = (
    "rock_name", "lithology_class", "density_min_max", "avg_density",
    "resistivity_min_max", "conductivity_min_max", "porosity", "mohs_hardness",
)

# A lookup table, not a model: textbook ranges per rock type, never measurements
# from a well. Rock names follow the lithology model's classes, so any predicted
# class resolves to an entry.

class RockNotFoundError(LookupError):
    pass


def _key(name: str) -> str:
    name = re.sub(r"\s*/\s*", "/", name.strip().lower())
    return re.sub(r"[\s_-]+", " ", name)


@lru_cache(maxsize=1)
def _table() -> dict:
    
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _index() -> dict[str, dict]:
    
    index = {_key(r["rock_name"]): r for r in _table()["rocks"]}
    
    for alias, name in _ALIASES.items():
        
        index.setdefault(_key(alias), index[_key(name)])
        
    return index


def units() -> dict:
    return dict(_table()["units"])


def rock_names() -> list[str]:
    return [r["rock_name"] for r in _table()["rocks"]]


def get_rock_properties(name: str) -> dict:
    """Full record for one rock, matched case-insensitively, by alias or plural."""
    key = _key(name)
    index = _index()
    
    record = index.get(key) or (index.get(key[:-1]) if key.endswith("s") else None)

    if record is None:
        raise RockNotFoundError(f"No rock named {name!r}")

    return dict(record)


def list_rocks(lithology_class: str | None = None) -> list[dict]:
    """Every rock's numeric fields, optionally narrowed to one lithology class.
    Substring match, so "Igneous" also returns Basement ("Igneous/Metamorphic")."""
    rocks = _table()["rocks"]

    if lithology_class:
        
        wanted = lithology_class.strip().lower()
        rocks = [r for r in rocks if wanted in r["lithology_class"].lower()]

    return [{f: r[f] for f in COMPARE_FIELDS} for r in rocks]
