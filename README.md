# GT7 Telemetry Recorder

Small Python recorder for Gran Turismo 7 telemetry from a PS5. It listens for GT7 UDP telemetry and saves one lap to a JSON file.

## Requirements

- PS5 and Mac on the same local network.
- Gran Turismo 7 telemetry output enabled in the game settings.
- Car must be on track/in a session, not only in the main menu.
- Python environment installed from `pyproject.toml` with `gt-telem`.

Default PS5 IP in the script is `192.168.10.59`.

GT7 ports used by the script:

- Send heartbeat to PS5: `33739/udp`
- Receive telemetry on Mac: `33740/udp`

## Run

Record the next full lap:

```bash
.venv/bin/python main.py
```

or with `uv`:

```bash
uv run python main.py
```

By default the script waits until the lap number changes, records that whole lap, and writes:

```text
laps/gt7_lap_<timestamp>.json
```

The JSON contains `metadata` and `samples`. Each sample includes convenient fields such as speed, RPM, gear, throttle, brake, position, tire data, and a `raw` object with all telemetry fields exposed by `gt-telem`.

## Options

Use another PS5 IP:

```bash
.venv/bin/python main.py --ps5-ip 192.168.10.59
```

Write to a specific file:

```bash
.venv/bin/python main.py --output laps/my_lap.json
```

Start recording the current lap immediately:

```bash
.venv/bin/python main.py --include-current
```

Increase or reduce the maximum wait time:

```bash
.venv/bin/python main.py --max-wait-seconds 1200
```

Show all options:

```bash
.venv/bin/python main.py --help
```

## Troubleshooting

If ping to the PS5 works but no telemetry arrives:

- Check that telemetry output is enabled in GT7.
- Make sure the car is actually on track.
- Allow Python through the macOS firewall for incoming UDP.
- Check that the router/access point does not isolate Wi-Fi clients from LAN devices.
- Make sure no other process is already listening on UDP port `33740`.
