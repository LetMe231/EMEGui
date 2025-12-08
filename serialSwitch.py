"""
SerialSwitch driver for the Raspberry Pi Pico coax switch.

Protocol (examples):
    SET S1_1
    SET S2_2
    STATUS  -> "STATE S1=1 S2=2 S3=1"
"""

import time
from typing import Any, Dict, Optional

import serial


class SerialSwitch:
    """
    Small wrapper around a Pico-based coax switch on a serial port.

    Attributes
    ----------
    port : str
        Serial port (e.g. "COM4", "/dev/ttyACM0", ...)
    ser : serial.Serial | None
        Underlying pyserial object.
    connected : bool
        True if the last operation succeeded and the port appears healthy.
    """

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout: float = 0.2,   # faster default timeout
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser: Optional[serial.Serial] = None
        self.connected: bool = False

        self._open()

    # --------------------------------------------------------------------- #
    # Low-level helpers
    # --------------------------------------------------------------------- #

    def _open(self) -> None:
        """(Re)open the serial port."""
        self.close()
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            # Small settle time; 2s was killing responsiveness.
            time.sleep(0.1)
            self.connected = self.ser.is_open
        except Exception as exc:  # noqa: BLE001
            self.ser = None
            self.connected = False
            raise RuntimeError(f"SerialSwitch: failed to open {self.port}: {exc}") from exc

    def _send_raw(self, cmd: str) -> str:
        """
        Send a single command line and return the reply as a stripped string.

        Raises RuntimeError if the port is not open or I/O fails.
        """
        if not (self.ser and self.ser.is_open):
            self.connected = False
            raise RuntimeError("SerialSwitch: port is not open")

        try:
            self.ser.reset_input_buffer()
            self.ser.write((cmd.strip() + "\n").encode("ascii", errors="ignore"))
            self.ser.flush()
            line = self.ser.readline().decode(errors="ignore").strip()
            self.connected = True
            return line
        except Exception as exc:  # noqa: BLE001
            # Mark as disconnected; caller (ensure_switch_connected) can retry.
            self.connected = False
            raise RuntimeError(f"SerialSwitch I/O error: {exc}") from exc

    # --------------------------------------------------------------------- #
    # High-level API
    # --------------------------------------------------------------------- #

    def set(self, sid: int, side: str) -> str:
        """
        Set switch S1/S2/S3 to position "1" or "2".

        Examples:
            set(1, "1")  ->  "SET S1_1"
            set(2, "2")  ->  "SET S2_2"
        """
        side = str(side).strip()
        if sid not in (1, 2, 3):
            raise ValueError("sid must be 1, 2, or 3")
        if side not in ("1", "2"):
            raise ValueError("side must be '1' or '2'")

        cmd = f"SET S{sid}_{side}"
        return self._send_raw(cmd)

    def status(self) -> str:
        """
        Query raw status string from the Pico.

        Typical response:
            "STATE S1=1 S2=2 S3=1"
        """
        return self._send_raw("STATUS")

    def status_parsed(self) -> Dict[str, Any]:
        """
        Return a parsed view of the STATUS response.

        Returns dict:
            {
              "connected": bool,
              "raw": "STATE S1=1 S2=2 S3=1",
              "switches": {"S1": "1", "S2": "2", "S3": "1"}
            }
        """
        raw = self.status().strip()

        switches: Dict[str, Optional[str]] = {
            "S1": None,
            "S2": None,
            "S3": None,
        }

        # Example raw: "STATE S1=1 S2=2 S3=1"
        for token in raw.split():
            if token.startswith("S") and "=" in token:
                key, val = token.split("=", 1)
                if key in switches:
                    switches[key] = val

        # Consider it connected if it looks like a valid STATE line,
        # or if at least one switch value was parsed.
        connected = raw.startswith("STATE") or any(v is not None for v in switches.values())

        return {
            "connected": connected,
            "raw": raw,
            "switches": switches,
        }

    def close(self) -> None:
        """Close the serial port, if open."""
        if self.ser is not None:
            try:
                if self.ser.is_open:
                    self.ser.close()
            except Exception:
                # We don't care if close fails during shutdown.
                pass
        self.connected = False
