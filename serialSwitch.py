# serialSwitch.py
import serial
import time
from typing import Dict, Optional


class SerialSwitch:
    """
    Tiny driver for the coax Pico.

    Protocol:
      - SET S1_1 / SET S1_2 / SET S2_1 / ...
      - STATUS  -> e.g. 'STATE S1=1 S2=2 S3=2'
    """

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser: Optional[serial.Serial] = None
        self.connected: bool = False

        self._open_port()

    # ---------- low-level ----------

    def _open_port(self):
        try:
            self.ser = serial.Serial(
                self.port,
                self.baudrate,
                timeout=self.timeout
            )
            # give Pico a moment to reset
            time.sleep(2)
            self.connected = True
        except serial.SerialException as e:
            print(f"[SerialSwitch] Failed to open {self.port}: {e}")
            self.ser = None
            self.connected = False

    def _send_raw(self, cmd: str) -> str:
        """
        Send a raw command and return a single line as string.
        Returns "" on error / not connected.
        """
        if not self.connected or self.ser is None:
            print("[SerialSwitch] _send_raw called while not connected")
            return ""

        try:
            self.ser.reset_input_buffer()
            self.ser.write((cmd.strip() + "\n").encode())
            self.ser.flush()
            line = self.ser.readline().decode(errors="ignore").strip()
            if not line:
                # treat empty as “not really talking to us”
                self.connected = False
            return line
        except serial.SerialException as e:
            print(f"[SerialSwitch] Serial error while sending '{cmd}': {e}")
            self.connected = False
            return ""

    # ---------- public API (backwards compatible) ----------

    def set(self, sid: int, side: str) -> str:
        """
        Set switch S{sid} to side '1' or '2'.
        Returns raw response string.
        """
        side = side.upper()
        if side not in ("1", "2"):
            raise ValueError("side must be '1' or '2'")
        cmd = f"SET S{sid}_{side}"
        return self._send_raw(cmd)

    def status(self) -> str:
        """
        Backwards-compatible: return raw STATUS line as string.
        """
        return self._send_raw("STATUS")

    # Extra helper: parsed view for the web API
    def status_parsed(self) -> Dict:
        """
        Return parsed status:

        {
          "raw": "STATE S1=1 S2=2 S3=2",
          "switches": {"S1": "1", "S2": "2", "S3": "2"},
          "connected": True/False
        }
        """
        raw = self.status()
        switches: Dict[str, str] = {}

        if raw:
            parts = raw.split()
            # Expect: ["STATE", "S1=1", "S2=2", "S3=2"]
            for p in parts:
                if p.startswith("S") and "=" in p:
                    sid, side = p.split("=", 1)
                    sid = sid.strip()
                    side = side.strip().upper()
                    if side in ("1", "2"):
                        switches[sid] = side

        # connected=True only if the port is open, driver thinks connected,
        # and we actually got *some* response
        is_connected = bool(self.connected and raw)

        return {
            "raw": raw,
            "switches": switches,
            "connected": is_connected,
        }

    def close(self):
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except serial.SerialException:
                pass
        self.connected = False

    def __enter__(self):
        if not self.connected:
            self._open_port()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
