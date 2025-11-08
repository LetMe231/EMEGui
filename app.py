from flask import Flask, render_template, jsonify, request, Response
from camera import CameraStream, mjpeg_generator
import serial.tools.list_ports
import threading, time, os

# --- App setup ----------------------------------------------------------------
app = Flask(__name__)

CAMERA_SOURCE = os.getenv(
    "CAMERA_SOURCE",
    "rtsp://admin:EME_2025@192.168.0.3:554/h264Preview_01_main"
)
camera = CameraStream(src=CAMERA_SOURCE, jpeg_quality=80)

# --- Antenna & moon tracking imports -----------------------------------------
from serialComm import SerialAntenna
import CalcMoonPos

serial_lock = threading.Lock()
tracking_thread = None
tracking_stop = threading.Event()

# --- Configuration ------------------------------------------------------------
# --- Parking ------------------------------------------------------------------
PARKAZ = 40
PARKEL = 60

# --- Tracking -----------------------------------------------------------------
ELEVATION_MIN = 15          # deg — tracking allowed only above this (unless force=1)
POS_TOL       = 0.8         # deg — how close is “on target” for az & el
DEAD_BAND     = 0.1         # deg — don’t send tiny corrections
SEND_INTERVAL = 3.0         # s   — how often we consider sending a correction
SLEW_TIMEOUT  = 180         # s   — max time we’ll wait for an initial slew/park slew


# Mechanical azimuth wrap limits
AZ_LIMIT = 540           # total safe mechanical range ±540°
CABLE_MARGIN = 30        # safety margin before wrap

# --- State --------------------------------------------------------------------
state = {
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
    "port": None
}

ant = None
moon_cont_az = None
last_moon_az = None

# --- Status manager -----------------------------------------------------------
from datetime import datetime
from functools import wraps

def set_status(level: str, message: str):
    """
    level: 'info' | 'success' | 'warning' | 'error' | 'busy'
    """
    state["status_level"] = level
    state["status"] = message
    state["status_at"] = datetime.utcnow().isoformat() + "Z"

def api_action(fn):
    """Decorator to return uniform JSON on failures and set status."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            set_status("error", f"{type(e).__name__}: {e}")
            return jsonify(success=False, status=state["status"]), 500
    return wrapper


# --- Helpers ------------------------------------------------------------------
# --- Controller azimuth encoding ---------------------------------------------
AZ_OFFSET_DEG = 0      # use if your mount is offset (e.g., 180 to fix a south-centered setup)
AZ_FLIP_180   = False  # quick switch to flip by 180° if your reference is inverted

def norm360(x: float) -> float:
    return x % 360

def signed180(x: float) -> float:
    """Wrap any angle to [-180, +180)."""
    return ((x + 180) % 360) - 180

def app_to_ctrl_continuous(app_deg: float) -> float:
    """
    Convert an angle in your app's coordinate system to the controller's
    'continuous' azimuth before wrapping/encoding.
    """
    a = app_deg - AZ_OFFSET_DEG
    if AZ_FLIP_180:
        a -= 180
    return a

def encode_ctrl_az_from_continuous(app_cont_deg: float) -> float:
    """
    Take a 'continuous' desired azimuth in app-space (can be negative or >360),
    map to controller space, then encode as a single signed command in [-180,+180].
    """
    ctrl_cont = app_to_ctrl_continuous(app_cont_deg)
    cmd = signed180(ctrl_cont)
    # avoid sending -0.0 (some firmwares display it weirdly)
    if abs(cmd) < 1e-6:
        cmd = 0.0
    return round(cmd, 1)


def ang_err(target_deg, current_deg):
    """Signed minimal angle error in degrees, in [-180, +180]."""
    return ((target_deg - current_deg + 180) % 360) - 180

def wait_until_position(target_az, target_el, timeout=SLEW_TIMEOUT):
    """Block until antenna reaches (target_az,target_el) within POS_TOL, or timeout."""
    t0 = time.time()
    while time.time() - t0 < timeout and not tracking_stop.is_set():
        with serial_lock:
            try:
                az, el = ant.read_md01_position()
            except Exception:
                time.sleep(0.5)
                continue
        state["az"] = round(az, 1)
        state["az_norm"] = round(state["az"] % 360, 1)
        state["el"] = round(el, 1)
        if abs(ang_err(target_az % 360, az % 360)) <= POS_TOL and abs(target_el - el) <= POS_TOL:
            return True
        time.sleep(0.5)
    return False

def wait_for_moon_above(min_el=ELEVATION_MIN, poll_s=10):
    """Pause here until the Moon's elevation is >= min_el or stop requested."""
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

def go_to_parking():
    """Command park, wait until there, and set status."""
    with serial_lock:
        ant.send_rot2_set(ant.ser, PARKAZ, PARKEL)
    set_status("info", f"Parking: Az={PARKAZ}°, El={PARKEL}°")
    reached = wait_until_position(PARKAZ, PARKEL, timeout=SLEW_TIMEOUT)
    if reached:
        set_status("info", "Parked and waiting for Moon to rise")
    else:
        set_status("warning", "Park slew timed out; holding position")

def unwrap_azimuth(current, last):
    """Return a continuous azimuth."""
    delta = current - last
    if delta > 180:
        delta -= 360
    elif delta < -180:
        delta += 360
    return last + delta

def safe_azimuth(target_az, current_az):
    """
    Compute a cable-safe azimuth command.
    Keeps rotation within ±AZ_LIMIT range, chooses shortest rotation.
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

# --- Background poll loop -----------------------------------------------------
def poll_loop():
    global ant, state
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
            except Exception as e:
                fail_count += 1
                set_status("warning", f"Read error ({fail_count})")
                if fail_count >= 3:
                    try:
                        with serial_lock:
                            ant.close()
                    except:
                        pass
                    ant = None
                    state["connected"] = False
                    set_status("error", f"Connection lost: {e}")
                    fail_count = 0
                time.sleep(2)
        else:
            time.sleep(1)

        # Always update moon position
        try:
            azm, elm = CalcMoonPos.get_moon_position()
            state["az_moon"] = round(azm, 1)
            state["el_moon"] = round(elm, 1)
        except Exception:
            pass

        time.sleep(1)

# --- Flask routes -------------------------------------------------------------
@app.route("/")
def index():
    ports = [p.device for p in serial.tools.list_ports.comports()]
    return render_template("index.html", state=state, ports=ports)

@app.route("/status")
def status():
    return jsonify(state)

# --- Connect / disconnect -----------------------------------------------------
@app.route("/connect", methods=["POST"])
@api_action
def connect():
    global ant
    port = request.form.get("port")
    ant = SerialAntenna(port)
    if not ant.status():
        raise RuntimeError("Port could not be opened")
    with serial_lock:
        az, el = ant.read_md01_position()
    state.update({
        "port": port, "connected": True,
        "az": round(az, 1), "az_norm": round(az % 360, 1), "el": round(el, 1),
    })
    set_status("success", f"Connected with {port} (Az={az:.1f}°, El={el:.1f}°)")
    return jsonify(success=True, status=state["status"])

@app.route("/disconnect", methods=["POST"])
@api_action
def disconnect():
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

    state.update({
        "connected": False,
        "tracking": False,
        "az": 0.0,
        "el": 0.0
    })
    set_status("info", "Not connected")
    return jsonify(success=True, status=state["status"])

# --- Manual set ---------------------------------------------------------------
@app.route("/set", methods=["POST"])
@api_action
def set_position():
    global ant
    az_req = float(request.form["az"])     # app-space target
    el_req = float(request.form["el"])

    if el_req <= 15:
        set_status("warning", "Elevation must be > 15°")
        return jsonify(success=False, status=state["status"]), 400
    if not ant:
        set_status("error", "Not connected")
        return jsonify(success=False, status=state["status"]), 400

    cur_app = state["az"]                       # current in app-space
    tgt_app = norm360(az_req)                   # requested in app-space 0..360
    cont_app = safe_azimuth(tgt_app, cur_app)   # shortest-path continuous angle

    cmd_ctrl_az = encode_ctrl_az_from_continuous(cont_app)

    with serial_lock:
        ant.send_rot2_set(ant.ser, cmd_ctrl_az, el_req)

    # optimistic UI update (poll loop will refine)
    state["az_norm"] = round(norm360(cont_app), 1)
    set_status(
        "success",
        f"Set to {tgt_app:.1f}° (Δ={signed180(tgt_app - cur_app):.1f}°) → cmd {cmd_ctrl_az:.1f}° / {el_req:.1f}°"
    )
    return jsonify(success=True, status=state["status"])


# --- Moon tracker -------------------------------------------------------------
@app.route("/tracker", methods=["POST"])
@api_action
def tracker():
    global ant, tracking_thread, tracking_stop, moon_cont_az, last_moon_az
    if not (state["connected"] and ant):
        set_status("error", "Controller not connected!")
        return jsonify(success=False, status=state["status"]), 400

    force = request.args.get("force", "0") == "1"
    state["tracking"] = not state["tracking"]

    if state["tracking"]:
        # ensure any previous worker is stopped
        if tracking_thread and tracking_thread.is_alive():
            tracking_stop.set()
            try:
                tracking_thread.join(timeout=1)
            except Exception:
                pass

        tracking_stop.clear()

        def _loop():
            nonlocal force
            global moon_cont_az, last_moon_az

            # Step 0: park and wait if Moon is below horizon limit (unless forced)
            try:
                azm, elm = CalcMoonPos.get_moon_position()
                state["az_moon"] = round(azm, 1)
                state["el_moon"] = round(elm, 1)
            except Exception:
                set_status("warning", "Could not compute Moon position; retrying…")
                time.sleep(2)

            if (state.get("el_moon", 0) < ELEVATION_MIN) and not force:
                go_to_parking()
                if not wait_for_moon_above():
                    return  # stop requested before rise
                # refresh Moon position on rise
                try:
                    azm, elm = CalcMoonPos.get_moon_position()
                    state["az_moon"] = round(azm, 1)
                    state["el_moon"] = round(elm, 1)
                except Exception:
                    pass

            # Step 1: INITIAL SLEW — one command, then WAIT until reached
            # unwrap moon az smoothly for continuous az tracking
            if last_moon_az is not None:
                moon_cont_az = unwrap_azimuth(state["az_moon"], last_moon_az)
            else:
                moon_cont_az = state["az_moon"]
            last_moon_az = state["az_moon"]

            desired_az = safe_azimuth(moon_cont_az, state["az"])
            desired_el = state["el_moon"]

            with serial_lock:
                ant.send_rot2_set(ant.ser, desired_az, desired_el)
            set_status("busy", f"Slewing to Moon: Az={desired_az:.1f}°, El={desired_el:.1f}°")

            reached = wait_until_position(desired_az, desired_el, timeout=SLEW_TIMEOUT)
            if not reached:
                set_status("warning", "Initial slew timed out; entering tracking anyway")
            else:
                set_status("success", "On target — starting active tracking")

            # Step 2: ACTIVE TRACKING — gentle, deadbanded corrections
            last_send = 0.0
            while not tracking_stop.is_set():
                # Update moon
                try:
                    azm, elm = CalcMoonPos.get_moon_position()
                    state["az_moon"] = round(azm, 1)
                    state["el_moon"] = round(elm, 1)
                except Exception as e:
                    set_status("warning", f"Moon calc error: {e}")
                    time.sleep(1)
                    continue

                # If Moon dips below limit (and not forced): park and wait to rise again
                if state["el_moon"] < ELEVATION_MIN and not force:
                    go_to_parking()
                    if not wait_for_moon_above():
                        break
                    # re-seed unwrap after long pause
                    last_moon_az = None
                    continue

                # unwrap moon az smoothly
                if last_moon_az is not None:
                    moon_cont_az = unwrap_azimuth(state["az_moon"], last_moon_az)
                else:
                    moon_cont_az = state["az_moon"]
                last_moon_az = state["az_moon"]

                desired_az = safe_azimuth(moon_cont_az, state["az"])
                desired_el = state["el_moon"]

                # read current pos (more timely than waiting for poll loop)
                with serial_lock:
                    try:
                        cur_az, cur_el = ant.read_md01_position()
                    except Exception as e:
                        set_status("error", f"Read error during tracking: {e}")
                        time.sleep(1)
                        continue
                state["az"] = round(cur_az, 1)
                state["az_norm"] = round(state["az"] % 360, 1)
                state["el"] = round(cur_el, 1)

                err_az = ang_err(desired_az % 360, cur_az % 360)
                err_el = desired_el - cur_el

                now = time.time()
                if (abs(err_az) > DEAD_BAND or abs(err_el) > DEAD_BAND) and (now - last_send >= SEND_INTERVAL):
                    with serial_lock:
                        try:
                            ant.send_rot2_set(ant.ser, desired_az, desired_el)
                        except Exception as e:
                            set_status("error", f"Tracking error: {e}")
                            time.sleep(1)
                            continue
                    last_send = now
                    set_status("busy", f"Tracking: Az→{desired_az:.1f}°, El→{desired_el:.1f}° (ΔAz={err_az:.1f}°, ΔEl={err_el:.1f}°)")

                time.sleep(0.25)  # smooth loop

        tracking_thread = threading.Thread(target=_loop, daemon=True)
        tracking_thread.start()
        return jsonify(success=True, tracking=True, status=state["status"])
    else:
        # STOP tracking branch
        tracking_stop.set()
        try:
            if tracking_thread:
                tracking_thread.join(timeout=1)
        except Exception:
            pass
        try:
            with serial_lock:
                ant.stopMovement()
        except Exception:
            pass
        set_status("info", "Tracking and movement stopped")
        return jsonify(success=True, tracking=False, status=state["status"])

# --- Stop & park --------------------------------------------------------------
@app.route("/stop", methods=["POST"])
@api_action
def stop():
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
    except Exception as e:
        set_status("error", f"Error while stopping: {e}")
        return jsonify(success=False, status=state["status"])

@app.route("/park", methods=["POST"])
@api_action
def park():
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
    except Exception as e:
        set_status("error", f"Error while parking: {e}")
        return jsonify(success=False, status=state["status"])

# --- Camera -------------------------------------------------------------------
@app.route("/camera/health")
def camera_health():
    # Try to (re)start gently if not running
    try:
        if not camera.running:
            camera.start()
    except Exception as e:
        try:
            camera.last_error = str(e)
        except Exception:
            pass
    h = camera.get_health()
    ok = h["running"] and (h["has_frame"] or h["last_frame_age"] is not None)
    return jsonify(h), (200 if ok else 503)

@app.route("/video.mjpg")
def video_mjpg():
    # Proactively start so we can 503 cleanly if it fails
    try:
        if not camera.running:
            camera.start()
    except Exception as e:
        try:
            camera.last_error = str(e)
        except Exception:
            pass
        # <img> will fire onerror; frontend shows "No video"
        return Response(status=503)
    # Stream if we can
    return Response(mjpeg_generator(camera, fps=25),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

# --- Main ---------------------------------------------------------------------
if __name__ == "__main__":
    threading.Thread(target=poll_loop, daemon=True).start()
    app.run(debug=True)
