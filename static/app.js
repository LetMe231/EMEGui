// ==================== Drawing Helpers ====================
function drawTicks(ctx, cx, cy, r, startAngle, endAngle, step, labelStep, color, outside=false, elevationMode=false) {
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.font = "11px Arial";
  ctx.textAlign = "center";

  for (let angle = startAngle; angle <= endAngle; angle += step) {
    // Azimuth: 0° = up, clockwise
    // Elevation: 0° = right, counter-clockwise to 90° at top
    const rad = elevationMode 
      ? (-angle) * Math.PI / 180 
      : (angle - 90) * Math.PI / 180;

    const x1 = cx + r * Math.cos(rad);
    const y1 = cy + r * Math.sin(rad);
    const x2 = cx + (r - 10) * Math.cos(rad);
    const y2 = cy + (r - 10) * Math.sin(rad);

    // tick mark
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.lineWidth = 1;
    ctx.stroke();

    // label skip 360° so 0° appears only once
    if (angle % labelStep === 0 && !(angle === endAngle && endAngle === 360)) {
      const offset = outside ? 15 : -25;
      const lx = cx + (r + offset) * Math.cos(rad);
      const ly = cy + (r + offset) * Math.sin(rad);
      ctx.fillText(`${angle}°`, lx, ly + 3);
    }
  }
}



function drawAzimuth(az, azMoon, connected) {
  const c = document.getElementById("azCanvas");
  if (!c) return;
  const ctx = c.getContext("2d");
  ctx.clearRect(0, 0, c.width, c.height);

  const r = 100;                              // define radius of azimuth circle
  const cx = c.width / 2, cy = c.height / 2;  // define center of circle

  const isDark = isDarkMode();
  const color = isDark ? "white" : "black";

  // draw circle
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, 2 * Math.PI);
  ctx.lineWidth = 2;
  ctx.strokeStyle = color;
  ctx.stroke();

  // add ticks + labels
  drawTicks(ctx, cx, cy, r, 0, 360, 30, 90, color, false, false);

  // add title
  ctx.font = "bold 14px Arial";
  ctx.fillStyle = color;
  ctx.textAlign = "center";
  ctx.fillText("Azimuth", cx, cy - r - 15);

  if (connected) {
    // antenna pointer
    let rad = (az - 90) * Math.PI / 180;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + r * Math.cos(rad), cy + r * Math.sin(rad));
    ctx.strokeStyle = isDark ? "deepskyblue" : "blue";
    ctx.lineWidth = 3;
    ctx.stroke();

    // moon pointer
    let radMoon = (azMoon - 90) * Math.PI / 180;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + r * Math.cos(radMoon), cy + r * Math.sin(radMoon));
    ctx.strokeStyle = isDark ? "yellow" : "orange";
    ctx.setLineDash([5, 5]);
    ctx.stroke();
    ctx.setLineDash([]);

    // park position pointer
    let radPark = (40 - 90) * Math.PI / 180;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + r * Math.cos(radPark), cy + r * Math.sin(radPark));
    ctx.strokeStyle = "gray";
    ctx.setLineDash([3, 5]);
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.setLineDash([]);
  } else {
    // cross + "No Data!"
    ctx.strokeStyle = "red";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(cx - r, cy - r);
    ctx.lineTo(cx + r, cy + r);
    ctx.moveTo(cx + r, cy - r);
    ctx.lineTo(cx - r, cy + r);
    ctx.stroke();

    ctx.font = "bold 18px Arial";
    ctx.fillStyle = "red";
    ctx.fillText("No Data!", cx, cy + r + 30);
  }
}

function drawElevation(el, elMoon, connected) {
  // get canvas
  const c = document.getElementById("elCanvas");
  if (!c) return;
  const ctx = c.getContext("2d");
  ctx.clearRect(0, 0, c.width, c.height);

  // draw elevatuion quarter circle
  const Rq = 200;                 // define radius
  const cxCanvas = c.width / 2;   // calculate center of canvas
  const cyCanvas = c.height / 2;
  const left = cxCanvas - 100;
  const top = cyCanvas - 100;
  const bottom = top + 200;
  const cx = left;
  const cy = bottom;

  const isDark = isDarkMode();
  const color = isDark ? "white" : "black";

  // draw quarter arc
  ctx.beginPath();
  ctx.arc(cx, cy, Rq, -Math.PI / 2, 0);
  ctx.lineWidth = 2;
  ctx.strokeStyle = color;
  ctx.stroke();

  // draw ticks + labels
  drawTicks(ctx, cx, cy, Rq, 0, 90, 15, 30, color, true, true);

  // set title
  ctx.font = "bold 14px Arial";
  ctx.fillStyle = color;
  ctx.textAlign = "center";
  ctx.fillText("Elevation", c.width / 2, top - 10);

  if (connected) {
    // antenna pointer
    let rad = el * Math.PI / 180; // 0° = +x, 90° = +y
    let ex = cx + Rq * Math.cos(rad);
    let ey = cy - Rq * Math.sin(rad);
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(ex, ey);
    ctx.strokeStyle = isDark ? "deepskyblue" : "blue";
    ctx.lineWidth = 3;
    ctx.stroke();

    // moon pointer (dashed)
    let radMoon = elMoon * Math.PI / 180;
    let exm = cx + Rq * Math.cos(radMoon);
    let eym = cy - Rq * Math.sin(radMoon);
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(exm, eym);
    ctx.strokeStyle = isDark ? "yellow" : "orange";
    ctx.setLineDash([5, 5]);
    ctx.stroke();
    ctx.setLineDash([]);

    // park position pointer
    let radPark = (60) * Math.PI / 180;
    let px = cx + Rq * Math.cos(radPark);
    let py = cy - Rq * Math.sin(radPark);
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(px, py);
    ctx.strokeStyle = "gray";
    ctx.setLineDash([3, 5]);
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.setLineDash([]);
  } else {
    // cross + "No Data!"
    ctx.strokeStyle = "red";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(left, top);
    ctx.lineTo(cx + 200, bottom);
    ctx.moveTo(cx + 200, top);
    ctx.lineTo(left, bottom);
    ctx.stroke();

    ctx.font = "bold 18px Arial";
    ctx.fillStyle = "red";
    ctx.textAlign = "center";
    ctx.fillText("No Data!", c.width / 2, bottom + 30);
  }
}

// ==================== Status & AJAX ====================
function updateStatusBar(text, success) {
  const statusBar = document.getElementById("status-bar");
  if (!statusBar) return;

  statusBar.innerText = text;
  const isDark = isDarkMode();

  if (isDark) {
    statusBar.style.backgroundColor = "#000";
    if (text.toLowerCase().includes("tracking")) {
      statusBar.style.color = "orange";
    } else {
      statusBar.style.color = success ? "limegreen" : "red";
    }
  } else {
    if (text.toLowerCase().includes("tracking")) {
      statusBar.style.backgroundColor = "orange";
      statusBar.style.color = "black";
    } else {
      statusBar.style.backgroundColor = success ? "green" : "red";
      statusBar.style.color = "white";
    }
  }
}

async function refreshStatus() {
  const isDark = isDarkMode();
  const normalText = isDark ? "white" : "black";
  const moonText   = isDark ? "yellow" : "orange";

  try {
    const res = await fetch("/status");
    const data = await res.json();

    updateStatusBar(data.status, data.connected);

    // DOM refs
    const azText     = document.getElementById("azText");
    const azNormText = document.getElementById("azNormText");
    const azMoonText = document.getElementById("azMoonText");
    const elText     = document.getElementById("elText");
    const elMoonText = document.getElementById("elMoonText");
    const trackerBtn = document.getElementById("trackerBtn");
    const forceChk   = document.getElementById("forceTrackChk");

    // Numbers under canvases
    if (azText) {
      azText.innerText = data.connected ? `Absolute angle: ${(+data.az).toFixed(1)}°` : "Absolute angle: --°";
      azText.style.color = normalText;
    }
    if (azNormText) {
      azNormText.innerText = data.connected ? `Normalized angle: ${(+data.az_norm).toFixed(1)}°` : "Normalized angle: --°";
      azNormText.style.color = normalText;
    }
    if (azMoonText) {
      azMoonText.innerText = `Moon angle: ${(+data.az_moon).toFixed(1)}°`;
      azMoonText.style.color = moonText;
      azMoonText.style.textShadow = isDark ? "0 0 8px yellow" : "";
    }
    if (elText) {
      elText.innerText = data.connected ? `Current angle: ${(+data.el).toFixed(1)}°` : "Current angle: --°";
      elText.style.color = normalText;
    }
    if (elMoonText) {
      const moonLow = (+data.el_moon) < 15;
      const badge = moonLow ? " — paused <15°" : "";
      elMoonText.innerText = `Moon angle: ${(+data.el_moon).toFixed(1)}°${badge}`;
      elMoonText.style.color = moonText;
      elMoonText.style.textShadow = isDark ? "0 0 8px yellow" : "";
    }

    // Tracker button UX (disable if moon < 15° unless forced; also toggle label on active)
    if (trackerBtn) {
      const moonLow = (+data.el_moon) < 15;
      const forced  = forceChk && forceChk.checked;
      const canTrack = !!data.connected && (!moonLow || forced);

      trackerBtn.disabled = !canTrack;
      trackerBtn.title = !canTrack ? "Moon below 15° — tracking paused" : "";

      // Reflect backend tracking state in button text/color
      if (data.tracking) {
        trackerBtn.innerText = "Tracker Stop";
        trackerBtn.classList.remove("btn-success");
        trackerBtn.classList.add("btn-danger");
      } else {
        trackerBtn.innerText = "Tracker Start";
        trackerBtn.classList.remove("btn-danger");
        trackerBtn.classList.add("btn-success");
      }
    }

    // Redraw dials (ensure numeric/boolean types)
    drawAzimuth(+data.az, +data.az_moon, !!data.connected);
    drawElevation(+data.el, +data.el_moon, !!data.connected);

  } catch (e) {
    updateStatusBar(`Error: ${e}`, false);
  }
}
// ===== DARK MODE SYSTEM =====
function isDarkMode() {
  return document.body.classList.contains("dark-mode");
}

function applyThemeLabels() {
  const dark = isDarkMode();
  document.querySelectorAll("[data-label-light]").forEach(el => {
    const txt = dark ? el.dataset.labelDark : el.dataset.labelLight;
    if (txt) {
      el.textContent = txt;
      el.setAttribute("aria-label", txt);
      el.title = txt;
    }
  });
}

function setTheme(dark) {
  document.body.classList.toggle("dark-mode", dark);
  localStorage.setItem("darkMode", dark ? "dark" : "light");
  applyThemeLabels();

  // Redraw graphics with new colors if those functions exist
  if (typeof refreshStatus === "function") refreshStatus();
}



// ===== INIT & EVENT WIRING (single block) =====
document.addEventListener("DOMContentLoaded", () => {
  // Fullscreen toggle for camera
  const camFsBtn = document.getElementById("camFsBtn");
  const camFsContainer = document.getElementById("camFsContainer");
  const camImg = document.getElementById("camStream");

  async function toggleCamFullscreen() {
    try {
      if (!document.fullscreenElement) {
        await (camFsContainer.requestFullscreen
          ? camFsContainer.requestFullscreen()
          : camFsContainer.webkitRequestFullscreen()); // Safari
      } else {
        await (document.exitFullscreen
          ? document.exitFullscreen()
          : document.webkitExitFullscreen()); // Safari
      }
    } catch (e) {
      updateStatusBar("Fullscreen error: " + e, false);
    }
  }

  function setFsButtonLabel() {
    if (camFsBtn) {
      camFsBtn.textContent = document.fullscreenElement ? "⛶ Exit Fullscreen" : "⛶ Fullscreen";
    }
  }

  if (camFsBtn && camFsContainer) {
    camFsBtn.addEventListener("click", toggleCamFullscreen);
    // Double-click the video to toggle, too
    if (camImg) camImg.addEventListener("dblclick", toggleCamFullscreen);

    // Keep label in sync when user presses ESC, etc.
    document.addEventListener("fullscreenchange", setFsButtonLabel);
    document.addEventListener("webkitfullscreenchange", setFsButtonLabel);
    setFsButtonLabel();
  }

  // Dark mode toggle with forced darkmode at start
  setTheme(true);
  localStorage.setItem("darkMode", "dark");
  const darkBtn = document.getElementById("darkModeBtn");
  if (darkBtn) darkBtn.addEventListener("click", () => setTheme(!isDarkMode()));

  // Connect
  const connectForm = document.getElementById("connectForm");
  if (connectForm) {
    connectForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const formData = new FormData(e.target);
      const res = await fetch("/connect", { method: "POST", body: formData });
      const data = await res.json();
      updateStatusBar(data.status, data.success);
      refreshStatus();
    });
  }

  // Disconnect
  const disconnectBtn = document.getElementById("disconnectBtn");
  if (disconnectBtn) {
    disconnectBtn.addEventListener("click", async () => {
      const res = await fetch("/disconnect", { method: "POST" });
      const data = await res.json();
      updateStatusBar(data.status, data.success);
      refreshStatus();
    });
  }

  // Set position
  const setForm = document.getElementById("setForm");
  if (setForm) {
    setForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const formData = new FormData(e.target);
      const res = await fetch("/set", { method: "POST", body: formData });
      const data = await res.json();
      updateStatusBar(data.status, data.success);
      refreshStatus();
    });
  }

  // Tracker
  const trackerBtn = document.getElementById("trackerBtn");
  if (trackerBtn) {
    trackerBtn.addEventListener("click", async () => {
      const force = document.getElementById("forceTrackChk")?.checked ? "1" : "0";
      const res = await fetch(`/tracker?force=${force}`, { method: "POST" });
      const data = await res.json();
      updateStatusBar(data.status, data.success);
      // Button label/color mirror backend state
      if (data.tracking) {
        trackerBtn.innerText = "Tracker Stop";
        trackerBtn.classList.remove("btn-success");
        trackerBtn.classList.add("btn-danger");
      } else {
        trackerBtn.innerText = "Tracker Start";
        trackerBtn.classList.remove("btn-danger");
        trackerBtn.classList.add("btn-success");
      }
      refreshStatus();
    });
  }

  // Stop all
  const stopBtn = document.getElementById("stopBtn");
  if (stopBtn) {
    stopBtn.addEventListener("click", async () => {
      const res = await fetch("/stop", { method: "POST" });
      const data = await res.json();
      updateStatusBar(data.status, data.success);
      refreshStatus();
    });
  }

  // Park
  const parkBtn = document.getElementById("parkBtn");
  if (parkBtn) {
    parkBtn.addEventListener("click", async () => {
      const res = await fetch("/park", { method: "POST" });
      const data = await res.json();
      updateStatusBar(data.status, data.success);
      refreshStatus();
    });
  }

  // First draw + periodic refresh
  refreshStatus();
  setInterval(refreshStatus, 2000);
});

// --- Status Bar Controller ----------------------------------------------------
(function () {
  const bar = document.getElementById("status-bar");
  if (!bar) return;

  const cls = l => `statusbar statusbar--${l || "info"}`;
  function setStatus(level, text) {
    bar.textContent = text;
    bar.className = cls(level);
    bar.setAttribute("data-level", level);
    bar.setAttribute("aria-live", "polite");
  }

  async function poll() {
    try {
      const r = await fetch("/status", { cache: "no-store" });
      const s = await r.json();
      setStatus(s.status_level || "info", s.status || "");
    } catch (e) {
      setStatus("error", "Lost connection to server");
    } finally {
      setTimeout(poll, 1000);
    }
  }
  poll();

  // Optional: optimistic "busy" hint on actions the user triggers
  const busy = () => setStatus("busy", "Working…");
  [["connectForm","submit"],["setForm","submit"],
   ["trackerBtn","click"],["stopBtn","click"],
   ["parkBtn","click"],["disconnectBtn","click"]]
   .forEach(([id, evt]) => {
     const el = document.getElementById(id);
     if (!el) return;
     el.addEventListener(evt, busy, { capture: true });
   });

  // Optional: surface network/HTTP errors globally
  const _fetch = window.fetch;
  window.fetch = async (...args) => {
    try {
      const res = await _fetch(...args);
      if (!res.ok) setStatus("error", `HTTP ${res.status} ${res.statusText}`);
      return res;
    } catch (e) {
      setStatus("error", `Network error: ${e.message}`);
      throw e;
    }
  };
})();

// --- Camera health / overlay --------------------------------------------------
(() => {
  const img = document.getElementById("camStream");
  const overlay = document.getElementById("camOverlay");
  if (!img || !overlay) return;

  let lastReload = 0;

  function showOverlay(on) { overlay.hidden = !on; }

  img.addEventListener("error", () => {
    showOverlay(true);
    // throttle reloads
    const now = Date.now();
    if (now - lastReload > 4000) {
      lastReload = now;
      // cache-bust so the browser re-requests the stream
      img.src = "/video.mjpg?ts=" + Date.now();
    }
  });

  img.addEventListener("load", () => {
    // When an mjpeg stream loads, 'load' fires once. We still poll health below.
    showOverlay(false);
  });

  async function pollCam() {
    try {
      const r = await fetch("/camera/health", { cache: "no-store" });
      const j = await r.json();
      const ok = r.ok && (j.has_frame || j.last_frame_age !== null);
      showOverlay(!ok);
      // if unhealthy, nudge the <img> to reconnect every few seconds
      if (!ok && Date.now() - lastReload > 4000) {
        lastReload = Date.now();
        img.src = "/video.mjpg?ts=" + Date.now();
      }
    } catch {
      showOverlay(true);
    } finally {
      setTimeout(pollCam, 2000);
    }
  }
  pollCam();
})();
