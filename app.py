"""
Main Flask application for MD-01 / EME GUI.

- Controls the MD-01 antenna controller (via SerialAntenna)
- Tracks the Moon and slews the antenna
- Streams an RTSP camera as MJPEG
- Controls a Raspberry Pi Pico-based coax switch
"""

from __future__ import annotations

import os
import threading
import time
import random
import webbrowser
from datetime import datetime
from datetime import timezone
UTC = timezone.utc
from functools import wraps
from typing import Any, Dict, Optional
from dotenv import load_dotenv
from Test_CW_gnu import testSpeci
import signal
import sys
from collections import deque
from queue import Queue, Empty

import serial.tools.list_ports
from flask import (
    Flask,
    Response,
    jsonify,
    render_template,
    request,
    Response, 
    session, 
    redirect, 
    url_for
)

from camera import CameraStream, mjpeg_generator
from serialComm import SerialAntenna
from serialSwitch import SerialSwitch
import CalcMoonPos
import logging

# Silence Flask/Werkzeug request logs (GET/POST lines), keep errors
logging.getLogger("werkzeug").setLevel(logging.ERROR)

measurements = []
# -----------------------------------------------------------------------------
# App / global objects
# -----------------------------------------------------------------------------

app = Flask(__name__)

load_dotenv()

app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")
APP_PASSWORD = os.getenv("APP_PASSWORD")


CAMERA_SOURCE = os.getenv("CAMERA_SOURCE")
# if not CAMERA_SOURCE:
#     raise RuntimeError("CAMERA_SOURCE environment variable not set")

camera = CameraStream(src=CAMERA_SOURCE, jpeg_quality=80)

# Multithreading
serial_lock = threading.Lock()
camera_lock = threading.Lock()
tracking_thread: Optional[threading.Thread] = None
tracking_stop = threading.Event()

# Pico switch auto-detection
SWITCH_PORT_ENV = "COM14"     # optional override, e.g. "COM5"
SWITCH_PORT_DEFAULT = "COM14"            # optional hard-coded fallback; "" = disabled
switch: Optional[SerialSwitch] = None


# Parking position for the antenna
PARKAZ = 40
PARKEL = 60

# Tracking parameters
ELEVATION_MIN = 15          # deg — tracking allowed only above this (unless force=1)
POS_TOL = 0.1               # deg — how close is “on target” for az & el
DEAD_BAND = 0.1             # deg — ignore tiny corrections
SEND_INTERVAL = 3.0         # s   — minimum time between corrections
SLEW_TIMEOUT = 180          # s   — max time for initial / park slew

# Mechanical azimuth limits
AZ_LIMIT = 540              # total safe mechanical range ±540°
CABLE_MARGIN = 30           # safety margin before wrap

# Controller azimuth encoding parameters
AZ_OFFSET_DEG = 0           # offset if your mount is shifted
AZ_FLIP_180 = False         # quick flip by 180° if reference is inverted

# --- Measurement live console (SSE) ---
MEAS_LOG_MAX = 3000
meas_log = deque(maxlen=MEAS_LOG_MAX)     # keeps recent lines
meas_stream = Queue()                     # pushes lines to connected browsers
meas_lock = threading.Lock()
meas_running = False


# Shared state dictionary exposed through /status
state: Dict[str, Any] = {
    "connected": False,
    "status": "Not connected",
    "status_level": "info",
    "status_at": None,
    "az": 0.0,
    "az_cont": 0.0,
    "el": 0.0,
    "az_norm": 0.0,
    "az_moon": 0.0,
    "el_moon": 0.0,
    "tracking": False,
    "port": None,
    "switch_port": None,
    "switch_connected": False,
    "switches": {
        "S1": 0,
        "S2": 0,
        "S3": 0,
    },
    "moon_next_above_15": None,
    "moon_next_below_15": None,
}


ant: Optional[SerialAntenna] = None
moon_cont_az: Optional[float] = None
last_moon_az: Optional[float] = None


def stop_tracking_worker() -> None:
    """
    Stop the background tracking thread (if running) and
    mark state['tracking'] = False.
    """
    global tracking_thread, tracking_stop, ant

    tracking_stop.set()

    if tracking_thread and tracking_thread.is_alive():
        try:
            tracking_thread.join(timeout=1)
        except Exception:
            pass

    tracking_thread = None
    state["tracking"] = False

def meas_print(line: str) -> None:
    """Append a line to measurement log + push to SSE listeners."""
    ts = datetime.now().strftime("%H:%M:%S")
    msg = f"[{ts}] {line}".rstrip()

    with meas_lock:
        meas_log.append(msg)

    try:
        meas_stream.put_nowait(msg)
    except Exception:
        pass

# -----------------------------------------------------------------------------
# Status manager / decorator
# -----------------------------------------------------------------------------

def set_status(level: str, message: str) -> None:
    """
    Update the global status.

    level: 'info' | 'success' | 'warning' | 'error' | 'busy'
    """
    state["status_level"] = level
    state["status"] = message
    state["status_at"] = datetime.now(UTC).isoformat()


def api_action(fn):
    """
    Decorator for JSON API routes.

    - Catches exceptions
    - Updates status to 'error'
    - Returns a consistent JSON error payload
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            set_status("error", f"{type(exc).__name__}: {exc}")
            return jsonify(success=False, status=state["status"]), 500

    return wrapper

def is_authenticated() -> bool:
    """Return True if the current session is logged in for control."""
    return bool(session.get("auth", False))


def require_auth(fn):
    """
    Decorator for routes that modify hardware.

    - If not logged in, returns 403 JSON
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            msg = "Authentication required"
            set_status("error", msg)
            return jsonify(success=False, status=msg), 403
        return fn(*args, **kwargs)

    return wrapper

@app.context_processor
def inject_auth_flags():
    """
    Inject can_edit into all templates.

    - False: view-only (no controls)
    - True: user logged in and allowed to change things
    """
    return {"can_edit": is_authenticated()}


# -----------------------------------------------------------------------------
# Angle / coordinate helpers
# -----------------------------------------------------------------------------

def norm360(x: float) -> float:
    """Normalize angle to [0, 360)."""
    return x % 360


def signed180(x: float) -> float:
    """Wrap any angle to [-180, +180)."""
    return ((x + 180) % 360) - 180


def app_to_ctrl_continuous(app_deg: float) -> float:
    """
    Convert an angle in app coordinates to controller 'continuous' azimuth
    (before wrapping/encoding).
    """
    val = app_deg - AZ_OFFSET_DEG
    if AZ_FLIP_180:
        val -= 180
    return val


def encode_ctrl_az_from_continuous(app_cont_deg: float) -> float:
    """
    Take a continuous desired azimuth in app-space (can be negative or >360),
    map to controller space, and encode as a single signed command in
    [-180, +180].
    """
    ctrl_cont = app_to_ctrl_continuous(app_cont_deg)
    cmd = signed180(ctrl_cont)

    # Avoid -0.0 which some firmwares display oddly.
    if abs(cmd) < 1e-6:
        cmd = 0.0

    return round(cmd, 1)


def ang_err(target_deg: float, current_deg: float) -> float:
    """Signed minimal angle error in degrees, in [-180, +180]."""
    return ((target_deg - current_deg + 180) % 360) - 180


def unwrap_azimuth(current: float, last: float) -> float:
    """
    Unwrap azimuth to produce a continuous angle, avoiding 0/360 jumps.
    """
    delta = current - last
    if delta > 180:
        delta -= 360
    elif delta < -180:
        delta += 360
    return last + delta

def unwrap_ctrl_az(current_az_deg: float, last_cont: float) -> float:
    """
    Unwrap controller-read azimuth into a continuous azimuth.
    Uses normalized current angle, but produces a continuous result.
    """
    cur = norm360(current_az_deg)
    last_norm = norm360(last_cont)
    delta = cur - last_norm
    if delta > 180:
        delta -= 360
    elif delta < -180:
        delta += 360
    return last_cont + delta

def safe_azimuth(target_az: float, current_az: float) -> float:
    """
    Compute a cable-safe azimuth command.

    - Keeps rotation within ±AZ_LIMIT range
    - Chooses the shortest rotation
    """
    delta = target_az - (current_az % 360)
    if delta > 180:
        delta -= 360
    elif delta < -180:
        delta += 360

    new_az = current_az + delta

    # Wrap protection
    if new_az > AZ_LIMIT - CABLE_MARGIN:
        new_az -= 360
    elif new_az < -AZ_LIMIT + CABLE_MARGIN:
        new_az += 360

    return new_az


# -----------------------------------------------------------------------------
# Camera helpers
# -----------------------------------------------------------------------------

def ensure_camera_running() -> None:
    """
    Safely start the camera if it's not running yet.

    Called from routes that need video/health. Uses a lock to avoid concurrent
    start() calls from multiple requests.
    """
    with camera_lock:
        try:
            if not camera.running:
                camera.start()
        except Exception as exc:  # noqa: BLE001
            # Store error for /camera/health, don't crash the app.
            try:
                camera.last_error = str(exc)
            except Exception:  # noqa: BLE001
                pass


# -----------------------------------------------------------------------------
# Antenna helpers
# -----------------------------------------------------------------------------

def wait_until_position(
    target_az: float,
    target_el: float,
    timeout: float = SLEW_TIMEOUT,
) -> bool:
    """
    Block until antenna reaches (target_az, target_el) within POS_TOL, or
    until timeout.

    Returns True if target reached, otherwise False.
    """
    global ant

    t0 = time.time()
    while time.time() - t0 < timeout and not tracking_stop.is_set():
        if ant is None:
            return False

        with serial_lock:
            try:
                az, el = ant.read_md01_position()
            except Exception:
                time.sleep(0.5)
                continue

        state["az"] = round(az, 1)
        try:
            state["az_cont"] = round(
                unwrap_ctrl_az(az, float(state.get("az_cont", az))),
                2,
            )
        except Exception:
            state["az_cont"] = round(az, 2)
        state["az_norm"] = round(state["az"] % 360, 1)
        state["el"] = round(el, 1)

        az_ok = abs(ang_err(target_az % 360, az % 360)) <= POS_TOL
        el_ok = abs(target_el - el) <= POS_TOL
        if az_ok and el_ok:
            return True

        time.sleep(0.5)

    return False


def wait_for_moon_above(
    min_el: float = ELEVATION_MIN,
    poll_s: float = 10,
) -> bool:
    """
    Block until Moon's elevation is >= min_el, or tracking_stop is set.

    Returns True if Moon reaches the minimum elevation, False if stopped
    before that happens.
    """
    while not tracking_stop.is_set():
        try:
            azm, elm = CalcMoonPos.get_moon_position()
            state["az_moon"] = round(azm, 1)
            state["el_moon"] = round(elm, 1)
            if elm >= min_el:
                return True
        except Exception:
            pass
        time.sleep(poll_s)

    return False


def go_to_parking() -> None:
    """
    Command the antenna to park and wait until it reaches the parking position.
    """
    global ant

    if ant is None:
        return

    with serial_lock:
        ant.send_rot2_set(ant.ser, PARKAZ, PARKEL)

    set_status("info", f"Parking: Az={PARKAZ}°, El={PARKEL}°")
    reached = wait_until_position(PARKAZ, PARKEL, timeout=SLEW_TIMEOUT)

    if reached:
        set_status("info", "Parked and waiting for Moon to rise")
    else:
        set_status("warning", "Park slew timed out; holding position")


# -----------------------------------------------------------------------------
# Background poll loop
# -----------------------------------------------------------------------------

def poll_loop() -> None:
    """
    Background loop that:

    - Periodically reads antenna position (if connected)
    - Keeps the global state angles up to date
    - Continually updates Moon position
    """
    global ant

    fail_count = 0
    last_good_cont: Optional[float] = None
    MAX_JUMP_DEG = 60.0  # ignore single-sample az jumps bigger than this (noise/wrap glitch)

    while True:
        if state["connected"] and ant:
            try:
                with serial_lock:
                    az, el = ant.read_md01_position()
                state["az"] = round(az, 1)
                state["az_norm"] = round(state["az"] % 360, 1)
                state["el"] = round(el, 1)
                # Update raw
                az_raw = float(az)
                el_raw = float(el)
                # Build continuous azimuth estimate
                if last_good_cont is None:
                    az_cont = az_raw
                else:
                    az_cont = unwrap_ctrl_az(az_raw, last_good_cont)
                # Reject improbable single-sample jumps (typical cause of +/-90 or +/-180 offsets)
                if last_good_cont is not None and abs(az_cont - last_good_cont) > MAX_JUMP_DEG:
                    # keep last_good_cont, but still update norm for UI sanity
                    set_status("warning", f"Az jump filtered: {az_raw:.1f}°")
                else:
                    last_good_cont = az_cont
                    state["az_cont"] = round(az_cont, 2)
                # Always expose a stable UI view
                state["az"] = round(last_good_cont if last_good_cont is not None else az_raw, 1)
                state["az_norm"] = round(norm360(state["az"]), 1)
                state["el"] = round(el_raw, 1)
                fail_count = 0
            except Exception as exc:  # noqa: BLE001
                fail_count += 1
                set_status("warning", f"Read error ({fail_count})")
                if fail_count >= 3:
                    try:
                        with serial_lock:
                            ant.close()
                    except Exception:  # noqa: BLE001
                        pass
                    ant = None
                    state["connected"] = False
                    set_status("error", f"Connection lost: {exc}")
                    fail_count = 0
                time.sleep(2)
        else:
            time.sleep(1)

        # Always update Moon position + projected crossing times
        try:
            azm, elm = CalcMoonPos.get_moon_position()
            state["az_moon"] = round(azm, 1)
            state["el_moon"] = round(elm, 1)

            # Also compute when the Moon will next go above / below 15°
            try:
                next_up_iso, next_down_iso = CalcMoonPos.get_moon_threshold_times(
                    min_el_deg=ELEVATION_MIN
                )
                state["moon_next_above_15"] = next_up_iso
                state["moon_next_below_15"] = next_down_iso
            except Exception:
                state["moon_next_above_15"] = None
                state["moon_next_below_15"] = None

        except Exception:
            # If even Moon position fails, don't crash the loop
            pass

        time.sleep(1)



# -----------------------------------------------------------------------------
# Flask routes: main / status
# -----------------------------------------------------------------------------

@app.route("/")
def index():
    """
    Public, data-only dashboard.

    - Shows live data (status, az/el, moon, camera, coax state)
    - No controls
    """
    ports = [p.device for p in serial.tools.list_ports.comports()]
    return render_template("view.html", state=state, ports=ports)


@app.route("/control")
def control():
    """
    Full control dashboard.

    - Requires login
    - Uses existing control UI (index.html)
    """
    ports = [p.device for p in serial.tools.list_ports.comports()]

    if not is_authenticated():
        # Show login form, then come back here
        return render_template(
            "login.html",
            error=None,
            next=url_for("control"),
        )

    return render_template("index.html", state=state, ports=ports)

@app.route("/status")
def status():
    """Return the current global state as JSON."""
    return jsonify(state)

@app.route("/login", methods=["POST"])
def login():
    """
    Handle login form submission.

    If password matches APP_PASSWORD, mark session as authenticated
    and redirect to 'next' (default: /control).
    """
    password = request.form.get("password", "")
    next_url = request.form.get("next") or url_for("control")

    if password and password == APP_PASSWORD:
        session["auth"] = True
        set_status("info", "Login successful – control enabled")
        return redirect(next_url)

    set_status("error", "Invalid password")
    # Re-render login page with error and same 'next'
    return render_template("login.html", error="Invalid password", next=next_url)


@app.route("/logout", methods=["POST"])
def logout():
    """Log out and return to the public data view."""
    session.clear()
    set_status("info", "Logged out – view only")
    return redirect(url_for("index"))



# -----------------------------------------------------------------------------
# Connect / disconnect controller
# -----------------------------------------------------------------------------

@app.route("/connect", methods=["POST"])
@api_action
@require_auth
def connect():
    """Connect to the MD-01 controller on the selected serial port."""
    global ant

    port = request.form.get("port")
    ant = SerialAntenna(port)
    if not ant.status():
        raise RuntimeError("Port could not be opened")

    with serial_lock:
        az, el = ant.read_md01_position()

    state.update(
        {
            "port": port,
            "connected": True,
            "az": round(az, 1),
            "az_norm": round(az % 360, 1),
            "el": round(el, 1),
        },
    )
    set_status(
        "success",
        f"Connected with {port} (Az={az:.1f}°, El={el:.1f}°)",
    )
    return jsonify(success=True, status=state["status"])

@app.route("/connect_public", methods=["POST"])
@api_action
def connect_public():
    """
    Public connect for the MD-01 controller.

    - Used by the data-only view (no login required)
    - Only opens the serial port and reads current position
    """
    global ant

    port = request.form.get("port")
    ant = SerialAntenna(port)
    if not ant.status():
        raise RuntimeError("Port could not be opened")

    with serial_lock:
        az, el = ant.read_md01_position()

    state.update(
        {
            "port": port,
            "connected": True,
            "az": round(az, 1),
            "az_norm": round(az % 360, 1),
            "el": round(el, 1),
        },
    )
    set_status(
        "success",
        f"[view] Connected with {port} (Az={az:.1f}°, El={el:.1f}°)",
    )
    return jsonify(success=True, status=state["status"])


@app.route("/disconnect", methods=["POST"])
@require_auth
@api_action
def disconnect():
    """Disconnect from the MD-01, park, and stop tracking."""
    global ant, tracking_thread, tracking_stop

    tracking_stop.set()

    if tracking_thread and tracking_thread.is_alive():
        tracking_thread.join(timeout=1)

    if ant:
        with serial_lock:
            safe_az = safe_azimuth(PARKAZ, state["az"])
            ant.send_rot2_set(ant.ser, safe_az, PARKEL)
            ant.stopMovement()
        time.sleep(0.3)
        with serial_lock:
            ant.close()
        ant = None

    state.update(
        {
            "connected": False,
            "tracking": False,
            "az": 0.0,
            "el": 0.0,
        },
    )
    set_status("info", "Not connected")
    return jsonify(success=True, status=state["status"])


# -----------------------------------------------------------------------------
# Manual set
# -----------------------------------------------------------------------------

@app.route("/set", methods=["POST"])
@require_auth
@api_action
def set_position():
    """Manually set antenna position (az, el)."""
    global ant
    force = request.args.get("force", "0") == "1"
    az_req = float(request.form["az"])
    el_req = float(request.form["el"])

    if (el_req <= ELEVATION_MIN) and not force:
        set_status("warning", f"Elevation must be >= {ELEVATION_MIN}°")
        return jsonify(success=False, status=state["status"]), 400

    if not ant:
        set_status("error", "Not connected")
        return jsonify(success=False, status=state["status"]), 400

    cur_app = float(state.get("az_cont", state["az"]))
    tgt_app = norm360(az_req)
    cont_app = safe_azimuth(tgt_app, cur_app)
    cmd_ctrl_az = encode_ctrl_az_from_continuous(cont_app)

    with serial_lock:
        ant.send_rot2_set(ant.ser, cmd_ctrl_az, el_req)

    # Optimistic UI update (poll loop will refine).
    state["az_norm"] = round(norm360(cont_app), 1)
    state["az_cont"] = round(cont_app, 2)

    delta = signed180(tgt_app - cur_app)
    set_status(
        "success",
        (
            f"Set to {tgt_app:.1f}° (Δ={delta:.1f}°) "
            f"→ cmd {cmd_ctrl_az:.1f}° / {el_req:.1f}°"
        ),
    )
    return jsonify(success=True, status=state["status"])


# -----------------------------------------------------------------------------
# Moon tracker
# -----------------------------------------------------------------------------

@app.route("/tracker", methods=["POST"])
@require_auth
@api_action
def tracker():
    """
    Toggle Moon tracking.

    - Starts background thread when enabling.
    - Stops tracking and motion when disabling.
    """
    global ant, tracking_thread, tracking_stop, moon_cont_az, last_moon_az

    if not (state["connected"] and ant):
        set_status("error", "Controller not connected!")
        return jsonify(success=False, status=state["status"]), 400

    force = request.args.get("force", "0") == "1"
    state["tracking"] = not state["tracking"]

    if state["tracking"]:
        # Kill any existing worker.
        if tracking_thread and tracking_thread.is_alive():
            tracking_stop.set()
            try:
                tracking_thread.join(timeout=1)
            except Exception:
                pass

        tracking_stop.clear()

        def _loop():
            nonlocal force
            global moon_cont_az, last_moon_az, ant

            # Step 0: park and wait if Moon below horizon (unless forced)
            try:
                azm, elm = CalcMoonPos.get_moon_position()
                state["az_moon"] = round(azm, 1)
                state["el_moon"] = round(elm, 1)
            except Exception:
                set_status(
                    "warning",
                    "Could not compute Moon position; retrying…",
                )
                time.sleep(2)

            if (state.get("el_moon", 0) < ELEVATION_MIN) and not force:
                go_to_parking()
                if not wait_for_moon_above():
                    return
                try:
                    azm, elm = CalcMoonPos.get_moon_position()
                    state["az_moon"] = round(azm, 1)
                    state["el_moon"] = round(elm, 1)
                except Exception:
                    pass

            # Step 1: initial slew
            if last_moon_az is not None:
                moon_cont_az = unwrap_azimuth(state["az_moon"], last_moon_az)
            else:
                moon_cont_az = state["az_moon"]
            last_moon_az = state["az_moon"]

            # use continuous az estimate for safe wrap handling
            cur_cont = float(state.get("az_cont", state["az"]))
            desired_az = safe_azimuth(moon_cont_az, cur_cont)
            desired_el = state["el_moon"]

            if ant is None:
                return

            with serial_lock:
                ant.send_rot2_set(ant.ser, desired_az, desired_el)

            set_status(
                "busy",
                (
                    f"Slewing to Moon: Az={desired_az:.1f}°, "
                    f"El={desired_el:.1f}°"
                ),
            )

            reached = wait_until_position(
                desired_az,
                desired_el,
                timeout=SLEW_TIMEOUT,
            )
            if not reached:
                set_status(
                    "warning",
                    "Initial slew timed out; entering tracking anyway",
                )
            else:
                set_status("success", "On target — starting active tracking")

            # Step 2: active tracking
            last_send = 0.0
            while not tracking_stop.is_set():
                try:
                    azm, elm = CalcMoonPos.get_moon_position()
                    state["az_moon"] = round(azm, 1)
                    state["el_moon"] = round(elm, 1)
                except Exception as exc:  # noqa: BLE001
                    set_status("warning", f"Moon calc error: {exc}")
                    time.sleep(1)
                    continue

                if state["el_moon"] < ELEVATION_MIN and not force:
                    go_to_parking()
                    if not wait_for_moon_above():
                        break
                    last_moon_az = None
                    continue

                if last_moon_az is not None:
                    moon_cont_az = unwrap_azimuth(
                        state["az_moon"],
                        last_moon_az,
                    )
                else:
                    moon_cont_az = state["az_moon"]
                last_moon_az = state["az_moon"]

                desired_az = safe_azimuth(moon_cont_az, state["az"])
                desired_el = state["el_moon"]

                if ant is None:
                    break

                with serial_lock:
                    try:
                        cur_az, cur_el = ant.read_md01_position()
                    except Exception as exc:  # noqa: BLE001
                        set_status(
                            "error",
                            f"Read error during tracking: {exc}",
                        )
                        time.sleep(1)
                        continue

                state["az"] = round(cur_az, 1)
                state["az_norm"] = round(state["az"] % 360, 1)
                state["el"] = round(cur_el, 1)
                # Update state with continuous unwrap (same logic as poll_loop)
                try:
                    prev = float(state.get("az_cont", cur_az))
                    cont = unwrap_ctrl_az(float(cur_az), prev)
                    # Filter tracking-loop glitches too
                    if abs(cont - prev) <= 60.0:
                        state["az_cont"] = round(cont, 2)
                    state["az"] = round(float(state.get("az_cont", cur_az)), 1)
                except Exception:
                    state["az"] = round(cur_az, 1)
                state["az_norm"] = round(norm360(state["az"]), 1)
                state["el"] = round(cur_el, 1)


                err_az = ang_err(desired_az % 360, cur_az % 360)
                err_el = desired_el - cur_el

                now = time.time()
                if (
                    (abs(err_az) > DEAD_BAND or abs(err_el) > DEAD_BAND)
                    and (now - last_send >= SEND_INTERVAL)
                ):
                    with serial_lock:
                        try:
                            ant.send_rot2_set(ant.ser, desired_az, desired_el)
                        except Exception as exc:  # noqa: BLE001
                            set_status(
                                "error",
                                f"Tracking error: {exc}",
                            )
                            time.sleep(1)
                            continue
                    last_send = now
                    set_status(
                        "busy",
                        (
                            f"Tracking: Az→{desired_az:.1f}°, "
                            f"El→{desired_el:.1f}° "
                            f"(ΔAz={err_az:.1f}°, ΔEl={err_el:.1f}°)"
                        ),
                    )

                time.sleep(0.25)

        tracking_thread = threading.Thread(target=_loop, daemon=True)
        tracking_thread.start()
        return jsonify(success=True, tracking=True, status=state["status"])

    # STOP tracking branch
    stop_tracking_worker()

    try:
        if ant:
            with serial_lock:
                ant.stopMovement()
    except Exception:
        pass

    set_status("info", "Tracking and movement stopped")
    return jsonify(success=True, tracking=False, status=state["status"])


# -----------------------------------------------------------------------------
# Start a measurement
# -----------------------------------------------------------------------------
@app.post("/measurement/start")
@require_auth
@api_action
def measurement_start():
    global meas_running

    if meas_running:
        return jsonify(success=False, status="Measurement already running"), 409

    if not state.get("connected"):
        return jsonify(success=False, status="Controller not connected"), 400

    def meas_stderr(line: str) -> None:
        if (line or "").lstrip().startswith("[INFO]"):
            meas_print(line)
        else:
            meas_print("ERR: " + line)

    def worker():
        global meas_running
        meas_running = True
        meas_print("=== Measurement started ===")

        restore_logging = None
        fd_out = None
        fd_err = None

        try:
            # redirect Python logging into meas console (prevents "--- Logging error ---")
            restore_logging = install_meas_logging(meas_print)

            # Try to capture GNU Radio / UHD stdout+stderr
            try:
                fd_out = _FdTee(1, meas_print)
                fd_err = _FdTee(2, meas_stderr)
                fd_out.__enter__()
                fd_err.__enter__()
                meas_print("Console capture: FD tee enabled")
            except Exception as e:
                fd_out = None
                fd_err = None
                meas_print(f"Console capture: FD tee FAILED ({type(e).__name__}: {e})")
                meas_print("Continuing without FD tee (you will still see meas_print + Python logging).")

            meas_print(f"Current coax_mode={state.get('coax_mode')!r}")

            if state.get("coax_mode") != "tx":
                meas_print("Switching coax to TX preset...")
                ok, payload = coax_toggle_mode_internal()
                if not ok:
                    raise RuntimeError(payload.get("status", "Coax toggle failed"))
                meas_print("Coax switched to TX.")

            meas_print("Starting GNU Radio flowgraph...")
            tb = testSpeci()

            tb.start()
            meas_print("Flowgraph started. Sleeping 2.1s before switching to RX...")
            time.sleep(2.1)

            meas_print("Switching coax to RX preset...")
            ok, payload = coax_toggle_mode_internal()
            if not ok:
                raise RuntimeError(payload.get("status", "Coax toggle failed"))
            meas_print("Coax switched to RX.")

            meas_print("Waiting for flowgraph to finish...")
            tb.wait()
            meas_print("Flowgraph finished.")

            # Drain (only if your _FdTee has close_and_drain)
            if fd_out and hasattr(fd_out, "close_and_drain"):
                fd_out.close_and_drain(timeout=1.5)
            if fd_err and hasattr(fd_err, "close_and_drain"):
                fd_err.close_and_drain(timeout=1.5)
            meas_print("Switching coax back to TX preset...")
            ok, payload = coax_toggle_mode_internal()
            if not ok:
                raise RuntimeError(payload.get("status", "Coax toggle failed"))
            meas_print("Coax switched to TX.")
            meas_print("=== Measurement finished OK ===")

        except Exception as e:
            meas_print(f"=== Measurement FAILED: {type(e).__name__}: {e} ===")
        finally:
            try:
                if fd_out and hasattr(fd_out, "close_and_drain"):
                    fd_out.close_and_drain(timeout=0.2)
            except Exception:
                pass
            try:
                if fd_err and hasattr(fd_err, "close_and_drain"):
                    fd_err.close_and_drain(timeout=0.2)
            except Exception:
                pass
            try:
                if restore_logging:
                    restore_logging()
            except Exception:
                pass

            meas_running = False

    threading.Thread(target=worker, daemon=True).start()
    return jsonify(success=True, status="Measurement started (live console running).")

@app.post("/measurement/console")
@require_auth
@api_action
def measurement_console_write():
    txt = (request.form.get("text") or "").strip()
    if not txt:
        return jsonify(success=False, status="No text"), 400
    meas_print(f">>> {txt}")
    return jsonify(success=True, status="OK")

def coax_toggle_mode_internal():
    """
    Context-free version of coax toggle. Safe to call from background threads.
    Returns: (success: bool, payload: dict)
    """
    global switch

    if not (
        switch
        and getattr(switch, "ser", None)
        and switch.ser.is_open
        and state.get("switch_connected")
    ):
        # IMPORTANT: do not call set_status() here if it uses request context
        state["status"] = "Pico switch not connected"
        return False, {"status": state["status"]}

    switches = state.get("switches") or {}

    current_mode = state.get("coax_mode")
    s1 = switches.get("S1")
    s2 = switches.get("S2")
    s3 = switches.get("S3")

    if current_mode not in ("tx", "rx"):
        if s1 == "1" and s2 == "2" and s3 == "2":
            current_mode = "tx"
        elif s1 == "2" and s2 == "1" and s3 == "1":
            current_mode = "rx"
        else:
            current_mode = "rx"  # unknown/mixed -> next toggle goes to TX

    if current_mode == "tx":
        new_mode = "rx"
        target = {"S1": "2", "S2": "1", "S3": "1"}
        label = "RX"
    else:
        new_mode = "tx"
        target = {"S1": "1", "S2": "2", "S3": "2"}
        label = "TX"

    all_resp = {}
    with serial_lock:
        for sid in (1, 2, 3):
            side = target[f"S{sid}"]
            resp = switch.set(sid, side)
            if isinstance(resp, dict):
                all_resp.update(resp)
                sw = resp.get("switches")
                if isinstance(sw, dict):
                    switches.update(sw)

    state["switches"] = switches
    state["coax_mode"] = new_mode
    state["status"] = f"Coax relays set to {label} preset"

    payload = {
        "success": True,
        "mode": new_mode,
        "switches": switches,
        "status": f"Coax relays set to {label} preset (S1={target['S1']}, S2={target['S2']}, S3={target['S3']})",
    }
    return True, payload


@app.route("/coax/toggle_mode", methods=["POST"])
@require_auth
@api_action
def coax_toggle_mode():
    ok, payload = coax_toggle_mode_internal()
    if not ok:
        # route can still call set_status safely (it has request context)
        set_status("error", payload.get("status", "Pico switch not connected"))
        return jsonify(success=False, status=state.get("status", "Error")), 500

    set_status("ok", payload.get("status", "OK"))
    return jsonify(**payload)


@app.route("/data")
def data_page():
    """
    Data / analysis page.

    - Umlaufbahn (orbit-style) Moon plot
    - EME measurement history (distance, SNR, etc.)
    """
    ports = [p.device for p in serial.tools.list_ports.comports()]
    return render_template("data.html", state=state, ports=ports)


@app.route("/api/measurements")
def api_measurements():
    """
    Return measurement history for charts.
    """
    return jsonify(
        measurements=measurements,
        count=len(measurements),
    )

# -----------------------------------------------------------------------------
# Stop / park
# -----------------------------------------------------------------------------

@app.route("/stop", methods=["POST"])
@require_auth
@api_action
def stop():
    """
    Immediate stop of movement AND stop tracking thread.
    Does NOT park – it just freezes everything where it is.
    """
    global ant

    if not ant:
        set_status("error", "Controller not connected!")
        return jsonify(success=False, status=state["status"]), 400

    # First: stop tracking thread so it doesn't keep sending commands
    stop_tracking_worker()

    try:
        with serial_lock:
            ant.stopMovement()
        set_status("info", "Movement & tracking stopped")
        return jsonify(success=True, status=state["status"])
    except Exception as exc:  # noqa: BLE001
        set_status("error", f"Error while stopping: {exc}")
        return jsonify(success=False, status=state["status"])


@app.route("/park", methods=["POST"])
@require_auth
@api_action
def park():
    """Send antenna to park position."""
    global ant

    if not ant:
        set_status("error", "Controller not connected!")
        return jsonify(success=False, status=state["status"]), 400

    try:
        with serial_lock:
            safe_az = safe_azimuth(PARKAZ, state["az"])
            ant.send_rot2_set(ant.ser, safe_az, PARKEL)
            ant.stopMovement()
        set_status("info", "Parkposition set")
        return jsonify(success=True, status=state["status"])
    except Exception as exc:  # noqa: BLE001
        set_status("error", f"Error while parking: {exc}")
        return jsonify(success=False, status=state["status"])

# console route

@app.get("/measurement/stream")
def measurement_stream():
    def gen():
        # Send backlog first
        with meas_lock:
            backlog = list(meas_log)

        for line in backlog[-300:]:
            yield f"data: {line}\n\n"

        # Then live
        while True:
            try:
                line = meas_stream.get(timeout=15)
                yield f"data: {line}\n\n"
            except Empty:
                # keep connection alive
                yield "data: \n\n"

    return Response(gen(), mimetype="text/event-stream")


# -----------------------------------------------------------------------------
# Camera routes
# -----------------------------------------------------------------------------

@app.route("/camera/health")
def camera_health():
    """
    Report camera health.

    Also attempts to (re)start the camera if it is not running.
    """
    ensure_camera_running()

    h = camera.get_health()
    ok = h["running"] and (
        h["has_frame"] or h["last_frame_age"] is not None
    )
    return jsonify(h), (200 if ok else 503)


@app.route("/video.mjpg")
def video_mjpg():
    """
    MJPEG video stream endpoint.

    Frontend uses this inside an <img>. If unhealthy, returns 503 so that
    the frontend can show a "No video" overlay.
    """
    ensure_camera_running()

    h = camera.get_health()
    ok = h["running"] and (
        h["has_frame"] or h["last_frame_age"] is not None
    )
    if not ok:
        return Response(status=503)

    return Response(
        mjpeg_generator(camera, fps=25),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


# -----------------------------------------------------------------------------
# Coax switch helpers / routes
# -----------------------------------------------------------------------------

import serial  # at top of file, if not already

def probe_pico_port(port: str, timeout: float = 1.0) -> dict:
    """
    Open 'port', send STATUS, and verify we get a Pico-style reply:

        STATE S1=1 S2=2 S3=1

    Returns a switches dict like {"S1": "1", "S2": "1", "S3": "1"}
    or raises RuntimeError if the port is not our Pico.
    """
    ser = None
    try:
        # Adjust baudrate if your Pico uses something else
        ser = serial.Serial(port, baudrate=115200, timeout=0.3)

        # Flush any garbage / boot messages
        try:
            ser.reset_input_buffer()
            ser.reset_output_buffer()
        except Exception:
            pass

        # Send STATUS
        ser.write(b"STATUS\r\n")
        ser.flush()

        t0 = time.time()
        switches: dict[str, str] = {}

        while time.time() - t0 < timeout:
            line = ser.readline()
            if not line:
                continue

            text = line.decode(errors="ignore").strip().upper()

            # Ignore your "Ready: commands ..." banner etc.
            if not text.startswith("STATE "):
                continue

            # Expect: STATE S1=1 S2=2 S3=1
            parts = text.split()
            for part in parts[1:]:
                if "=" not in part:
                    continue
                k, v = part.split("=", 1)
                if k in ("S1", "S2", "S3") and v in ("1", "2"):
                    switches[k] = v

            if {"S1", "S2", "S3"} <= set(switches.keys()):
                return switches

            raise RuntimeError(f"Bad STATE line on {port!r}: {text!r}")

        raise RuntimeError(f"No STATE reply within timeout on {port!r}")

    finally:
        if ser is not None:
            try:
                ser.close()
            except Exception:
                pass


@app.route("/coax/connect", methods=["POST"])
@api_action
def coax_connect():
    """
    Manually connect to the Pico coax switch on the selected serial port.

    - Opens the port with pyserial
    - Sends STATUS and parses "STATE S1=.. S2=.. S3=.."
    - Only on success creates SerialSwitch and marks as connected
    """
    global switch

    port = request.form.get("port")
    if not port:
        set_status("error", "No switch COM port selected")
        return jsonify(success=False, status=state["status"]), 400

    try:
        # 1) HARD PROBE: must look like our Pico
        switches_dict = probe_pico_port(port)

        # 2) Now that we know it is our firmware, create the high-level wrapper
        with serial_lock:
            sw = SerialSwitch(port)
        switch = sw

        state["switch_port"] = port
        state["switch_connected"] = True
        # Initialize global switches with what we saw in the first STATUS
        state["switches"] = switches_dict

        set_status("success", f"Pico switch connected on {port}")
        return jsonify(success=True, status=state["status"])

    except Exception as exc:
        switch = None
        state["switch_port"] = None
        state["switch_connected"] = False
        set_status("error", f"Failed to connect Pico switch on {port}: {exc}")
        return jsonify(success=False, status=state["status"]), 500

@app.route("/coax/connect_public", methods=["POST"])
@api_action
def coax_connect_public():
    """
    Public connect for the Pico coax switch (no login).

    Used by the data-only view page.
    """
    global switch

    port = request.form.get("port")
    if not port:
        set_status("error", "No switch COM port selected")
        return jsonify(success=False, status=state["status"]), 400

    try:
        # 1) HARD PROBE: must look like our Pico
        switches_dict = probe_pico_port(port)

        # 2) Now that we know it is our firmware, create the high-level wrapper
        with serial_lock:
            sw = SerialSwitch(port)
        switch = sw

        state["switch_port"] = port
        state["switch_connected"] = True
        state["switches"] = switches_dict

        set_status("success", f"[view] Pico switch connected on {port}")
        return jsonify(success=True, status=state["status"])

    except Exception as exc:
        switch = None
        state["switch_port"] = None
        state["switch_connected"] = False
        set_status("error", f"[view] Failed to connect Pico switch on {port}: {exc}")
        return jsonify(success=False, status=state["status"]), 500


@app.route("/coax/disconnect", methods=["POST"])
@require_auth
@api_action
def coax_disconnect():
    """
    Disconnect from the Pico coax switch.
    """
    global switch

    if switch is not None:
        try:
            with serial_lock:
                if getattr(switch, "ser", None):
                # close if possible
                    switch.ser.close()
        except Exception:
            pass
        switch = None

    state["switch_port"] = None
    state["switch_connected"] = False
    state["switches"] = {"S1": 0, "S2": 0, "S3": 0}

    set_status("info", "Pico switch disconnected")
    return jsonify(success=True, status=state["status"])


@app.route("/coax/<int:sid>/<side>", methods=["POST"])
@require_auth
@api_action
def coax_set(sid: int, side: str):
    global switch

    side = str(side).strip()
    if sid not in (1, 2, 3) or side not in ("1", "2"):
        return jsonify(success=False, error="Invalid command"), 400

    if not (
        switch
        and getattr(switch, "ser", None)
        and switch.ser.is_open
        and state.get("switch_connected")
    ):
        set_status("error", "Pico switch not connected")
        return jsonify(success=False, status=state["status"]), 500

    with serial_lock:
        resp = switch.set(sid, side)

    sw = resp.get("switches") if isinstance(resp, dict) else None
    if isinstance(sw, dict):
        state["switches"].update(sw)

    return jsonify(success=True, state=resp, status="Coax command sent")



@app.route("/coax/status")
@api_action
def coax_status():
    """
    Status endpoint for coax switch.

    - Does not try to auto-connect.
    - Says connected=True ONLY if we have an open switch and can read STATUS.
    """
    global switch

    if not (switch and getattr(switch, "ser", None) and switch.ser.is_open):
        return jsonify(
            success=True,
            connected=False,
            state="NO SWITCH",
            switches={},
        ), 200

    switches = {}
    state_str = ""
    connected = False

    try:
        with serial_lock:
            st = switch.status_parsed()

        state_str = (st.get("raw") or "").strip()
        sw = st.get("switches") or {}

        if isinstance(sw, dict) and {"S1", "S2", "S3"} <= set(sw.keys()):
            switches = sw
            connected = True
        else:
            connected = False

    except Exception as exc:  # noqa: BLE001
        state_str = f"ERROR: {exc}"
        switches = {}
        connected = False

    return jsonify(
        success=True,
        connected=connected,
        state=state_str,
        switches=switches,
    ), 200

# -----------------------------------------------------------------------------
# Start background threads when the Flask app is used
# -----------------------------------------------------------------------------


_poll_started = False
_poll_lock = threading.Lock()

def start_background_threads() -> None:
    """
    Ensure the antenna / Moon poll loop is running,
    even if the app is started via `flask run` or gunicorn.
    """
    global _poll_started
    with _poll_lock:
        if not _poll_started:
            threading.Thread(target=poll_loop, daemon=True).start()
            _poll_started = True

class _MeasTee:
    def __init__(self, original, writer):
        self.original = original
        self.writer = writer

    def write(self, s):
        if s:
            # split to lines so SSE updates “live”
            for part in s.splitlines():
                if part.strip():
                    self.writer(part)
        return self.original.write(s)

    def flush(self):
        return self.original.flush()

class _FdTee:
    """
    Tee OS-level FD (1 or 2) into a callback, while still forwarding to original FD.
    WARNING: dup2 affects the whole process while active.
    """
    def __init__(self, fd: int, callback):
        self.fd = fd
        self.callback = callback
        self._old_fd_dup = None
        self._pipe_r = None
        self._pipe_w = None
        self._t = None

    def __enter__(self):
        self._old_fd_dup = os.dup(self.fd)
        self._pipe_r, self._pipe_w = os.pipe()

        # redirect fd -> pipe write end
        os.dup2(self._pipe_w, self.fd)

        def _reader():
            try:
                with os.fdopen(self._pipe_r, "rb", closefd=True) as r:
                    while True:
                        chunk = r.read(4096)
                        if not chunk:
                            break

                        # forward to original fd
                        try:
                            os.write(self._old_fd_dup, chunk)
                        except Exception:
                            pass

                        # callback lines
                        try:
                            text = chunk.decode("utf-8", errors="replace")
                        except Exception:
                            text = repr(chunk)

                        for line in text.splitlines():
                            if line.strip():
                                self.callback(line)
            except Exception:
                pass

        self._t = threading.Thread(target=_reader, daemon=True)
        self._t.start()
        return self

    def close_and_drain(self, timeout: float = 1.0):
        """
        Restore fd and close the write-end so the reader sees EOF and exits,
        then join the reader thread to drain remaining buffered output.
        """
        # restore original fd (stops new bytes entering the pipe)
        try:
            if self._old_fd_dup is not None:
                os.dup2(self._old_fd_dup, self.fd)
        except Exception:
            pass

        # closing write-end makes reader exit after draining
        try:
            if self._pipe_w is not None:
                os.close(self._pipe_w)
                self._pipe_w = None
        except Exception:
            pass

        # wait for reader to finish draining
        try:
            if self._t is not None:
                self._t.join(timeout=timeout)
        except Exception:
            pass

        # cleanup
        try:
            if self._old_fd_dup is not None:
                os.close(self._old_fd_dup)
                self._old_fd_dup = None
        except Exception:
            pass

    def __exit__(self, exc_type, exc, tb):
        self.close_and_drain(timeout=1.0)

import logging

class _MeasLogHandler(logging.Handler):
    def __init__(self, emit_fn, prefix="LOG: "):
        super().__init__()
        self.emit_fn = emit_fn
        self.prefix = prefix

    def emit(self, record):
        try:
            msg = self.format(record)
            if msg and msg.strip():
                self.emit_fn(self.prefix + msg)
        except Exception:
            pass


def install_meas_logging(meas_print_fn):
    """
    Temporarily route Python logging into meas_print during a measurement.
    Returns a restore() function.
    """
    root = logging.getLogger()
    old_handlers = list(root.handlers)
    old_level = root.level
    old_raise = logging.raiseExceptions

    # Remove existing handlers (they may write to stderr / broken streams)
    for h in list(root.handlers):
        root.removeHandler(h)

    h = _MeasLogHandler(meas_print_fn, prefix="LOG: ")
    h.setLevel(logging.DEBUG)
    h.setFormatter(logging.Formatter("%(asctime)s %(name)s [%(levelname)s] %(message)s"))
    root.addHandler(h)
    root.setLevel(logging.DEBUG)

    # Don’t print “--- Logging error ---” tracebacks
    logging.raiseExceptions = False

    def restore():
        root.handlers.clear()
        for oh in old_handlers:
            root.addHandler(oh)
        root.setLevel(old_level)
        logging.raiseExceptions = old_raise

    return restore


@app.before_request
def ensure_poll_loop_started():
    # This will be called before every request, but the inner logic
    # only starts the thread once thanks to _poll_started + _poll_lock
    start_background_threads()

# -----------------------------------------------------------------------------
# App entry point
# -----------------------------------------------------------------------------

def open_browser() -> None:
    """Open the web UI in the default browser."""
    webbrowser.open_new("http://127.0.0.1:5000/")


if __name__ == "__main__":
    # Background poller for antenna / Moon.
    threading.Thread(target=poll_loop, daemon=True).start()

    threading.Timer(1, open_browser).start()
    # IMPORTANT: allow concurrent requests, so serial I/O won't freeze the UI
    app.run(debug=False, threaded=True)