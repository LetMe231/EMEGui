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
import webbrowser
from datetime import datetime, UTC
from functools import wraps
from typing import Any, Dict, Optional
from dotenv import load_dotenv

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


# -----------------------------------------------------------------------------
# App / global objects
# -----------------------------------------------------------------------------

app = Flask(__name__)

load_dotenv()

app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")
APP_PASSWORD = os.getenv("APP_PASSWORD", "eme")


CAMERA_SOURCE = os.getenv("CAMERA_SOURCE")
if not CAMERA_SOURCE:
    raise RuntimeError("CAMERA_SOURCE environment variable not set")

camera = CameraStream(src=CAMERA_SOURCE, jpeg_quality=80)

# Multithreading
serial_lock = threading.Lock()
camera_lock = threading.Lock()
tracking_thread: Optional[threading.Thread] = None
tracking_stop = threading.Event()

# Pico switch auto-detection
SWITCH_PORT_ENV = "SWITCH_PORT"     # optional override, e.g. "COM5"
SWITCH_PORT_DEFAULT = ""            # optional hard-coded fallback; "" = disabled
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

# Shared state dictionary exposed through /status
state: Dict[str, Any] = {
    "connected": False,
    "status": "Not connected",
    "status_level": "info",
    "status_at": None,
    "az": 0.0,
    "el": 0.0,
    "az_norm": 0.0,
    "az_moon": 0.0,
    "el_moon": 0.0,
    "tracking": False,
    "port": None,
    "switches": {
        "S1": 0,
        "S2": 0,
        "S3": 0,
    },
}

ant: Optional[SerialAntenna] = None
moon_cont_az: Optional[float] = None
last_moon_az: Optional[float] = None


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

    while True:
        if state["connected"] and ant:
            try:
                with serial_lock:
                    az, el = ant.read_md01_position()
                state["az"] = round(az, 1)
                state["az_norm"] = round(state["az"] % 360, 1)
                state["el"] = round(el, 1)
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

        # Always update Moon position
        try:
            azm, elm = CalcMoonPos.get_moon_position()
            state["az_moon"] = round(azm, 1)
            state["el_moon"] = round(elm, 1)
        except Exception:
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

    cur_app = state["az"]
    tgt_app = norm360(az_req)
    cont_app = safe_azimuth(tgt_app, cur_app)
    cmd_ctrl_az = encode_ctrl_az_from_continuous(cont_app)

    with serial_lock:
        ant.send_rot2_set(ant.ser, cmd_ctrl_az, el_req)

    # Optimistic UI update (poll loop will refine).
    state["az_norm"] = round(norm360(cont_app), 1)

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

            desired_az = safe_azimuth(moon_cont_az, state["az"])
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
    tracking_stop.set()
    try:
        if tracking_thread:
            tracking_thread.join(timeout=1)
    except Exception:
        pass

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
from flask import jsonify

@app.post("/measurement/start")
def measurement_start():
    """
    Placeholder endpoint to start a Moon distance measurement.

    TODO (later):
      - Check current controller state (connected, tracking, moon locked).
      - If not in TX mode:
          - command Pico coax: TX path (e.g. S1=1, S2=2, S3=2)
      - Trigger TX pulse on the radio / PA.
      - After pulse is sent, switch coax to RX path (e.g. S1=2, S2=1, S3=1).
      - Arm receive chain, timestamp outgoing & incoming signals.
      - Compute round-trip time Δt and distance d = c * Δt / 2.
      - Store the result and expose it via /status or a dedicated endpoint.
    """

    # For now we just do a couple of basic sanity checks if you want:

    # If you already have some global/state object, you can plug it here.
    # For example (PSEUDO):
    # if not state.connected:
    #     return jsonify(success=False, status="Cannot start measurement: controller not connected"), 400
    # if not state.tracking:
    #     return jsonify(success=False, status="Cannot start measurement: tracking is off"), 400
    # if not getattr(state, "locked", False):
    #     return jsonify(success=False, status="Cannot start measurement: Moon not locked"), 400

    return jsonify(
        success=True,
        status="Measurement sequence would start now (logic not implemented yet)."
    )



# -----------------------------------------------------------------------------
# Stop / park
# -----------------------------------------------------------------------------

@app.route("/stop", methods=["POST"])
@require_auth
@api_action
def stop():
    """Immediate stop of movement (no parking)."""
    global ant

    if not ant:
        set_status("error", "Controller not connected!")
        return jsonify(success=False, status=state["status"]), 400

    try:
        with serial_lock:
            ant.stopMovement()
        state["tracking"] = False
        set_status("info", "Movement stopped")
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

def find_pico_port() -> Optional[str]:
    """
    Detect Pico COM port.

    Priority:
      1) env var SWITCH_PORT (if set)
      2) SWITCH_PORT_DEFAULT constant
      3) auto-scan for Pico VID / description
    """
    env_port = os.getenv(SWITCH_PORT_ENV)
    if env_port:
        return env_port

    if SWITCH_PORT_DEFAULT:
        return SWITCH_PORT_DEFAULT

    # (optional) auto-scan, if you want to keep it:
    import serial.tools.list_ports
    for p in serial.tools.list_ports.comports():
        desc = (p.description or "").lower()
        if p.vid == 0x2E8A or "pico" in desc or "raspberry" in desc:
            return p.device

    return None




def auto_connect_switch(quiet: bool = False) -> bool:
    """
    Try to auto-connect the coax switch.

    Strategy:
      1) If an existing switch looks healthy, keep it.
      2) Try env var SWITCH_PORT (if set).
      3) Try SWITCH_PORT_DEFAULT (if non-empty).
      4) Try auto-detected Pico port by VID/description.
    """
    global switch

    # If we already have a working switch, don't thrash.
    if switch is not None:
        try:
            if (
                getattr(switch, "ser", None)
                and switch.ser.is_open
                and getattr(switch, "connected", True)
            ):
                return True
        except Exception:
            # drop broken instance
            switch = None

    candidate_ports: list[str] = []

    # 1) Env override
    env_port = os.getenv(SWITCH_PORT_ENV)
    if env_port:
        candidate_ports.append(env_port)

    # 2) Hardcoded default (optional)
    if SWITCH_PORT_DEFAULT and SWITCH_PORT_DEFAULT not in candidate_ports:
        candidate_ports.append(SWITCH_PORT_DEFAULT)

    # 3) Auto-detected Pico
    pico_port = find_pico_port()
    if pico_port and pico_port not in candidate_ports:
        candidate_ports.append(pico_port)

    if not candidate_ports:
        if not quiet:
            set_status("warning", "Pico switch not found on any COM port")
        switch = None
        return False

    last_exc: Optional[Exception] = None

    for port in candidate_ports:
        try:
            with serial_lock:
                switch = SerialSwitch(port)
            if not quiet:
                set_status("success", f"Switch connected on {port}")
            return True
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            switch = None

    if not quiet:
        msg = "Pico switch not found on any COM port"
        if last_exc:
            msg += f" (last error: {last_exc})"
        set_status("warning", msg)

    return False



def ensure_switch_connected(quiet: bool = False) -> bool:
    global switch

    # Drop broken / closed instances
    if switch is not None:
        try:
            if not switch.ser or not switch.ser.is_open:
                switch = None
        except Exception:
            switch = None

    # If we don't have a switch, try to create one
    if switch is None:
        port = find_pico_port()
        if not port:
            if not quiet:
                set_status("warning", "No Pico switch port found")
            return False
        try:
            with serial_lock:
                sw = SerialSwitch(port)

                # Probe once to make sure it’s *our* Pico firmware
                st = sw.status_parsed()
                sw_dict = st.get("switches") or {}
                if not (isinstance(sw_dict, dict) and {"S1", "S2", "S3"} <= set(sw_dict.keys())):
                    # Not our device → close and fail
                    try:
                        sw.ser.close()
                    except Exception:
                        pass
                    if not quiet:
                        set_status("warning", f"Port {port} is not a Pico coax switch")
                    return False

                switch = sw

            if not quiet:
                set_status("success", f"Pico switch connected on {port}")
        except Exception as exc:
            switch = None
            if not quiet:
                set_status("error", f"Failed to open Pico switch on {port}: {exc}")
            return False

    try:
        return bool(switch and switch.ser and switch.ser.is_open)
    except Exception:
        switch = None
        return False





@app.route("/coax/<int:sid>/<side>", methods=["POST"])
@require_auth
@api_action
def coax_set(sid: int, side: str):
    """
    Set a coax switch position.

    sid:
        1, 2, or 3
    side:
        "1" or "2"
    """
    global switch

    side = str(side).strip()
    if sid not in (1, 2, 3) or side not in ("1", "2"):
        return jsonify(success=False, error="Invalid command"), 400

    # Loud: for user actions we want to see errors in status bar.
    if not ensure_switch_connected(quiet=False):
        return jsonify(success=False, error="Not connected"), 500

    with serial_lock:
        resp = switch.set(sid, side)

    return jsonify(success=True, state=resp)


@app.route("/coax/status")
@api_action
def coax_status():
    """
    Quiet status endpoint for coax switch.

    - Never updates main status bar.
    - Always returns HTTP 200.
    - Says connected=True ONLY if we can successfully read & parse STATUS.
    """
    global switch

    # 1) Ensure we have an open switch on some port
    if not ensure_switch_connected(quiet=True) or switch is None:
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

        # Only treat as connected if it looks like our Pico protocol
        if isinstance(sw, dict) and {"S1", "S2", "S3"} <= set(sw.keys()):
            switches = sw
            # Optional: also require that at least one switch has a non-empty value
            connected = any(v not in (None, "", 0) for v in switches.values())
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
# App entry point
# -----------------------------------------------------------------------------

def open_browser() -> None:
    """Open the web UI in the default browser."""
    webbrowser.open_new("http://127.0.0.1:5000/")


if __name__ == "__main__":
    # Background poller for antenna / Moon.
    threading.Thread(target=poll_loop, daemon=True).start()
    try:
        auto_connect_switch(quiet=False)
    except Exception as exc:  # noqa: BLE001
        print("ERROR during initial switch auto-connect:", exc)

    threading.Timer(1, open_browser).start()
    # IMPORTANT: allow concurrent requests, so serial I/O won't freeze the UI
    app.run(debug=False, threaded=True)