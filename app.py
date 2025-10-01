from flask import Flask, render_template, jsonify, request
import serial.tools.list_ports
import threading, time
serial_lock = threading.Lock()

# import your existing backend modules
from serialComm import SerialAntenna
import CalcMoonPos

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
                # Read current position for display
                with serial_lock:
                    az, el = ant.read_md01_position()
                state["az"] = round(az, 1)
                state["el"] = round(el, 1)
                fail_count = 0

                # If tracking, command moon setpoint
                if state["tracking"] and state["el_moon"] >= 15:
                    with serial_lock:
                        ant.send_rot2_set(ant.ser, state["az_moon"], state["el_moon"])
                    state["status"] = (f"Tracking... Az={state['az_moon']:.1f}°, "
                                       f"El={state['el_moon']:.1f}°")

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

        time.sleep(0.5)

        # Always refresh moon pos
        try:
            azm, elm = CalcMoonPos.get_moon_position()
            state["az_moon"] = round(azm, 1)
            state["el_moon"] = round(elm, 1)
        except Exception as e:
            print(f"[MOON ERROR] {e}")

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
    global ant
    if ant:
        try:
            # Park before closing
            with serial_lock:
                ant.send_rot2_set(ant.ser, 18, 60)
                ant.stopMovement()
            time.sleep(0.3)  # small flush delay
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
def tracker():
    global ant
    if not ant:
        return jsonify(success=False, status="Controller nicht verbunden!")

    state["tracking"] = not state["tracking"]
    if state["tracking"]:
        state["status"] = "Tracking gestartet"
    else:
        try:
            with serial_lock:
                ant.stopMovement()
        except Exception as e:
            print(f"[TRACKER STOP ERROR] {e}")
        state["status"] = "Tracking gestoppt, Bewegung gestoppt"
    return jsonify(success=True, tracking=state["tracking"], status=state["status"])


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
            ant.send_rot2_set(ant.ser, 18, 60)   # Park at Az=18, El=60
            ant.stopMovement()
        state["status"] = "Parkposition angefahren"
        return jsonify(success=True, status=state["status"])
    except Exception as e:
        return jsonify(success=False, status=f"Fehler beim Parken: {e}")



if __name__ == "__main__":
    threading.Thread(target=poll_loop, daemon=True).start()
    app.run(debug=True)