import time
from dataclasses import fields
from datetime import UTC, datetime

from gt_telem.models.telemetry import Telemetry

RAW_TELEMETRY_FIELDS = [field.name for field in fields(Telemetry)]


def telemetry_sample(t: Telemetry, capture_started_at: float, include_raw: bool) -> dict:
    sample = {
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "elapsed_capture_s": round(time.monotonic() - capture_started_at, 6),
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

    if include_raw:
        sample["raw"] = {field_name: getattr(t, field_name) for field_name in RAW_TELEMETRY_FIELDS}

    return sample

