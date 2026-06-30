import argparse
import json
import socket
import time
from dataclasses import fields
from datetime import UTC, datetime
from pathlib import Path

from gt_telem.models.telemetry import Telemetry
from gt_telem.turismo_client import TurismoClient

DEFAULT_PS5_IP = "192.168.10.59"
GT7_HEARTBEAT_PORT = 33739
LOCAL_TELEMETRY_PORT = 33740
HEARTBEAT = b"A"
RAW_TELEMETRY_FIELDS = [field.name for field in fields(Telemetry)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record one Gran Turismo 7 lap telemetry stream to a JSON file."
    )
    parser.add_argument("--ps5-ip", default=DEFAULT_PS5_IP, help="PS5 IPv4 address.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON path. Defaults to laps/gt7_lap_<timestamp>.json.",
    )
    parser.add_argument(
        "--include-current",
        action="store_true",
        help="Start recording from the current lap immediately. By default, wait for the next lap.",
    )
    parser.add_argument(
        "--max-wait-seconds",
        type=int,
        default=900,
        help="Stop waiting if no full lap is captured within this many seconds.",
    )
    return parser.parse_args()


class TelemetryDecoder:
    def __init__(self, ps5_ip: str):
        self.client = TurismoClient(
            is_gt7=True,
            ps_ip=ps5_ip,
            heartbeat_type=HEARTBEAT.decode("ascii"),
            max_callback_workers=1,
        )

    def decode(self, data: bytes) -> Telemetry | None:
        self.client._handle_data(data)
        return self.client.telemetry


def default_output_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path("laps") / f"gt7_lap_{stamp}.json"


def telemetry_sample(t: Telemetry, capture_started_at: float) -> dict:
    return {
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "elapsed_capture_s": round(time.monotonic() - capture_started_at, 6),
        "raw": {field_name: getattr(t, field_name) for field_name in RAW_TELEMETRY_FIELDS},
        "packet_id": t.packet_id,
        "current_lap": t.current_lap,
        "total_laps": t.total_laps,
        "best_lap_time_ms": t.best_lap_time_ms,
        "last_lap_time_ms": t.last_lap_time_ms,
        "time_of_day_ms": t.time_of_day_ms,
        "track_id": t.track_id,
        "car_code": t.car_code,
        "speed_mps": t.speed_mps,
        "speed_kph": t.speed_kph,
        "engine_rpm": t.engine_rpm,
        "current_gear": t.current_gear,
        "suggested_gear": t.suggested_gear,
        "throttle": t.throttle,
        "brake": t.brake,
        "fuel_level": t.fuel_level,
        "fuel_capacity": t.fuel_capacity,
        "boost_pressure": t.boost_pressure,
        "oil_pressure": t.oil_pressure,
        "water_temp": t.water_temp,
        "oil_temp": t.oil_temp,
        "position": {
            "x": t.position_x,
            "y": t.position_y,
            "z": t.position_z,
        },
        "velocity": {
            "x": t.velocity_x,
            "y": t.velocity_y,
            "z": t.velocity_z,
        },
        "rotation": {
            "x": t.rotation_x,
            "y": t.rotation_y,
            "z": t.rotation_z,
            "orientation": t.orientation,
        },
        "angular_velocity": {
            "x": t.ang_vel_x,
            "y": t.ang_vel_y,
            "z": t.ang_vel_z,
        },
        "tires": {
            "temperature": {
                "fl": t.tire_fl_temp,
                "fr": t.tire_fr_temp,
                "rl": t.tire_rl_temp,
                "rr": t.tire_rr_temp,
            },
            "wheel_rps": {
                "fl": t.wheel_fl_rps,
                "fr": t.wheel_fr_rps,
                "rl": t.wheel_rl_rps,
                "rr": t.wheel_rr_rps,
            },
            "radius": {
                "fl": t.tire_fl_radius,
                "fr": t.tire_fr_radius,
                "rl": t.tire_rl_radius,
                "rr": t.tire_rr_radius,
            },
            "suspension_height": {
                "fl": t.tire_fl_sus_height,
                "fr": t.tire_fr_sus_height,
                "rl": t.tire_rl_sus_height,
                "rr": t.tire_rr_sus_height,
            },
        },
        "state": {
            "cars_on_track": t.cars_on_track,
            "is_paused": t.is_paused,
            "is_loading": t.is_loading,
            "in_gear": t.in_gear,
            "hand_brake_active": t.hand_brake_active,
            "rev_limit": t.rev_limit,
            "lights_active": t.lights_active,
        },
    }


def write_lap(output_path: Path, payload: dict) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def record_one_lap(args: argparse.Namespace) -> Path:
    output_path = args.output or default_output_path()
    decoder = TelemetryDecoder(args.ps5_ip)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", LOCAL_TELEMETRY_PORT))
    sock.settimeout(1.0)

    samples: list[dict] = []
    recording_lap: int | None = None
    armed_lap: int | None = None
    first_seen_lap: int | None = None
    capture_started_at = time.monotonic()
    wait_deadline = capture_started_at + args.max_wait_seconds
    next_heartbeat = 0.0
    last_status_at = 0.0

    print(f"PS5: {args.ps5_ip}")
    print(f"Heartbeat: {args.ps5_ip}:{GT7_HEARTBEAT_PORT} -> listen 0.0.0.0:{LOCAL_TELEMETRY_PORT}")
    print(f"Output: {output_path}")
    if args.include_current:
        print("Записываю текущий круг сразу после первого валидного пакета.")
    else:
        print("Жду начало следующего круга, чтобы записать полный круг.")

    try:
        while time.monotonic() < wait_deadline:
            now = time.monotonic()
            if now >= next_heartbeat:
                sock.sendto(HEARTBEAT, (args.ps5_ip, GT7_HEARTBEAT_PORT))
                next_heartbeat = now + 2.0

            try:
                data, _ = sock.recvfrom(4096)
            except socket.timeout:
                print(".", end="", flush=True)
                continue

            telemetry = decoder.decode(data)
            if telemetry is None or telemetry.current_lap < 0:
                continue
            if telemetry.is_loading:
                continue

            current_lap = telemetry.current_lap
            if first_seen_lap is None:
                first_seen_lap = current_lap
                armed_lap = current_lap
                if args.include_current and current_lap > 0:
                    recording_lap = current_lap
                    capture_started_at = time.monotonic()
                    print(f"\nНачал запись текущего круга {recording_lap}.")
                else:
                    print(f"\nВижу круг {current_lap}. Стартую запись при переходе на следующий круг.")

            if not args.include_current and recording_lap is None and armed_lap is not None:
                if current_lap != armed_lap and current_lap > 0:
                    recording_lap = current_lap
                    capture_started_at = time.monotonic()
                    samples.clear()
                    print(f"\nНачал запись круга {recording_lap}.")
                else:
                    if time.monotonic() - last_status_at > 10:
                        print(
                            f"\nОжидание следующего круга. Сейчас lap={current_lap}, "
                            f"speed={telemetry.speed_kph:.1f} км/ч."
                        )
                        last_status_at = time.monotonic()
                    continue

            if recording_lap is None:
                continue

            if current_lap != recording_lap:
                if not samples:
                    raise RuntimeError("Круг сменился, но кадры телеметрии не были записаны.")

                finished_at = datetime.now(UTC).isoformat()
                payload = {
                    "metadata": {
                        "game": "Gran Turismo 7",
                        "ps5_ip": args.ps5_ip,
                        "heartbeat": HEARTBEAT.decode("ascii"),
                        "heartbeat_port": GT7_HEARTBEAT_PORT,
                        "local_telemetry_port": LOCAL_TELEMETRY_PORT,
                        "recorded_lap": recording_lap,
                        "next_lap_seen": current_lap,
                        "sample_count": len(samples),
                        "started_at_utc": samples[0]["captured_at_utc"],
                        "finished_at_utc": finished_at,
                        "last_lap_time_ms_reported_after_finish": telemetry.last_lap_time_ms,
                    },
                    "samples": samples,
                }
                write_lap(output_path, payload)
                print(f"\nГотово: записал {len(samples)} кадров круга {recording_lap} в {output_path}")
                return output_path

            samples.append(telemetry_sample(telemetry, capture_started_at))
            if len(samples) % 600 == 0:
                print(
                    f"\nПишу lap={recording_lap}: {len(samples)} кадров, "
                    f"speed={telemetry.speed_kph:.1f} км/ч, rpm={telemetry.engine_rpm:.0f}."
                )

        raise TimeoutError(f"Не удалось записать полный круг за {args.max_wait_seconds} секунд.")
    finally:
        sock.close()


def main() -> None:
    args = parse_args()
    try:
        record_one_lap(args)
    except KeyboardInterrupt:
        print("\nОстановлено пользователем. JSON не сохранён, потому что круг не завершён.")
    except Exception as exc:
        print(f"\n[ОШИБКА] {exc}")


if __name__ == "__main__":
    main()
