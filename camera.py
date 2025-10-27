# camera.py
import cv2
import threading
import time
import os

class CameraStream:
    """
    Simple thread-based camera reader that exposes latest JPEG frame.
    Works with RTSP/HTTP URLs or a local device index (e.g., 0).
    """
    def __init__(self, src=None, jpeg_quality=80, width=None, height=None):
        self.src = src or os.getenv("CAMERA_SOURCE", 0)  # default to device 0
        self.jpeg_quality = int(jpeg_quality)
        self.width = width
        self.height = height

        self.cap = None
        self.lock = threading.Lock()
        self.frame = None
        self.running = False
        self.thread = None

    def start(self):
        if self.running:
            return
        self.cap = cv2.VideoCapture(self.src)
        if not self.cap.isOpened():
            raise RuntimeError(f"Kamera-Quelle konnte nicht geöffnet werden: {self.src}")
        self.running = True
        self.thread = threading.Thread(target=self._reader, daemon=True)
        self.thread.start()

    def _reader(self):
        while self.running:
            ok, frame = self.cap.read()
            if not ok:
                # small backoff on failure; try again
                time.sleep(0.1)
                continue
            # optional resize
            if self.width and self.height:
                frame = cv2.resize(frame, (self.width, self.height))
            with self.lock:
                self.frame = frame

    def get_jpeg(self):
        with self.lock:
            if self.frame is None:
                return None
            ok, buf = cv2.imencode(".jpg", self.frame, [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality])
            if not ok:
                return None
            return buf.tobytes()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
            self.thread = None
        if self.cap:
            try:
                self.cap.release()
            except:
                pass
            self.cap = None


# ---- Helpers for Flask integration ----

def mjpeg_generator(cam: CameraStream, fps=25):
    """
    Multipart JPEG generator for Flask Response.
    Starts the camera on-demand.
    """
    if not cam.running:
        cam.start()
    delay = 1.0 / float(fps)
    boundary = b"--frame\r\n"
    while True:
        jpeg = cam.get_jpeg()
        if jpeg is None:
            time.sleep(0.05)
            continue
        yield boundary + b"Content-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
        time.sleep(delay)
