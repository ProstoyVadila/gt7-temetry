import socket
import time
from pathlib import Path

from gt7_telemetry.config import (
    GT7_HEARTBEAT_PORT,
    HEARTBEAT,
    LOCAL_TELEMETRY_PORT,
    RecorderConfig,
)
from gt7_telemetry.decoder import TelemetryDecoder
from gt7_telemetry.output import build_lap_payload, write_lap
from gt7_telemetry.paths import default_output_path
from gt7_telemetry.samples import telemetry_sample


def save_partial_lap(
    config: RecorderConfig,
    output_path: Path,
    recording_lap: int | None,
    samples: list[dict],
    completion_reason: str,
) -> bool:
    if not config.save_partial:
        return False
    if recording_lap is None or not samples:
        return False

    payload = build_lap_payload(
        config=config,
        recording_lap=recording_lap,
        samples=samples,
        completion_reason=completion_reason,
    )
    write_lap(output_path, payload)
    print(
        f"\nСохранил partial JSON: {len(samples)} кадров lap={recording_lap} "
        f"в {output_path} ({completion_reason})."
    )
    return True


def print_startup_summary(config: RecorderConfig, output_path: Path) -> None:
    print(f"PS5: {config.ps5_ip}")
    print(
        f"Heartbeat: {config.ps5_ip}:{GT7_HEARTBEAT_PORT} "
        f"-> listen 0.0.0.0:{LOCAL_TELEMETRY_PORT}"
    )
    print(f"Output: {output_path}")

    if config.replay and config.include_current:
        print("Replay mode + include-current: начну запись сразу после первого валидного пакета.")
    elif config.replay:
        print("Replay mode: жду переход на следующий lap, чтобы не записывать pre-roll.")
    elif config.include_current:
        print("Записываю текущий круг сразу после первого валидного пакета.")
    else:
        print("Жду начало следующего круга, чтобы записать полный круг.")

    if config.save_partial:
        print("Partial JSON будет сохранён при Ctrl-C или timeout.")
    else:
        print("Неполный круг не сохраняю. Для partial JSON используй --save-partial.")


def record_one_lap(config: RecorderConfig) -> Path:
    output_path = config.output or default_output_path(config.name)
    decoder = TelemetryDecoder(config.ps5_ip)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", LOCAL_TELEMETRY_PORT))
    sock.settimeout(1.0)

    samples: list[dict] = []
    recording_lap: int | None = None
    armed_lap: int | None = None
    first_seen_lap: int | None = None
    capture_started_at = time.monotonic()
    wait_deadline = capture_started_at + config.max_wait_seconds
    next_heartbeat = 0.0
    last_status_at = 0.0

    print_startup_summary(config, output_path)

    try:
        while time.monotonic() < wait_deadline:
            now = time.monotonic()
            if now >= next_heartbeat:
                sock.sendto(HEARTBEAT, (config.ps5_ip, GT7_HEARTBEAT_PORT))
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
                if config.include_current:
                    recording_lap = current_lap
                    capture_started_at = time.monotonic()
                    print(f"\nНачал запись текущего круга, lap={recording_lap}.")
                else:
                    print(f"\nВижу круг {current_lap}. Стартую запись при переходе на следующий круг.")

            if not config.include_current and recording_lap is None and armed_lap is not None:
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

                payload = build_lap_payload(
                    config=config,
                    recording_lap=recording_lap,
                    samples=samples,
                    completion_reason="lap_changed",
                    finished_telemetry=telemetry,
                )
                write_lap(output_path, payload)
                print(f"\nГотово: записал {len(samples)} кадров круга {recording_lap} в {output_path}")
                return output_path

            samples.append(telemetry_sample(telemetry, capture_started_at, config.include_raw))
            if len(samples) % 600 == 0:
                print(
                    f"\nПишу lap={recording_lap}: {len(samples)} кадров, "
                    f"speed={telemetry.speed_kph:.1f} км/ч, rpm={telemetry.engine_rpm:.0f}."
                )

        if save_partial_lap(
            config=config,
            output_path=output_path,
            recording_lap=recording_lap,
            samples=samples,
            completion_reason="max_wait_seconds",
        ):
            return output_path
        if recording_lap is not None and samples:
            raise TimeoutError(
                f"Круг {recording_lap} не завершился за {config.max_wait_seconds} секунд. "
                "JSON не сохранён, потому что круг неполный."
            )
        raise TimeoutError(f"Не удалось записать полный круг за {config.max_wait_seconds} секунд.")
    except KeyboardInterrupt:
        if save_partial_lap(
            config=config,
            output_path=output_path,
            recording_lap=recording_lap,
            samples=samples,
            completion_reason="interrupted_by_user",
        ):
            return output_path
        if recording_lap is None or not samples:
            print("\nОстановлено пользователем. JSON не сохранён: запись ещё не начиналась.")
        else:
            print("\nОстановлено пользователем. JSON не сохранён, потому что круг не завершён.")
        return output_path
    finally:
        sock.close()

