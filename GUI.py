from tkinter import ttk, messagebox
import tkinter as tk
import threading, queue, time
import serial.tools.list_ports
import math

from serialComm import SerialAntenna
import CalcMoonPos
import widgets as wdg


class SimpleAntennaGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MD-01 Controller v0.1")
        self.geometry("600x600")

        self.COLORS = { "pointer": "blue", "error": "red", "connected": "green", "tracking": "orange", "cross": "red", "posSet": "green" }
        
        # Positions of Az/El display
        self.el_center_x = 350
        self.el_center_y = 170
        self.el_radius = 140

        self.az_center_x = 220
        self.az_center_y = 100
        self.az_radius = 70


        self.tracking = False
        self.connected = False
        self.ant = None

        self.status_var = tk.StringVar(value="Nicht verbunden")
        self.port_var = tk.StringVar(value="COM3")

        #Initialize handler queues for multi threading
        self.pos_queue = queue.Queue()
        self.cmd_queue = queue.Queue()
        self.reader_thread = None
        self.stop_reader = threading.Event()

        self.POLL_INTERVAL = 1.0

        #initialize Az and El values for Manual and Tracking input
        self.az_tracking = 0.0
        self.el_tracking = 0.0
        self.az_manual = tk.DoubleVar(value=0.0)
        self.el_manual = tk.DoubleVar(value=0.0)
        self.az_moon, self.el_moon = CalcMoonPos.get_moon_position()

        # Eingabefelder
        ttk.Label(self, text="Azimuth (0-359°):").pack(pady=(10, 0))
        self.az_entry = ttk.Spinbox(self, from_=0, to=359, textvariable=self.az_manual)
        self.az_entry.pack()

        ttk.Label(self, text="Elevation (0-90°):").pack(pady=(10, 0))
        self.el_entry = ttk.Spinbox(self, from_=0, to=90, textvariable=self.el_manual)
        self.el_entry.pack()



        ports = [p.device for p in serial.tools.list_ports.comports()]
        ttk.Label(self, text="COM-Port").pack(pady=(10, 0))
        self.port_entry = ttk.Combobox(self, textvariable=self.port_var, values=ports)
        self.port_entry.pack()

        # Buttons
        self.connect_btn = ttk.Button(self, text="Verbinden", command=self.toggle_connect)
        self.connect_btn.pack(pady=5)

        self.set_btn = ttk.Button(self, text="Setzen", command=self.toggle_set)
        self.set_btn.pack(pady=5)
        self.set_btn.state(["disabled"])

        self.disconnect_btn = ttk.Button(self, text="Trennen", command=self.toggle_disconnect)
        self.disconnect_btn.pack(pady=5)
        self.disconnect_btn.state(["disabled"])

        self.tracker_btn = ttk.Button(self, text="Tracker Start", command=self.toggle_tracker)
        self.tracker_btn.pack(pady=5)
        self.tracker_btn.state(["disabled"])

        self.stop_btn = ttk.Button(self, text="Stop all movement", command=self.stop_movement)
        self.stop_btn.pack(pady=5)
        self.stop_btn.state(["disabled"])

        # Canvas für Anzeigen
        self.canvas = tk.Canvas(self, width=600, height=400)
        self.canvas.pack(pady=10)

        # ---- Azimuth-Kreis ----
        self.az_text = self.canvas.create_text(self.az_center_x, 
                                               self.az_center_y - 90, 
                                               text="Azimuth", font=("Arial", 10, "bold"))
        self.az_circle = wdg.draw_smooth_arc(self.canvas, 
                                             self.az_center_x, 
                                             self.az_center_y, 
                                             self.az_radius, 
                                             start=0, extent=360, width=1)
        self.az_valDisp = self.canvas.create_text(self.az_center_x, 
                                               self.az_center_y + 90, 
                                               text=f'Current angle: --', font=("Arial", 10, "bold"))
        self.az_moonDisp = self.canvas.create_text(self.az_center_x, 
                                               self.az_center_y + 110, 
                                               text=f'Current moon angle: --', font=("Arial", 10, "bold"))
        
        # ----Azimuth-Anzeige ----
        self.az_pointer = wdg.draw_smooth_line(self.canvas, 
                                               self.az_center_x, 
                                               self.az_center_y, 
                                               self.az_center_x, 
                                               self.az_center_y - self.az_radius, 
                                               width=1, color=(0, 0, 0, 0))
        
        # ---- Elevation-Halbkreis ----
        self.el_text = self.canvas.create_text(self.el_center_x + self.el_radius / 2, 
                                               self.el_center_y - self.el_radius - 20, 
                                               text="Elevation", font=("Arial", 10, "bold"))
        self.el_arc = wdg.draw_smooth_arc(self.canvas, 
                                          self.el_center_x, 
                                          self.el_center_y, 
                                          self.el_radius, 
                                          start=270, extent=90, width=1)
        self.el_valDisp = self.canvas.create_text(self.el_center_x + self.el_radius/2, 
                                               self.el_center_y + 20, 
                                               text=f'Current angle: --', font=("Arial", 10, "bold"))
        self.el_moonDisp = self.canvas.create_text(self.el_center_x + self.el_radius/2, 
                                               self.el_center_y + 40, 
                                               text=f'Current moon angle: --', font=("Arial", 10, "bold"))
        
        # ----Elevation-Anzeige ----
        self.el_pointer = wdg.draw_smooth_line(self.canvas, 
                                               self.el_center_x, 
                                               self.el_center_y,
                                                self.el_center_x + self.el_radius, 
                                                self.el_center_y, 
                                                width=1, color=(0, 0, 0, 0))

        # Statusleiste
        self.status_label = ttk.Label(self, 
                                      textvariable=self.status_var, 
                                      relief=tk.SUNKEN,
                                      anchor='center', 
                                      foreground=self.COLORS["error"]
        )
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        
        # --- Initiale Anzeige ---
        self.update_display(self.az_manual.get(), self.el_manual.get())

    def toggle_connect(self):
        try:
            self.ant = SerialAntenna(self.port_var.get())
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler bei der Verbindung: {e}")
            self.status_label.config(foreground=self.COLORS["error"])
            return
        if self.ant.status():
            self.connected = True

            # Update Status Bar
            self.status_var.set("Verbunden")
            self.status_label.config(foreground=self.COLORS["connected"])

            # Read initial position from controller
            try:
                az, el = self.ant.read_md01_position()
                self.az_manual.set(round(az, 1))
                self.el_manual.set(round(el, 1))
            except Exception as e:
                self.status_var.set(f"Position lesen fehlgeschlagen: {e}")

            # Update Buttons
            self.disconnect_btn.state(["!disabled"])
            self.set_btn.state(["!disabled"])
            if self.el_moon >= 15:
                self.tracker_btn.state(["!disabled"])
            self.connect_btn.state(["disabled"])
            self.stop_btn.state(["!disabled"])

            # Start background reader
            self.stop_reader.clear()
            self.reader_thread = threading.Thread(target=self.reader_loop, daemon=True)
            self.reader_thread.start()
            self.after(200, self.process_queue)  # periodically check results
        else:
            messagebox.showerror("Fehler", "Probleme bei der Verbindung.")
            self.status_var.set("Verbindung fehlgeschlagen")
            self.status_label.config(foreground=self.COLORS["error"])

    def toggle_set(self):
        try:
            if not self.connected:
                raise ConnectionError
            
            # Read Az/El values from input text
            az = float(self.az_manual.get())
            el = float(self.el_manual.get())

            # Sanity check values
            if not (0 <= az <= 359) or not (0 <= el <= 90):
                raise ValueError

            # Send Positions to MD-01 Controller
            self.cmd_queue.put(("set", az, el))
            
            # Anzeige updaten
            self.status_var.set(f"Az={az:.1f}°, El={el:.1f}° gesetzt")
            self.status_label.config(foreground=self.COLORS["posSet"])

        except ValueError:
            messagebox.showerror("Fehler", "Bitte gültige Werte eingeben (Az 0-359, El 0-90).")
            self.status_var.set("Fehlerhafte Eingabe")
            self.status_label.config(foreground=self.COLORS["error"])
            return
        except ConnectionError:
            messagebox.showerror("Fehler", "Controller nicht verbunden!")
            self.status_label.config(foreground=self.COLORS["error"])
            return

    def toggle_disconnect(self):
        if self.ant:
            self.stop_reader.set()
            if self.reader_thread:
                self.reader_thread.join(timeout=1)
                self.reader_thread = None

            self.tracking = False
            self.ant.close()

            # Update Buttons
            self.disconnect_btn.state(["disabled"])
            self.set_btn.state(["disabled"])
            self.tracker_btn.state(["disabled"])
            self.connect_btn.state(["!disabled"])
            self.stop_btn.state(["disabled"])

        if self.ant.status():
            messagebox.showerror("Fehler", "Trennen nicht erfolgreich")
            self.status_label.config(foreground=self.COLORS["error"])
        else:
            self.connected = False
            self.status_var.set("Nicht verbunden")
            self.status_label.config(foreground=self.COLORS["error"])
            # Update Displays
            self.update_display(0.0, 0.0)

    def toggle_tracker(self):
        if not self.connected:
            messagebox.showerror("Fehler", "Controller nicht verbunden!")
            self.status_label.config(foreground=self.COLORS["error"])
            return

        self.tracking = not self.tracking

        if self.tracking:
            self.tracker_btn.config(text="Tracker Stop")
            # Disable manual Input
            self.az_entry.state(["disabled"])
            self.el_entry.state(["disabled"])
            if self.el_moon >= 15:
                self.moon_tracking()
            else:
                self.cmd_queue.put("error", "Moon too low")
        else:
            self.tracker_btn.config(text="Tracker Start")
            
            # Stop automatic tracking
            self.stop_movement()
            
            # Update Status Bar
            self.status_var.set("Tracking gestoppt")
            self.status_label.config(foreground=self.COLORS["connected"]) 

            # Save last tracked values as manual
            self.az_manual.set(round(self.az_tracking, 1))
            self.el_manual.set(round(self.el_tracking, 1))

            # Read last position from controller
            try:
                az, el = self.ant.read_md01_position()
                self.az_manual.set(round(az, 1))
                self.el_manual.set(round(el, 1))
            except Exception as e:
                self.status_var.set(f"Position lesen fehlgeschlagen: {e}")
            # Enable manual Input
            self.az_entry.state(["!disabled"])
            self.el_entry.state(["!disabled"])

    def safe_call(self, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            self.status_var.set(f"Fehler: {e}")
            self.status_label.config(foreground=self.COLORS["error"])
            return None


    def stop_movement(self):
        if not self.connected:
            messagebox.showerror("Fehler", "Controller nicht verbunden!")
            self.status_label.config(foreground=self.COLORS["error"])
            return
        try:
            self.cmd_queue.put(("stop",))
            self.status_var.set("Bewegung gestoppt")
            self.status_label.config(foreground=self.COLORS["error"])
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Stoppen: {e}")
            self.status_label.config(foreground=self.COLORS["error"])
            return

    def moon_tracking(self):
        if self.tracking:
            try:
                self.az_tracking, self.el_tracking = CalcMoonPos.get_moon_position()
                if self.el_tracking <= 15:
                  
                    return
                self.cmd_queue.put(("set", self.az_tracking, self.el_tracking))
                self.status_var.set(f"Tracking... Az={self.az_tracking:.1f}°, El={self.el_tracking:.1f}°")
                self.status_label.config(foreground=self.COLORS["tracking"])
            except Exception as e:
                messagebox.showerror("Fehler", f"Tracker-Fehler: {e}")
                self.status_label.config(foreground=self.COLORS["error"])
                return
            finally:
                if self.tracking:
                    self.after(10000, self.moon_tracking)

    def reader_loop(self):
        """Background thread: handle commands + poll current position"""
        while not self.stop_reader.is_set():
            if not self.connected:
                # Try to reconnect
                self.pos_queue.put(("status", "Reconnecting..."))
                try:
                    self.ant = SerialAntenna(self.port_var.get())
                    if self.ant.status():
                        self.connected = True
                        self.pos_queue.put(("status", "Verbunden"))
                    else:
                        time.sleep(3)  # wait before retry
                        continue
                except Exception as e:
                    self.pos_queue.put(("error", f"Reconnect failed: {e}"))
                    self.connected = False
                    time.sleep(3)
                    continue
            try:
                # Handle queued commands first
                try:
                    cmd = self.cmd_queue.get_nowait()
                    if cmd[0] == "set":
                        az, el = cmd[1], cmd[2]
                        self.ant.send_rot2_set(self.ant.ser, az, el)
                    elif cmd[0] == "stop":
                        self.ant.stopMovement()
                except queue.Empty:
                    pass

                # Poll current position
                if self.connected:
                    az, el = self.ant.read_md01_position()
                    self.pos_queue.put((az, el))

            except Exception as e:
                self.pos_queue.put(("error", str(e)))
                time.sleep(3)  # backoff on error

            time.sleep(self.POLL_INTERVAL)  # polling interval

    def process_queue(self):
        """Process data from reader thread and update GUI"""
        try:
            while True:
                item = self.pos_queue.get_nowait()
                if item[0] == "status":
                    if "Reconnect" in item[1]:
                        self.status_label.config(foreground=self.COLORS["tracking"])
                    else:
                        self.status_var.set(item[1])
                        self.status_label.config(foreground=self.COLORS["connected"])
                elif item[0] == "error":
                    self.status_var.set(item[1])
                    self.status_label.config(foreground=self.COLORS["error"])
                    # Reset buttons to disconnected state
                    self.disconnect_btn.state(["disabled"])
                    self.set_btn.state(["disabled"])
                    self.tracker_btn.state(["disabled"])
                    self.connect_btn.state(["!disabled"])
                    self.stop_btn.state(["disabled"])
                    self.connected = False
                else:
                    az, el = item
                    self.update_display(az, el)
        except queue.Empty:
            pass

        if not self.stop_reader.is_set():
            self.after(200, self.process_queue)  # reschedule

    def update_display(self, az, el):
        """Aktualisiert die grafische Anzeige auf dem Canvas"""
        
        if self.connected:
            # Remove "No Data" indicators if present
            if hasattr(self, 'azCross1'):
                self.canvas.delete(self.azCross1)
                self.canvas.delete(self.azCross2)
                self.canvas.delete(self.azNodata)
                del self.azCross1, self.azCross2, self.azNodata
            if hasattr(self, 'elCross1'):
                self.canvas.delete(self.elCross1)
                self.canvas.delete(self.elCross2)
                self.canvas.delete(self.elNodata)
                del self.elCross1, self.elCross2, self.elNodata
            # ---- Azimuth ----
            angle_rad = math.radians(az - 90)  # 0° nach oben
            x = self.az_center_x + self.az_radius * math.cos(angle_rad)
            y = self.az_center_y + self.az_radius * math.sin(angle_rad)
            self.canvas.delete(self.az_pointer)
            self.az_pointer = wdg.draw_smooth_line(self.canvas,
                                            self.az_center_x, self.az_center_y,
                                            x, y, width=2, color=self.COLORS["pointer"])
            self.canvas.itemconfig(self.az_valDisp, text=f"Current angle: {az:.1f}°")
            self.canvas.itemconfig(self.az_moonDisp, text=f"Current Moon angle: {self.az_moon:.1f}°")

            # ---- Elevation pointer ----
            angle_rad = math.radians(el)
            x = self.el_center_x + self.el_radius * math.cos(angle_rad)
            y = self.el_center_y - self.el_radius * math.sin(angle_rad)
            self.canvas.delete(self.el_pointer) # Remove old pointer
            self.el_pointer = wdg.draw_smooth_line(self.canvas,
                                            self.el_center_x, self.el_center_y,
                                            x, y, width=2, color=self.COLORS["pointer"])
            self.canvas.itemconfig(self.el_valDisp, text=f"Current angle: {el:.1f}°")
            self.canvas.itemconfig(self.el_moonDisp, text=f"Current Moon angle: {self.el_moon:.1f}°")
        else:
            self.azCross1 = wdg.draw_smooth_line(self.canvas, 
                                  self.az_center_x + self.az_radius, 
                                  self.az_center_y - self.az_radius, 
                                  self.az_center_x - self.az_radius, 
                                  self.az_center_y + self.az_radius,
                                  3, self.COLORS["cross"])
            self.azCross2 =wdg.draw_smooth_line(self.canvas, 
                                  self.az_center_x + self.az_radius, 
                                  self.az_center_y + self.az_radius, 
                                  self.az_center_x - self.az_radius, 
                                  self.az_center_y - self.az_radius,
                                  3, self.COLORS["cross"])
            self.azNodata = self.canvas.create_text(self.az_center_x, 
                                                    self.az_center_y, 
                                                    text="No Data!", 
                                                    font=("Arial", 20, "bold"))
            self.elCross1 = wdg.draw_smooth_line(self.canvas, 
                                  self.el_center_x + self.el_radius, 
                                  self.el_center_y - self.el_radius, 
                                  self.el_center_x, 
                                  self.el_center_y,
                                  3, self.COLORS["cross"])
            self.elCross2 = wdg.draw_smooth_line(self.canvas, 
                                  self.el_center_x, 
                                  self.el_center_y - self.el_radius, 
                                  self.el_center_x + self.el_radius, 
                                  self.el_center_y,
                                  3, self.COLORS["cross"])
            self.elNodata = self.canvas.create_text(self.el_center_x + self.el_radius/2, self.el_center_y - self.el_radius/2, text="No Data!", font=("Arial", 20, "bold"))

            self.canvas.itemconfig(self.az_valDisp, text=f"Current angle: --°")
            self.canvas.itemconfig(self.el_valDisp, text=f"Current angle: --°")
            self.canvas.itemconfig(self.az_moonDisp, text=f"Current Moon angle: {self.az_moon:.1f}°")
            self.canvas.itemconfig(self.el_moonDisp, text=f"Current Moon angle: {self.el_moon:.1f}°")
            self.canvas.delete(self.el_pointer)
            self.canvas.delete(self.az_pointer) 


if __name__ == "__main__":
    app = SimpleAntennaGUI()
    app.mainloop()
