#!/usr/bin/env python3
"""
Rolo scrobbler watchdog.

This script has no detection logic of its own on purpose: it delegates to an
external watchdog command (ROLO_SCROBBLER_CHECK_CMD), so a single place decides
what "alive" means. That command can run locally or over SSH on the host where
the scrobbler (for example multi-scrobbler) runs, and it must print one marker
line:

    VIGIA_SCROBBLER status=<STATUS> horas=<hours since last listen> detalhe="<text>"

Recognized STATUS values: OK, OK_LB_FORA, STALE, AUTH_BROKEN, CONFIG_BROKEN,
CONTAINER_DOWN, UNKNOWN. The marker format is a contract with the external
watchdog and is kept as-is.

Exit codes:
  0  ALIVE
  20 DEAD      - invalid config, container down, watchdog unreachable or not configured
  21 AUTH_DEAD - YouTube Music cookie expired
  22 DEGRADED  - no new listen for a long time, but config is valid
"""
import os
import re
import subprocess
import sys

CHECK_CMD = os.environ.get("ROLO_SCROBBLER_CHECK_CMD", "").strip()

STATUS_MAP = {
    "OK": (0, "ALIVE"),
    "OK_LB_FORA": (0, "ALIVE"),
    "STALE": (22, "DEGRADED"),
    "AUTH_BROKEN": (21, "AUTH_DEAD"),
    "CONFIG_BROKEN": (20, "DEAD"),
    "CONTAINER_DOWN": (20, "DEAD"),
    "UNKNOWN": (20, "DEAD"),
}


def main():
    if not CHECK_CMD:
        print("DEAD (ROLO_SCROBBLER_CHECK_CMD is not set)")
        sys.exit(20)
    try:
        out = subprocess.run(CHECK_CMD + " 2>&1", shell=True, capture_output=True,
                             text=True, timeout=120).stdout
    except Exception as err:
        print(f"DEAD (could not run the watchdog: {err})")
        sys.exit(20)

    m = re.search(r'VIGIA_SCROBBLER status=(\S+) horas=(-?\d+) detalhe="([^"]*)"', out or "")
    if not m:
        # A missing marker fails closed: silence is never success.
        print(f"DEAD (watchdog printed no marker. Output: {(out or '').strip()[:300]})")
        sys.exit(20)

    status, _hours, detail = m.group(1), m.group(2), m.group(3)
    code, label = STATUS_MAP.get(status, (20, "DEAD"))
    print(f"{label} ({status}: {detail})")
    sys.exit(code)


if __name__ == "__main__":
    main()
