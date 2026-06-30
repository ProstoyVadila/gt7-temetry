from gt_telem.models.telemetry import Telemetry
from gt_telem.turismo_client import TurismoClient

from gt7_telemetry.config import HEARTBEAT


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

