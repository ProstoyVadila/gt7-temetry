from dataclasses import dataclass
from pathlib import Path

DEFAULT_PS5_IP = "192.168.10.59"
GT7_HEARTBEAT_PORT = 33739
LOCAL_TELEMETRY_PORT = 33740
HEARTBEAT = b"A"


@dataclass(frozen=True)
class RecorderConfig:
    ps5_ip: str = DEFAULT_PS5_IP
    output: Path | None = None
    include_current: bool = False
    replay: bool = False
    save_partial: bool = False
    include_raw: bool = False
    name: str | None = None
    max_wait_seconds: int = 900

