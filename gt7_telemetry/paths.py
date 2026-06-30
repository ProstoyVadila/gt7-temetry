import re
from datetime import datetime
from pathlib import Path


def filename_prefix(name: str | None) -> str:
    if not name:
        return ""

    prefix = re.sub(r"\s+", "_", name.strip())
    prefix = re.sub(r"[^0-9A-Za-zА-Яа-яЁё_.-]+", "_", prefix)
    prefix = re.sub(r"_+", "_", prefix).strip("_.-")
    if not prefix:
        return ""

    return f"{prefix}_"


def default_output_path(name: str | None = None) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path("laps") / f"{filename_prefix(name)}gt7_lap_{stamp}.json"

