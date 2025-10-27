from flask import Flask, render_template, jsonify, request, Response
from camera import CameraStream, mjpeg_generator
import serial.tools.list_ports
import threading, time
# import your existing backend modules
from serialComm import SerialAntenna
import CalcMoonPos

serial_lock = threading.Lock()
CAMERA_SOURCE = "rtsp://admin:EME_2025@192.168.0.3:554/h264Preview_01_main"
camera = CameraStream(src=CAMERA_SOURCE, jpeg_quality=80)

# Tracking worker
tracking_thread = None
tracking_stop = threading.Event()

PARKAZ = 285
PARKEL = 60

app = Flask(__name__)

# Shared antenna state
state = {
    "connected": False,
    "status": "Nicht verbunden",
    "az": 0.0,
    "el": 0.0,
    "az_moon": 0.0,
    "el_moon": 0.0,
    "tracking": False,
    "port": None
}

ant = None

# -------- Background polling loop --------
def poll_loop():
    global ant, state
    fail_count = 0
    while True:
        if state["connected"] and ant:
            try:
                # Read current position
                with serial_lock:
                    az, el = ant.read_md01_position()
                state["az"] = round(az, 1)
                state["el"] = round(el, 1)
                fail_count = 0
            except Exception as e:
                fail_count += 1
                state["status"] = f"Lesefehler ({fail_count})"
                if fail_count >= 3:
                    try:
                        with serial_lock:
                            ant.close()
                    except:
                        pass
                    ant = None
                    state["connected"] = False
                    state["status"] = f"Verbindung verloren: {e}"
                    fail_count = 0
                time.sleep(2)  # backoff on error
        else:
            time.sleep(1)

        # Always refresh moon position
        try:
            azm, elm = CalcMoonPos.get_moon_position()
            state["az_moon"] = round(azm, 1)
            state["el_moon"] = round(elm, 1)
        except Exception:
            pass

        time.sleep(1)

def tracking_loop():
    """Send moon setpoints periodically while tracking is ON."""
    global ant, state
    while not tracking_stop.is_set():
        if not (state["connected"] and ant):
            time.sleep(1)
            continue

        # refresh moon pos (extra guard; poll_loop also does this)
        try:
            azm, elm = CalcMoonPos.get_moon_position()
            state["az_moon"] = round(azm, 1)
            state["el_moon"] = round(elm, 1)
        except Exception:
            pass

        try:
            if state["el_moon"] >= 15:
                with serial_lock:
                    ant.send_rot2_set(ant.ser, state["az_moon"], state["el_moon"])
                state["status"] = f"Tracking... Az={state['az_moon']:.1f}°, El={state['el_moon']:.1f}°"
            else:
                state["status"] = "Tracking pausiert (Mond < 15°)"
        except Exception as e:
            state["status"] = f"Tracking-Fehler: {e}"

        # send every 5s (adjust if you want tighter following)
        for _ in range(5):
            if tracking_stop.is_set():
                break
            time.sleep(1)



threading.Thread(target=poll_loop, daemon=True).start()

# -------- Flask Routes --------
@app.route("/")
def index():
    ports = [p.device for p in serial.tools.list_ports.comports()]
    return render_template("index.html", state=state, ports=ports)

@app.route("/status")
def status():
    return jsonify(state)

@app.route("/connect", methods=["POST"])
def connect():
    global ant
    port = request.form.get("port")
    try:
        ant = SerialAntenna(port)
        # Check opened
        if not ant.status():
            raise Exception("Port konnte nicht geöffnet werden")
        # Validate comms with a real read
        with serial_lock:
            az, el = ant.read_md01_position()

        state["port"] = port
        state["connected"] = True
        state["az"] = round(az, 1)
        state["el"] = round(el, 1)
        state["status"] = f"Verbunden mit {port} (Az={az:.1f}°, El={el:.1f}°)"
        return jsonify(success=True, status=state["status"])
    except Exception as e:
        if ant:
            try:
                with serial_lock:
                    ant.close()
            except:
                pass
        ant = None
        state["connected"] = False
        state["status"] = f"Verbindung fehlgeschlagen: {e}"
        return jsonify(success=False, status=state["status"])


@app.route("/disconnect", methods=["POST"])
def disconnect():
    global ant, tracking_thread, tracking_stop
    # stop tracking worker
    tracking_stop.set()
    try:
        if tracking_thread:
            tracking_thread.join(timeout=1)
    except:
        pass

    if ant:
        try:
            with serial_lock:
                ant.send_rot2_set(ant.ser, 0, 0)
                ant.stopMovement()
            time.sleep(0.3)
        except Exception as e:
            print(f"[WARN] Park/Stop failed on disconnect: {e}")
        try:
            with serial_lock:
                ant.close()
        except:
            pass
        ant = None

    state["connected"] = False
    state["tracking"] = False
    state["status"] = "Nicht verbunden (Parkposition gesendet)"
    state["az"] = 0.0
    state["el"] = 0.0
    return jsonify(success=True, status=state["status"])


@app.route("/set", methods=["POST"])
def set_position():
    global ant
    try:
        az = float(request.form["az"])
        el = float(request.form["el"])
        if not ant:
            raise Exception("Nicht verbunden")

        with serial_lock:
            ant.send_rot2_set(ant.ser, az, el)

        state["status"] = f"Az={az:.1f}°, El={el:.1f}° gesetzt"
        return jsonify(success=True, status=state["status"])
    except Exception as e:
        return jsonify(success=False, status=f"Fehler: {e}")
    
@app.route("/tracker", methods=["POST"])
@app.route("/tracker", methods=["POST"])
def tracker():
    global ant, tracking_thread, tracking_stop
    if not (state["connected"] and ant):
        return jsonify(success=False, status="Controller nicht verbunden!")

    force = request.args.get("force", "0") == "1"
    state["tracking"] = not state["tracking"]

    if state["tracking"]:
        # start (or restart) worker
        if tracking_thread and tracking_thread.is_alive():
            tracking_stop.set()
            try: tracking_thread.join(timeout=1)
            except: pass
        tracking_stop.clear()

        def tracking_loop():
            while not tracking_stop.is_set():
                if not (state["connected"] and ant):
                    time.sleep(1); continue
                # update moon pos
                try:
                    azm, elm = CalcMoonPos.get_moon_position()
                    state["az_moon"] = round(azm, 1)
                    state["el_moon"] = round(elm, 1)
                except: pass

                if state["el_moon"] >= 15 or force:
                    try:
                        with serial_lock:
                            ant.send_rot2_set(ant.ser, state["az_moon"], state["el_moon"])
                        state["status"] = f"Tracking... Az={state['az_moon']:.1f}°, El={state['el_moon']:.1f}°"
                    except Exception as e:
                        state["status"] = f"Tracking-Fehler: {e}"
                else:
                    state["status"] = "Tracking pausiert (Mond < 15°)"

                for _ in range(5):
                    if tracking_stop.is_set(): break
                    time.sleep(1)

        import threading
        tracking_thread = threading.Thread(target=tracking_loop, daemon=True)
        tracking_thread.start()
        return jsonify(success=True, tracking=True, status="Tracking gestartet")
    else:
        tracking_stop.set()
        try:
            if tracking_thread:
                tracking_thread.join(timeout=1)
        except: pass
        try:
            with serial_lock:
                ant.stopMovement()
        except: pass
        return jsonify(success=True, tracking=False, status="Tracking gestoppt, Bewegung gestoppt")


@app.route("/stop", methods=["POST"])
def stop():
    global ant
    if not ant:
        return jsonify(success=False, status="Controller nicht verbunden!")
    try:
        with serial_lock:
            ant.stopMovement()
        state["tracking"] = False
        state["status"] = "Bewegung gestoppt"
        return jsonify(success=True, status=state["status"])
    except Exception as e:
        print(f"[STOP ERROR] {e}")
        return jsonify(success=False, status=f"Fehler beim Stoppen: {e}")
    
@app.route("/park", methods=["POST"])
def park():
    global ant
    if not ant:
        return jsonify(success=False, status="Controller nicht verbunden!")
    try:
        with serial_lock:
            ant.send_rot2_set(ant.ser, PARKAZ, PARKEL)   
            ant.stopMovement()
        state["status"] = "Parkposition angefahren"
        return jsonify(success=True, status=state["status"])
    except Exception as e:
        return jsonify(success=False, status=f"Fehler beim Parken: {e}")

@app.route("/camera/start", methods=["POST"])
def camera_start():
    try:
        camera.start()
        return jsonify(success=True, status="Kamera gestartet")
    except Exception as e:
        return jsonify(success=False, status=f"Kamera-Fehler: {e}")

@app.route("/camera/stop", methods=["POST"])
def camera_stop():
    try:
        camera.stop()
        return jsonify(success=True, status="Kamera gestoppt")
    except Exception as e:
        return jsonify(success=False, status=f"Kamera-Fehler: {e}")

@app.route("/video.mjpg")
def video_mjpg():
    return Response(mjpeg_generator(camera, fps=25),
                    mimetype="multipart/x-mixed-replace; boundary=frame")



if __name__ == "__main__":
    threading.Thread(target=poll_loop, daemon=True).start()
    app.run(debug=True)