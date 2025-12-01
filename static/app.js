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
window.APP_CAN_EDIT = document.body.dataset.canEdit === "1";

function updateStatusBar(text, success, levelOverride) {
  const statusBar = document.getElementById("status-bar");
  if (!statusBar) return;

  statusBar.innerText = text || "";

  // Decide visual level
  let level = levelOverride;
  const t = (text || "").toLowerCase();

  if (!level) {
    if (t.includes("error") || t.includes("failed") || success === false) {
      level = "error";
    } else if (t.includes("tracking") || t.includes("working")) {
      level = "busy";
    } else if (success === true) {
      level = "ok";
    } else {
      level = "info";
    }
  }

  statusBar.setAttribute("data-level", level);
  statusBar.className = `statusbar statusbar--${level}`;
}


async function refreshStatus() {
  const isDark = isDarkMode();
  const normalText = isDark ? "white" : "black";
  const moonText   = isDark ? "yellow" : "orange";

  try {
    const res = await fetch("/status");
    const data = await res.json();

    updateStatusBar(data.status, data.connected);
    
    // ----- Connection card UI -----
    const connDot        = document.getElementById("connection-dot");
    const connStatusText = document.getElementById("connection-status-text");
    const connPortText   = document.getElementById("connection-port-text");
    const connectBtn     = document.querySelector("#connectForm button[type='submit']");
    const disconnectBtn  = document.getElementById("disconnectBtn");
    const portSelect     = document.querySelector("#connectForm select[name='port']");


        // ----- View-only connection card (data view) -----
    const viewConnDot   = document.getElementById("conn-dot");
    const viewConnLabel = document.getElementById("conn-label");
    const viewPortText  = document.getElementById("view-port-text");
    const viewConnectBtn = document.querySelector("#viewConnectForm button[type='submit']");
    const viewPortSelect = document.querySelector("#viewConnectForm select[name='port']");

    if (viewConnDot) {
      // Reuse the same 'offline' class; your CSS already supports connection-dot.offline
      if (data.connected) {
        viewConnDot.classList.remove("offline");
      } else {
        viewConnDot.classList.add("offline");
      }
    }

    if (viewConnLabel) {
      viewConnLabel.textContent = data.connected ? "Connected" : "Not connected";
    }

    if (viewPortText) {
      viewPortText.textContent = data.port || "—";
    }

    if (viewConnectBtn) {
      // Disable the button when already connected
      viewConnectBtn.disabled = !!data.connected;
    }

    if (viewPortSelect && data.port) {
      viewPortSelect.value = data.port;
    }


    // Dot: red/green
    if (connDot) {
      if (data.connected) {
        connDot.classList.remove("offline");
      } else {
        connDot.classList.add("offline");
      }
    }

    // Status label in the card
    if (connStatusText) {
      if (typeof data.connected === "boolean") {
        connStatusText.textContent = data.connected ? "Connected" : "Disconnected";
      } else {
        connStatusText.textContent = data.status || "Idle";
      }
    }

    // Port text + dropdown selection, if backend exposes it
    if (connPortText) {
      connPortText.textContent = data.port || "—";
    }
    if (portSelect && data.port) {
      portSelect.value = data.port;
    }

    // Enable / disable buttons based on connection state
    if (connectBtn) {
      connectBtn.disabled = !!data.connected;        // disable when connected
    }
    if (disconnectBtn) {
      disconnectBtn.disabled = !data.connected;      // disable when not connected
    }



    // DOM refs
    const azText     = document.getElementById("azText");
    const azNormText = document.getElementById("azNormText");
    const azMoonText = document.getElementById("azMoonText");
    const elText     = document.getElementById("elText");
    const elMoonText = document.getElementById("elMoonText");
    const trackerBtn = document.getElementById("trackerBtn");
    const forceChk   = document.getElementById("forceElChk");

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

      // trackerBtn.disabled = !canTrack;
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
  // We only support dark mode now
  return true;
}

function applyThemeLabels() {
  // If you still use data-label-light/dark on anything, keep this;
  // otherwise you can even remove this function entirely.
  const dark = true;
  document.querySelectorAll("[data-label-light]").forEach(el => {
    const txt = dark ? el.dataset.labelDark : el.dataset.labelLight;
    if (txt) {
      el.textContent = txt;
      el.setAttribute("aria-label", txt);
      el.title = txt;
    }
  });
}

function setTheme() {
  // Always dark mode
  document.body.classList.add("dark-mode");
  applyThemeLabels();
  if (typeof refreshStatus === "function") refreshStatus();
}

// ===== INIT & EVENT WIRING (single block) =====
document.addEventListener("DOMContentLoaded", () => {
  const camFsBtn = document.getElementById("camFsBtn");
  const camFsContainer = document.getElementById("camFsContainer");
  const camImg = document.getElementById("camStream");

  // Start MJPEG stream only after the page has fully loaded
  if (camImg) {
    window.addEventListener("load", () => {
      if (!camImg.src) {
        camImg.src = camImg.dataset.src || "/video.mjpg";
      }
    });
  }

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
  setTheme();
  localStorage.setItem("darkMode", "dark");

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

  // Public connect on data view (no login)
const viewConnectForm = document.getElementById("viewConnectForm");
if (viewConnectForm) {
  viewConnectForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const res = await fetch("/connect_public", { method: "POST", body: formData });
    const data = await res.json();
    // Status bar might not exist on view.html, but this is safe:
    updateStatusBar(data.status, data.success);
    // Refresh everywhere so labels / dials update
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
      const force = document.getElementById("forceElChk")?.checked ? "1" : "0";
      const formData = new FormData(e.target);
      const res = await fetch(`/set?force=${force}`, { method: "POST", body: formData });
      const data = await res.json();
      updateStatusBar(data.status, data.success);
      refreshStatus();
    });
  }

  // Tracker
  const trackerBtn = document.getElementById("trackerBtn");
  if (trackerBtn) {
    trackerBtn.addEventListener("click", async () => {
      const force = document.getElementById("forceElChk")?.checked ? "1" : "0";
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

// --- Camera health / overlay --------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  const img = document.getElementById("camStream");
  const overlay = document.getElementById("camOverlay");

  if (!img || !overlay) return;

  function showOverlay(on) {
    overlay.hidden = !on;
  }

  function startStream() {
    img.src = img.dataset.src + "?ts=" + Date.now();
  }

  img.addEventListener("error", () => {
    showOverlay(true);
    setTimeout(startStream, 1000);
  });

  img.addEventListener("load", () => showOverlay(false));

  // Start immediately
  startStream();

  img.addEventListener("error", () => {
    showOverlay(true);
    const now = Date.now();
    if (now - lastReload > 4000) {
      lastReload = now;
      startStream();
    }
  });

  img.addEventListener("load", () => {
    showOverlay(false);
  });

  async function pollCam() {
    try {
      const r = await fetch("/camera/health", { cache: "no-store" });
      const j = await r.json();
      const ok = r.ok && j.running && (j.has_frame || j.last_frame_age !== null);

      if (ok) {
        showOverlay(false);
        if (!img.src.includes("/video.mjpg")) startStream();
      } else {
        showOverlay(true);
        if (Date.now() - lastReload > 4000) {
          lastReload = Date.now();
          startStream();
        }
      }
    } catch {
      showOverlay(true);
    }
    setTimeout(pollCam, 2000);
  }

  pollCam();

  // --- Fullscreen toggle ---
  if (fsBtn) {
    async function toggleFs() {
      try {
        if (!document.fullscreenElement) {
          await (fsContainer.requestFullscreen
            ? fsContainer.requestFullscreen()
            : fsContainer.webkitRequestFullscreen?.());
        } else {
          await (document.exitFullscreen
            ? document.exitFullscreen()
            : document.webkitExitFullscreen?.());
        }
      } catch (e) {
        console.error("Fullscreen error:", e);
      }
    }
    fsBtn.addEventListener("click", toggleFs);
    if (img) img.addEventListener("dblclick", toggleFs);

    function updateFsLabel() {
      fsBtn.textContent = document.fullscreenElement ? "⛶ Exit Fullscreen" : "⛶ Fullscreen";
    }
    document.addEventListener("fullscreenchange", updateFsLabel);
    document.addEventListener("webkitfullscreenchange", updateFsLabel);
    updateFsLabel();
  }

});


// Pico relais switches
async function setCoax(sid, side) {
  // If UI is read-only, ignore clicks entirely
  if (!window.APP_CAN_EDIT) {
    return;
  }

  try {
    const r = await fetch(`/coax/${sid}/${side}`, { method: "POST" });
    const j = await r.json().catch(() => ({}));

    if (!r.ok || j.success === false) {
      const msg = j.error || j.status || `Coax S${sid} → ${side} failed`;
      updateStatusBar(msg, false);
      return;
    }

    updateStatusBar(j.status || `Coax S${sid} → ${side}`, true);
    // Re-poll to update button highlight
    pollCoax();
  } catch (e) {
    updateStatusBar(`Coax error: ${e}`, false);
  }
}

function updateCoaxButtonsFromState(switches, connected) {
  // Reset / disable everything first
  for (let sid = 1; sid <= 3; sid++) {
    ["1", "2"].forEach((side) => {
      const btn = document.getElementById(`coax-${sid}-${side}`);
      if (!btn) return;
      btn.disabled = !connected || !window.APP_CAN_EDIT;
      btn.classList.remove("coax-btn-active");
    });
  }

  if (!connected || !switches) return;

  // switches is e.g. { "S1": "1", "S2": "2", "S3": "1" }
  Object.entries(switches).forEach(([key, val]) => {
    if (!val) return;
    const sid = key.replace("S", "");
    const btn = document.getElementById(`coax-${sid}-${val}`);
    if (btn) btn.classList.add("coax-btn-active");
  });
}



// keep polling
setInterval(pollCoax, 2000);
pollCoax();

async function pollCoax() {
  try {
    const r = await fetch("/coax/status", { cache: "no-store" });
    const j = await r.json();

    const connected = !!j.connected;
    const switches = j.switches || {};

    // -------- Main status line inside card body --------
    const statusEl = document.getElementById("coax-status");
    if (statusEl) {
      if (connected) {
        statusEl.textContent = "Pico switch: online";
        statusEl.classList.remove("text-danger");
        statusEl.classList.add("text-success");
      } else {
        statusEl.textContent = "Pico switch: offline";
        statusEl.classList.remove("text-success");
        statusEl.classList.add("text-danger");
      }
    }

    // -------- Header indicator ("Coax Switches ● Online/Offline") --------
    const connDot  = document.getElementById("coax-conn-dot");
    const connText = document.getElementById("coax-conn-text");
    if (connDot) {
      if (connected) {
        connDot.classList.add("online");
      } else {
        connDot.classList.remove("online");
      }
    }
    if (connText) {
      connText.textContent = connected ? "Online" : "Offline";
    }

    // -------- Control-page buttons (if present) --------
    updateCoaxButtonsFromState(switches, connected);

    // -------- Read-only pills (view page) --------
    ["1", "2", "3"].forEach((sid) => {
      const current = switches["S" + sid];

      ["1", "2"].forEach((side) => {
        const pill = document.getElementById(`coax-view-${sid}-${side}`);
        if (!pill) return;

        // Clear previous state
        pill.classList.remove("coax-pill--active-1", "coax-pill--active-2");

        // Highlight only when connected and this is the active side
        if (connected && current === side) {
          pill.classList.add(
            side === "1" ? "coax-pill--active-1" : "coax-pill--active-2"
          );
        }
      });
    });

    // -------- RF schematic (control + view, if present) --------
    updateCoaxSchematic(switches, connected);

  } catch (e) {
    const statusEl = document.getElementById("coax-status");
    if (statusEl) {
      statusEl.textContent = "Pico switch: offline";
      statusEl.classList.remove("text-success");
      statusEl.classList.add("text-danger");
    }

    const connDot  = document.getElementById("coax-conn-dot");
    const connText = document.getElementById("coax-conn-text");
    if (connDot) connDot.classList.remove("online");
    if (connText) connText.textContent = "Offline";

    // Clear pills
    ["1", "2", "3"].forEach((sid) => {
      ["1", "2"].forEach((side) => {
        const pill = document.getElementById(`coax-view-${sid}-${side}`);
        if (pill) {
          pill.classList.remove("coax-pill--active-1", "coax-pill--active-2");
        }
      });
    });

    updateCoaxButtonsFromState({}, false);
    updateCoaxSchematic({}, false);
  }
}

// keep polling
setInterval(pollCoax, 2000);
pollCoax();


// ---------- RF schematic helpers (S1/S2/S3 from Pico) -------------------

// Your original orientation helper: p1/p2 + left/right
function setBladePosition(blade, orientation) {
  if (!blade) return;
  let x2, y2;
  if (orientation === "p1-left") {
    x2 = -50; y2 = -25;
  } else if (orientation === "p2-left") {
    x2 = -50; y2 = 25;
  } else if (orientation === "p1-right") {
    x2 = 50; y2 = -25;
  } else { // "p2-right"
    x2 = 50; y2 = 25;
  }
  blade.setAttribute("x1", "0");
  blade.setAttribute("y1", "0");
  blade.setAttribute("x2", String(x2));
  blade.setAttribute("y2", String(y2));
}

// Convenience: layout = "left" | "right", state = "p1" | "p2"
function setRfBlade(blade, layout, state) {
  if (!blade) return;
  const orientation =
    state === "p1"
      ? (layout === "left" ? "p1-left" : "p1-right")
      : (layout === "left" ? "p2-left" : "p2-right");
  setBladePosition(blade, orientation);
}

// Set a single wire's visual state: off / ok (green) / error (red)
function setWireState(id, state) {
  const wire = document.getElementById(id);
  if (!wire) return;
  wire.classList.remove("active", "error");

  if (state === "ok") {
    wire.classList.add("active");
  } else if (state === "error") {
    wire.classList.add("error");
  }
}

// Turn TX / RX RF waves on/off
function setRfWaves(txOn, rxOn) {
  const tx = document.querySelectorAll("#rf-schematic .ant-wave-tx");
  const rx = document.querySelectorAll("#rf-schematic .ant-wave-rx");

  tx.forEach((w) => w.classList.toggle("active", !!txOn));
  rx.forEach((w) => w.classList.toggle("active", !!rxOn));
}

// Highlight the RF path and decide if it's valid TX / RX
// s1State/s2State/s3State are "p1"/"p2"; connected is boolean
function highlightRfPath(s1State, s2State, s3State, connected) {
  const wireIds = {
    tx_to_pa:       "w_tx_to_pa",
    pa_to_s1p1:     "w_pa_to_s1p1",
    rx_to_s1p2:     "w_rx_to_s1p2",
    s1com_to_s2com: "w_s1com_to_s2com",
    s2p1_to_lna:    "w_s2p1_to_lna",
    lna_to_s3p1:    "w_lna_to_s3p1",
    s2p2_to_s3p2:   "w_s2p2_to_s3p2",
    s3com_to_out:   "w_s3com_to_out",
  };

  function clearAll() {
    Object.values(wireIds).forEach((id) => setWireState(id, "off"));
    setRfWaves(false, false);
  }

  if (!connected || !s1State || !s2State || !s3State) {
    clearAll();
    return;
  }

  const sourceIsTx = s1State === "p1"; // S1=1 → TX
  const sourceIsRx = s1State === "p2"; // S1=2 → RX

  const path = {
    tx_to_pa:       false,
    pa_to_s1p1:     false,
    rx_to_s1p2:     false,
    s1com_to_s2com: false,
    s2p1_to_lna:    false,
    lna_to_s3p1:    false,
    s2p2_to_s3p2:   false,
    s3com_to_out:   false,
  };

  setRfWaves(false, false);

  // --- S1: choose source (TX or RX) -------------------------------------
  let sourceFeedsS1Com = false;

  if (sourceIsTx) {
    path.tx_to_pa   = true;
    path.pa_to_s1p1 = true;
    sourceFeedsS1Com = true;
  } else if (sourceIsRx) {
    path.rx_to_s1p2 = true;
    sourceFeedsS1Com = true;
  }

  if (!sourceFeedsS1Com) {
    clearAll();
    return;
  }

  // --- S1 COM to S2 ------------------------------------------------------
  path.s1com_to_s2com = true;

  // --- S2: upper path (LNA) or lower bypass ------------------------------
  let s2FeedsS3P1 = false;
  let s2FeedsS3P2 = false;

  if (s2State === "p1") {
    path.s2p1_to_lna = true;
    path.lna_to_s3p1 = true;
    s2FeedsS3P1 = true;
  } else if (s2State === "p2") {
    path.s2p2_to_s3p2 = true;
    s2FeedsS3P2 = true;
  }

  // --- S3: decide if we reach the antenna -------------------------------
  let s3HasValidPathToOut = false;

  if (s3State === "p1" && s2FeedsS3P1) {
    path.s3com_to_out = true;
    s3HasValidPathToOut = true;
  }
  if (s3State === "p2" && s2FeedsS3P2) {
    path.s3com_to_out = true;
    s3HasValidPathToOut = true;
  }

  // --- Valid combos (from your original logic) --------------------------
  // Valid TX: S1=1 (p1), S2=2 (p2), S3=2 (p2)
  const txConfigCorrect =
    sourceIsTx &&
    s1State === "p1" &&
    s2State === "p2" &&
    s3State === "p2";

  // Valid RX: S1=2 (p2), S2=1 (p1), S3=1 (p1)
  const rxConfigCorrect =
    sourceIsRx &&
    s1State === "p2" &&
    s2State === "p1" &&
    s3State === "p1";

  const pathToAntennaIsCorrect =
    s3HasValidPathToOut && (txConfigCorrect || rxConfigCorrect);

  // --- Apply wire states -------------------------------------------------
  Object.entries(wireIds).forEach(([key, id]) => {
    if (!path[key]) {
      setWireState(id, "off");
      return;
    }

    if (s3HasValidPathToOut && !pathToAntennaIsCorrect) {
      // We are feeding the antenna, but NOT in one of the allowed configs
      setWireState(id, "error");
    } else {
      // Normal active (green)
      setWireState(id, "ok");
    }
  });

  // --- RF waves at antenna ----------------------------------------------
  if (pathToAntennaIsCorrect) {
    setRfWaves(sourceIsTx, sourceIsRx);
  } else {
    setRfWaves(false, false);
  }
}

// Use Pico switch states to drive blades + path
function updateCoaxSchematic(switches, connected) {
  const svg = document.getElementById("rf-schematic");
  if (!svg) return;

  // switches is e.g. { S1: "1", S2: "2", S3: "1" }
  const getVal = (sid) => {
    if (!switches) return null;
    const v = switches["S" + sid];
    return v !== undefined && v !== null ? v : null;
  };

  const s1Val = getVal(1);
  const s2Val = getVal(2);
  const s3Val = getVal(3);

  // Map Pico "1"/"2" to "p1"/"p2"
  const mapToState = (v) => (v === "2" || v === 2 ? "p2" : "p1");

  const s1State = s1Val ? mapToState(s1Val) : "p1";
  const s2State = s2Val ? mapToState(s2Val) : "p1";
  const s3State = s3Val ? mapToState(s3Val) : "p1";

  const s1Blade = document.getElementById("s1_blade");
  const s2Blade = document.getElementById("s2_blade");
  const s3Blade = document.getElementById("s3_blade");

  if (connected) {
    // Match your SVG geometry:
    // S1: ports LEFT, S2: ports RIGHT, S3: ports LEFT
    setRfBlade(s1Blade, "left",  s1State);
    setRfBlade(s2Blade, "right", s2State);
    setRfBlade(s3Blade, "left",  s3State);
  } else {
    // Park everything to p1 (TX path) when offline
    setRfBlade(s1Blade, "left",  "p1");
    setRfBlade(s2Blade, "right", "p1");
    setRfBlade(s3Blade, "left",  "p1");
  }

  // Highlight / animate RF path
  highlightRfPath(
    connected ? s1State : null,
    connected ? s2State : null,
    connected ? s3State : null,
    connected
  );
}
