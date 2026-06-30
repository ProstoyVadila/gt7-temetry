import json
from datetime import UTC, datetime
from pathlib import Path

from gt_telem.models.telemetry import Telemetry

from gt7_telemetry.config import (
    GT7_HEARTBEAT_PORT,
    HEARTBEAT,
    LOCAL_TELEMETRY_PORT,
    RecorderConfig,
)


def build_lap_payload(
    config: RecorderConfig,
    recording_lap: int,
    samples: list[dict],
    completion_reason: str,
    finished_telemetry: Telemetry | None = None,
) -> dict:
    metadata = {
        "game": "Gran Turismo 7",
        "ps5_ip": config.ps5_ip,
        "heartbeat": HEARTBEAT.decode("ascii"),
        "heartbeat_port": GT7_HEARTBEAT_PORT,
        "local_telemetry_port": LOCAL_TELEMETRY_PORT,
        "recorded_lap": recording_lap,
        "sample_count": len(samples),
        "started_at_utc": samples[0]["captured_at_utc"],
        "finished_at_utc": datetime.now(UTC).isoformat(),
        "completion_reason": completion_reason,
        "complete_lap": completion_reason == "lap_changed",
    }

    if config.name:
        metadata["name"] = config.name
    if finished_telemetry is not None:
        metadata["next_lap_seen"] = finished_telemetry.current_lap
        metadata["last_lap_time_ms_reported_after_finish"] = finished_telemetry.last_lap_time_ms

    return {
        "metadata": metadata,
        "samples": samples,
    }


def write_lap(output_path: Path, payload: dict) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

