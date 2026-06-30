import argparse
from pathlib import Path

from gt7_telemetry.config import DEFAULT_PS5_IP, RecorderConfig
from gt7_telemetry.recorder import record_one_lap


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
        "--replay",
        action="store_true",
        help="Replay mode: wait for the next lap change, then record one full lap.",
    )
    parser.add_argument(
        "--save-partial",
        action="store_true",
        help="Save an incomplete JSON if stopped before the recorded lap finishes.",
    )
    parser.add_argument(
        "--include-raw",
        action="store_true",
        help="Include all raw gt-telem fields in every sample. This makes JSON files much larger.",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Optional filename prefix, e.g. 'Porsche 911 Spa' -> Porsche_911_Spa_gt7_lap_...",
    )
    parser.add_argument(
        "--max-wait-seconds",
        type=int,
        default=900,
        help="Stop waiting if no full lap is captured within this many seconds.",
    )
    return parser.parse_args()


def config_from_args(args: argparse.Namespace) -> RecorderConfig:
    return RecorderConfig(
        ps5_ip=args.ps5_ip,
        output=args.output,
        include_current=args.include_current,
        replay=args.replay,
        save_partial=args.save_partial,
        include_raw=args.include_raw,
        name=args.name,
        max_wait_seconds=args.max_wait_seconds,
    )


def main() -> None:
    config = config_from_args(parse_args())
    try:
        record_one_lap(config)
    except KeyboardInterrupt:
        print("\nОстановлено пользователем. JSON не сохранён, потому что круг не завершён.")
    except Exception as exc:
        print(f"\n[ОШИБКА] {exc}")

