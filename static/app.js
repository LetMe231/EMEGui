// ==================== Drawing Helpers ====================

// Fit canvas backing store to its CSS size (crisp, no squish), DPR-safe.
// Draw functions will use CSS pixels after this call.
const AZEL_SIZE_PX = 350;

function fitCanvasFixed(canvas, sizePx) {
  // Force CSS size so layout does NOT depend on canvas.width/height
  canvas.style.width = sizePx + "px";
  canvas.style.height = sizePx + "px";

  const dpr = window.devicePixelRatio || 1;
  const w = Math.max(1, Math.round(sizePx * dpr));
  const h = Math.max(1, Math.round(sizePx * dpr));

  if (canvas.width !== w || canvas.height !== h) {
    canvas.width = w;
    canvas.height = h;
  }

  const ctx = canvas.getContext("2d");
  // Draw in CSS pixel coordinates
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, wCss: sizePx, hCss: sizePx };
}

function drawTicks(ctx, cx, cy, r, startAngle, endAngle, step, labelStep, color, outside = false, elevationMode = false) {
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.font = "11px Arial";
  ctx.textAlign = "center";

  for (let angle = startAngle; angle <= endAngle; angle += step) {
    const rad = elevationMode
      ? (-angle) * Math.PI / 180
      : (angle - 90) * Math.PI / 180;

    const x1 = cx + r * Math.cos(rad);
    const y1 = cy + r * Math.sin(rad);
    const x2 = cx + (r - 10) * Math.cos(rad);
    const y2 = cy + (r - 10) * Math.sin(rad);

    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.lineWidth = 1;
    ctx.stroke();

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

  const { ctx, wCss: w, hCss: h } = fitCanvasFixed(c, AZEL_SIZE_PX);
  ctx.clearRect(0, 0, w, h);

  const cx = w / 2, cy = h / 2;
  const r = Math.min(w, h) * 0.38;

  const isDark = isDarkMode();
  const color = isDark ? "white" : "black";

  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, 2 * Math.PI);
  ctx.lineWidth = 2;
  ctx.strokeStyle = color;
  ctx.stroke();

  drawTicks(ctx, cx, cy, r, 0, 360, 30, 90, color, false, false);

  ctx.font = "bold 14px Arial";
  ctx.fillStyle = color;
  ctx.textAlign = "center";
  ctx.fillText("Azimuth", cx, cy - r - 12);

  if (connected) {
    let rad = (az - 90) * Math.PI / 180;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + r * Math.cos(rad), cy + r * Math.sin(rad));
    ctx.strokeStyle = isDark ? "deepskyblue" : "blue";
    ctx.lineWidth = 3;
    ctx.stroke();

    let radMoon = (azMoon - 90) * Math.PI / 180;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + r * Math.cos(radMoon), cy + r * Math.sin(radMoon));
    ctx.strokeStyle = isDark ? "yellow" : "orange";
    ctx.setLineDash([5, 5]);
    ctx.stroke();
    ctx.setLineDash([]);

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
    ctx.fillText("No Data!", cx, cy + r + 24);
  }
}

function drawElevation(el, elMoon, connected) {
  const c = document.getElementById("elCanvas");
  if (!c) return;

  const { ctx, wCss: w, hCss: h } = fitCanvasFixed(c, AZEL_SIZE_PX);
  ctx.clearRect(0, 0, w, h);

  const isDark = isDarkMode();
  const color = isDark ? "white" : "black";

  const pad = Math.min(w, h) * 0.12;
  const Rq = Math.min(w, h) - pad * 2;
  const cx = pad;
  const cy = h - pad;

  ctx.beginPath();
  ctx.arc(cx, cy, Rq, -Math.PI / 2, 0);
  ctx.lineWidth = 2;
  ctx.strokeStyle = color;
  ctx.stroke();

  drawTicks(ctx, cx, cy, Rq, 0, 90, 15, 30, color, true, true);

  ctx.font = "bold 14px Arial";
  ctx.fillStyle = color;
  ctx.textAlign = "center";
  ctx.fillText("Elevation", w / 2, pad);

  if (connected) {
    let rad = el * Math.PI / 180;
    let ex = cx + Rq * Math.cos(rad);
    let ey = cy - Rq * Math.sin(rad);
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(ex, ey);
    ctx.strokeStyle = isDark ? "deepskyblue" : "blue";
    ctx.lineWidth = 3;
    ctx.stroke();

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

    let radPark = 60 * Math.PI / 180;
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
    ctx.strokeStyle = "red";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(pad, pad);
    ctx.lineTo(w - pad, h - pad);
    ctx.moveTo(w - pad, pad);
    ctx.lineTo(pad, h - pad);
    ctx.stroke();

    ctx.font = "bold 18px Arial";
    ctx.fillStyle = "red";
    ctx.textAlign = "center";
    ctx.fillText("No Data!", w / 2, h - pad / 2);
  }
}

// ==================== Moon Orbit (Umlaufbahn) ====================
function drawMoonOrbit(azMoonDeg, elMoonDeg, antAzDeg, antElDeg) {
  const c = document.getElementById("orbitCanvas");
  if (!c) return;

  const ctx = c.getContext("2d");
  const w = c.width;
  const h = c.height;
  const cx = w / 2;
  const cy = h / 2;
  const R = Math.min(w, h) * 0.38;

  ctx.clearRect(0, 0, w, h);

  const grd = ctx.createRadialGradient(cx, cy, 0, cx, cy, R * 1.4);
  grd.addColorStop(0, "#020617");
  grd.addColorStop(1, "#020617");
  ctx.fillStyle = grd;
  ctx.fillRect(0, 0, w, h);

  ctx.beginPath();
  ctx.arc(cx, cy, R, 0, 2 * Math.PI);
  ctx.strokeStyle = "#4b5563";
  ctx.lineWidth = 2;
  ctx.setLineDash([4, 6]);
  ctx.stroke();
  ctx.setLineDash([]);

  ctx.beginPath();
  ctx.arc(cx, cy, R * 0.2, 0, 2 * Math.PI);
  const earthGrd = ctx.createRadialGradient(cx - 4, cy - 4, 0, cx, cy, R * 0.2);
  earthGrd.addColorStop(0, "#38bdf8");
  earthGrd.addColorStop(1, "#0f172a");
  ctx.fillStyle = earthGrd;
  ctx.fill();
  ctx.strokeStyle = "#0ea5e9";
  ctx.lineWidth = 1.5;
  ctx.stroke();

  ctx.fillStyle = "#6b7280";
  ctx.font = "11px system-ui";
  ctx.textAlign = "center";
  ctx.fillText("N", cx, cy - R - 8);
  ctx.fillText("S", cx, cy + R + 12);
  ctx.fillText("W", cx - R - 10, cy + 4);
  ctx.fillText("E", cx + R + 10, cy + 4);

  const toRad = (azDeg) => (azDeg - 90) * Math.PI / 180;

  const azMoon = isFinite(azMoonDeg) ? azMoonDeg : 0;
  const moonA = toRad(azMoon);
  const mx = cx + R * Math.cos(moonA);
  const my = cy + R * Math.sin(moonA);

  const antAz = isFinite(antAzDeg) ? antAzDeg : azMoon;
  const antA = toRad(antAz);
  const ax = cx + (R * 0.75) * Math.cos(antA);
  const ay = cy + (R * 0.75) * Math.sin(antA);

  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.lineTo(ax, ay);
  ctx.strokeStyle = "#22c55e";
  ctx.lineWidth = 2;
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.lineTo(mx, my);
  ctx.strokeStyle = "#facc15";
  ctx.lineWidth = 2;
  ctx.setLineDash([6, 4]);
  ctx.stroke();
  ctx.setLineDash([]);

  ctx.beginPath();
  ctx.arc(ax, ay, 6, 0, 2 * Math.PI);
  ctx.fillStyle = "#22c55e";
  ctx.fill();
  ctx.strokeStyle = "#111827";
  ctx.lineWidth = 1.5;
  ctx.stroke();

  ctx.beginPath();
  ctx.arc(mx, my, 8, 0, 2 * Math.PI);
  const moonGrd = ctx.createRadialGradient(mx - 2, my - 3, 0, mx, my, 8);
  moonGrd.addColorStop(0, "#facc15");
  moonGrd.addColorStop(1, "#854d0e");
  ctx.fillStyle = moonGrd;
  ctx.fill();
  ctx.strokeStyle = "#fbbf24";
  ctx.lineWidth = 1.5;
  ctx.stroke();

  ctx.font = "10px system-ui";
  ctx.fillStyle = "#e5e7eb";
  ctx.textAlign = "left";
  ctx.fillText("Moon", mx + 10, my - 4);

  if (isFinite(elMoonDeg)) {
    const elRatio = Math.max(0, Math.min(1, elMoonDeg / 90));
    ctx.beginPath();
    ctx.arc(mx, my, 12, 0, 2 * Math.PI);
    ctx.strokeStyle = `rgba(250, 204, 21, ${0.15 + 0.35 * elRatio})`;
    ctx.lineWidth = 3;
    ctx.stroke();
  }
}

// ==================== Status & AJAX ====================
function computeCanEdit() {
  const ds = document.body?.dataset || {};
  // supports: data-can-edit="1"  OR data-can_edit="1"
  const v = ds.canEdit ?? ds.can_edit ?? ds.canedit ?? "0";
  return v === "1" || v === "true";
}

window.APP_CAN_EDIT = computeCanEdit();
window.LAST_STATUS = null;

function updateStatusBar(text, success, levelOverride) {
  const statusBar = document.getElementById("status-bar");
  if (!statusBar) return;

  statusBar.innerText = text || "";

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
    window.LAST_STATUS = data;

    updateStatusBar(data.status, data.connected);

    // ----- Control connection card (control.html) -----
    const connDot        = document.getElementById("connection-dot");
    const connStatusText = document.getElementById("connection-status-text");
    const connPortText   = document.getElementById("connection-port-text");
    const connectBtn     = document.querySelector("#connectForm button[type='submit']");
    const disconnectBtn  = document.getElementById("disconnectBtn");
    const portSelect     = document.querySelector("#connectForm select[name='port']");

    if (connDot) connDot.classList.toggle("offline", !data.connected);
    if (connStatusText) connStatusText.textContent = data.connected ? "Connected" : "Disconnected";
    if (connPortText) connPortText.textContent = data.port || "—";
    if (portSelect && data.port) portSelect.value = data.port;
    if (connectBtn) connectBtn.disabled = !!data.connected;
    if (disconnectBtn) disconnectBtn.disabled = !data.connected;

    // ----- View-only connection card (index.html) -----
    const viewConnDot     = document.getElementById("conn-dot");
    const viewConnLabel   = document.getElementById("conn-label");
    const viewPortText    = document.getElementById("view-port-text");
    const viewPortSelect  = document.querySelector("#viewConnectForm select[name='port']");

    if (viewConnDot) viewConnDot.classList.toggle("offline", !data.connected);
    if (viewConnLabel) viewConnLabel.textContent = data.connected ? "Connected" : "Not connected";
    if (viewPortText) viewPortText.textContent = data.port || "—";
    if (viewPortSelect && data.port) viewPortSelect.value = data.port;

    // Single toggle label (view MD)
    const viewMdToggleBtn = document.getElementById("viewMdToggleBtn");
    if (viewMdToggleBtn) {
      viewMdToggleBtn.textContent = data.connected ? "Disconnect MD-01" : "Connect MD-01";
      if (viewPortSelect) viewPortSelect.disabled = !!data.connected;
    }

    // ----- Pico coax connection UI (control.html) -----
    const coaxPortText       = document.getElementById("coax-port-text");
    const coaxConnectBtn     = document.getElementById("coaxConnectBtn");
    const coaxDisconnectBtn  = document.getElementById("coaxDisconnectBtn");

    if (coaxPortText) coaxPortText.textContent = data.switch_port || "—";

    // FIX: Don't disable connect/disconnect here based on switch_connected.
    // Let the handler decide what to do. Otherwise your "toggle" UX breaks.
    if (coaxConnectBtn) {
      // allow clicking; actual POST is still blocked by APP_CAN_EDIT in handler
      coaxConnectBtn.disabled = !window.APP_CAN_EDIT;
    }
    if (coaxDisconnectBtn) {
      coaxDisconnectBtn.disabled = !window.APP_CAN_EDIT;
    }

    // Single toggle label (view Pico)
    const viewPicoToggleBtn = document.getElementById("viewPicoToggleBtn");
    const coaxViewPortSelect = document.querySelector("#coaxViewConnectForm select[name='port']");
    if (viewPicoToggleBtn) {
      viewPicoToggleBtn.textContent = data.switch_connected ? "Disconnect Pico" : "Connect Pico";
      if (coaxViewPortSelect) coaxViewPortSelect.disabled = !!data.switch_connected;
    }

    // ----- Text under dials -----
    const azText     = document.getElementById("azText");
    const azNormText = document.getElementById("azNormText");
    const azMoonText = document.getElementById("azMoonText");
    const elText     = document.getElementById("elText");
    const elMoonText = document.getElementById("elMoonText");
    const moonAbove15El = document.getElementById("moonAbove15Text");
    const moonBelow15El = document.getElementById("moonBelow15Text");
    const trackerBtn = document.getElementById("trackerBtn");
    const forceChk   = document.getElementById("forceElChk");
    const measBtn    = document.getElementById("measBtn");
    const coaxModeBtn = document.getElementById("coaxModeBtn");

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

    const formatMoonTime = (iso) => {
      if (!iso) return "--:--";
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return "--:--";

      const now = new Date();
      const sameDay = d.toDateString() === now.toDateString();

      const timeStr = d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
      if (sameDay) return timeStr;

      const dateStr = d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
      return `${dateStr} ${timeStr}`;
    };

    if (moonAbove15El) moonAbove15El.textContent = "Next ≥15°: " + formatMoonTime(data.moon_next_above_15);
    if (moonBelow15El) moonBelow15El.textContent = "Next <15°: " + formatMoonTime(data.moon_next_below_15);

    if (trackerBtn) {
      const moonLow = (+data.el_moon) < 15;
      const forced  = forceChk && forceChk.checked;
      const canTrack = !!data.connected && (!moonLow || forced);

      trackerBtn.title = !canTrack ? "Moon below 15° — tracking paused" : "";

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

    if (coaxModeBtn) {
      const canToggle = !!data.connected && window.APP_CAN_EDIT;
      coaxModeBtn.disabled = !canToggle;

      if (!data.connected) coaxModeBtn.title = "Controller not connected";
      else if (!window.APP_CAN_EDIT) coaxModeBtn.title = "Read-only mode";
      else coaxModeBtn.title = "Toggle all relays between TX and RX presets";
    }

    if (measBtn) {
      const trackingOn = !!data.tracking;
      const hasLockInfo = typeof data.locked === "boolean";
      const moonLocked  = hasLockInfo ? !!data.locked : true;

      const canMeasure = !!data.connected && trackingOn && moonLocked && window.APP_CAN_EDIT;
      measBtn.disabled = !canMeasure;

      if (!trackingOn) measBtn.title = "Requires active tracking to the Moon";
      else if (!moonLocked) measBtn.title = "Requires Moon lock before measuring distance";
      else if (!data.connected) measBtn.title = "Controller not connected";
      else if (!window.APP_CAN_EDIT) measBtn.title = "Read-only mode";
      else measBtn.title = "Start distance measurement to the Moon";
    }

    // Draw dials using new responsive functions
    drawAzimuth(+data.az, +data.az_moon, !!data.connected);
    drawElevation(+data.el, +data.el_moon, !!data.connected);

    const orbitCanvas = document.getElementById("orbitCanvas");
    if (orbitCanvas) {
      const azMoon = +data.az_moon;
      const elMoon = +data.el_moon;
      const antAz  = +data.az;
      const antEl  = +data.el;

      drawMoonOrbit(azMoon, elMoon, antAz, antEl);

      const azLbl  = document.getElementById("orbit-az");
      const elLbl  = document.getElementById("orbit-el");
      const antAzLbl = document.getElementById("orbit-ant-az");
      const antElLbl = document.getElementById("orbit-ant-el");

      if (azLbl)    azLbl.textContent    = `${isFinite(azMoon) ? azMoon.toFixed(1) : "--.-"}°`;
      if (elLbl)    elLbl.textContent    = `${isFinite(elMoon) ? elMoon.toFixed(1) : "--.-"}°`;
      if (antAzLbl) antAzLbl.textContent = `${isFinite(antAz)  ? antAz.toFixed(1)  : "--.-"}°`;
      if (antElLbl) antElLbl.textContent = `${isFinite(antEl)  ? antEl.toFixed(1)  : "--.-"}°`;
    }

  } catch (e) {
    updateStatusBar(`Error: ${e}`, false);
  }
}

// ===== DARK MODE SYSTEM =====
function isDarkMode() { return true; }

function applyThemeLabels() {
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
  document.body.classList.add("dark-mode");
  applyThemeLabels();
  if (typeof refreshStatus === "function") refreshStatus();
}

// ==================== DOMContentLoaded MAIN ====================
document.addEventListener("DOMContentLoaded", () => {
  // update can_edit flag once DOM exists
  window.APP_CAN_EDIT = computeCanEdit();


  setTheme();
  localStorage.setItem("darkMode", "dark");

  // Camera fullscreen
  const camFsBtn = document.getElementById("camFsBtn");
  const camFsContainer = document.getElementById("camFsContainer");
  const camImg = document.getElementById("camStream");

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
          : camFsContainer.webkitRequestFullscreen?.());
      } else {
        await (document.exitFullscreen
          ? document.exitFullscreen()
          : document.webkitExitFullscreen?.());
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
    if (camImg) camImg.addEventListener("dblclick", toggleCamFullscreen);

    document.addEventListener("fullscreenchange", setFsButtonLabel);
    document.addEventListener("webkitfullscreenchange", setFsButtonLabel);
    setFsButtonLabel();
  }

  // MD-01 connect (control page)
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

  // MD-01 disconnect (control page)
  const disconnectBtn = document.getElementById("disconnectBtn");
  if (disconnectBtn) {
    disconnectBtn.addEventListener("click", async () => {
      const res = await fetch("/disconnect", { method: "POST" });
      const data = await res.json();
      updateStatusBar(data.status, data.success);
      refreshStatus();
    });
  }

  // MD toggle (view page): connect_public <-> disconnect
  const viewConnectForm = document.getElementById("viewConnectForm");
  if (viewConnectForm) {
    viewConnectForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const st = window.LAST_STATUS || {};
      const currentlyConnected = !!st.connected;

      try {
        if (currentlyConnected) {
          const res = await fetch("/disconnect", { method: "POST" });
          const data = await res.json().catch(() => ({}));
          updateStatusBar(data.status || "Disconnected", data.success !== false);
        } else {
          const formData = new FormData(e.target);
          const res = await fetch("/connect_public", { method: "POST", body: formData });
          const data = await res.json().catch(() => ({}));
          updateStatusBar(data.status || "Connected", data.success !== false);
        }
      } catch (err) {
        updateStatusBar("MD toggle error (view): " + err, false);
      }

      refreshStatus();
    });
  }

  // Pico coax connect/disconnect (control page) - gated by APP_CAN_EDIT
  const coaxConnectForm = document.getElementById("coaxConnectForm");
  const coaxDisconnectBtn = document.getElementById("coaxDisconnectBtn");

  if (coaxConnectForm) {
    coaxConnectForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const formData = new FormData(e.target);
      try {
        const res = await fetch("/coax/connect", { method: "POST", body: formData });
        const data = await res.json().catch(() => ({}));
        updateStatusBar(
          data.status || (data.success ? "Pico connected" : "Pico connect failed"),
          data.success
        );
      } catch (err) {
        updateStatusBar("Pico connect error: " + err, false);
      }
      refreshStatus();
      pollCoax();
    });
  }

  if (coaxDisconnectBtn) {
    coaxDisconnectBtn.addEventListener("click", async () => {
      if (!window.APP_CAN_EDIT) return;
      try {
        const res = await fetch("/coax/disconnect", { method: "POST" });
        const data = await res.json().catch(() => ({}));
        updateStatusBar(
          data.status || (data.success ? "Pico disconnected" : "Pico disconnect failed"),
          data.success
        );
      } catch (err) {
        updateStatusBar("Pico disconnect error: " + err, false);
      }
      refreshStatus();
      pollCoax();
    });
  }

  // Pico toggle (view page): connect_public <-> disconnect
  const coaxViewConnectForm = document.getElementById("coaxViewConnectForm");
  if (coaxViewConnectForm) {
    coaxViewConnectForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const st = window.LAST_STATUS || {};
      const picoConnected = !!st.switch_connected;

      try {
        if (picoConnected) {
          const res = await fetch("/coax/disconnect", { method: "POST" });
          const data = await res.json().catch(() => ({}));

          if (!res.ok || data.success === false) {
            updateStatusBar(data.status || data.error || "Pico disconnect failed", false);
          } else {
            updateStatusBar(data.status || "Pico disconnected", true);
          }
        } else {
          const formData = new FormData(e.target);
          const res = await fetch("/coax/connect_public", { method: "POST", body: formData });
          const data = await res.json().catch(() => ({}));

          if (!res.ok || data.success === false) {
            updateStatusBar(data.status || data.error || "Pico connect failed", false);
          } else {
            updateStatusBar(data.status || "Pico connected (view)", true);
          }
        }
      } catch (err) {
        updateStatusBar("Pico toggle error (view): " + err, false);
      }

      if (typeof pollCoax === "function") pollCoax();
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

  // Start measurement
  const measBtn = document.getElementById("measBtn");
  if (measBtn) {
    measBtn.addEventListener("click", async () => {
      try {
        const res = await fetch("/measurement/start", { method: "POST" });
        const data = await res.json().catch(() => ({}));

        if (!res.ok || data.success === false) {
          const msg = data.status || data.error || "Measurement start failed";
          updateStatusBar(msg, false);
          return;
        }

        updateStatusBar(data.status || "Measurement sequence started (placeholder)", true);
      } catch (e) {
        updateStatusBar(`Measurement error: ${e}`, false);
      }
    });
  }

  // Measurement console stream (ONLY if elements exist)
  const pre = document.getElementById("measConsole");
  if (pre) {
    const es = new EventSource("/measurement/stream");
    es.onmessage = (ev) => {
      if (!ev.data) return;
      pre.textContent += ev.data + "\n";
      pre.scrollTop = pre.scrollHeight;
    };
  }

  const sendBtn = document.getElementById("measCmdSend");
  const cmdInp = document.getElementById("measCmd");
  if (sendBtn && cmdInp) {
    sendBtn.addEventListener("click", async () => {
      const text = (cmdInp.value || "").trim();
      if (!text) return;
      cmdInp.value = "";
      const fd = new FormData();
      fd.append("text", text);
      await fetch("/measurement/console", { method: "POST", body: fd });
    });
  }

  // TX/RX path toggle
  const coaxModeBtn = document.getElementById("coaxModeBtn");
  if (coaxModeBtn) {
    coaxModeBtn.addEventListener("click", async () => {
      try {
        const res = await fetch("/coax/toggle_mode", { method: "POST" });
        const data = await res.json().catch(() => ({}));

        if (!res.ok || data.success === false) {
          const msg = data.status || data.error || "TX/RX toggle failed";
          updateStatusBar(msg, false);
          return;
        }

        if (data.mode === "tx") coaxModeBtn.textContent = "Switch to RX";
        else if (data.mode === "rx") coaxModeBtn.textContent = "Switch to TX";
        else coaxModeBtn.textContent = "Toggle TX / RX";

        updateStatusBar(data.status || "RF path toggled (TX/RX)", true);
        pollCoax();
      } catch (e) {
        updateStatusBar(`TX/RX toggle error: ${e}`, false);
      }
    });
  }

  // Redraw on resize so the new canvas sizing stays perfect
  window.addEventListener("resize", () => {
    if (window.LAST_STATUS) {
      const d = window.LAST_STATUS;
      drawAzimuth(+d.az, +d.az_moon, !!d.connected);
      drawElevation(+d.el, +d.el_moon, !!d.connected);
    }
  });

  // First draw + periodic refresh
  refreshStatus();
  setInterval(refreshStatus, 2000);
});

// --- Camera health / overlay --------------------------------------------------
(() => {
  const img = document.getElementById("camStream");
  const overlay = document.getElementById("camOverlay");
  if (!img || !overlay) return;

  let lastReload = 0;

  function showOverlay(on) {
    overlay.hidden = !on;
  }

  function startStream() {
    img.src = (img.dataset.src || "/video.mjpg") + "?ts=" + Date.now();
  }

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
    } finally {
      setTimeout(pollCam, 2000);
    }
  }

  startStream();
  pollCam();
})();

// ==================== Coax control & schematic ====================
async function setCoax(sid, side) {
  if (!window.APP_CAN_EDIT) return;

  try {
    const r = await fetch(`/coax/${sid}/${side}`, { method: "POST" });
    const j = await r.json().catch(() => ({}));

    if (!r.ok || j.success === false) {
      const msg = j.error || j.status || `Coax S${sid} → ${side} failed`;
      updateStatusBar(msg, false);
      return;
    }

    updateStatusBar(j.status || `Coax S${sid} → ${side}`, true);
    pollCoax();
  } catch (e) {
    updateStatusBar(`Coax error: ${e}`, false);
  }
}

function updateCoaxButtonsFromState(switches, connected) {
  for (let sid = 1; sid <= 3; sid++) {
    ["1", "2"].forEach((side) => {
      const btn = document.getElementById(`coax-${sid}-${side}`);
      if (!btn) return;
      btn.disabled = !connected || !window.APP_CAN_EDIT;
      btn.classList.remove("coax-btn-active");
    });
  }

  if (!connected || !switches) return;

  Object.entries(switches).forEach(([key, val]) => {
    if (!val) return;
    const sid = key.replace("S", "");
    const btn = document.getElementById(`coax-${sid}-${val}`);
    if (btn) btn.classList.add("coax-btn-active");
  });
}

// --- RF schematic helpers (S1/S2/S3 from Pico) ---
function setBladePosition(blade, orientation) {
  if (!blade) return;
  let x2, y2;
  if (orientation === "p1-left") {
    x2 = -50; y2 = -25;
  } else if (orientation === "p2-left") {
    x2 = -50; y2 = 25;
  } else if (orientation === "p1-right") {
    x2 = 50; y2 = -25;
  } else {
    x2 = 50; y2 = 25;
  }
  blade.setAttribute("x1", "0");
  blade.setAttribute("y1", "0");
  blade.setAttribute("x2", String(x2));
  blade.setAttribute("y2", String(y2));
}

function setRfBlade(blade, layout, state) {
  if (!blade) return;
  const orientation =
    state === "p1"
      ? (layout === "left" ? "p1-left" : "p1-right")
      : (layout === "left" ? "p2-left" : "p2-right");
  setBladePosition(blade, orientation);
}

function setWireState(id, state) {
  const wire = document.getElementById(id);
  if (!wire) return;
  wire.classList.remove("active", "error");
  if (state === "ok") wire.classList.add("active");
  if (state === "error") wire.classList.add("error");
}

function setRfWaves(txOn, rxOn) {
  const tx = document.querySelectorAll("#rf-schematic .ant-wave-tx");
  const rx = document.querySelectorAll("#rf-schematic .ant-wave-rx");
  tx.forEach((w) => w.classList.toggle("active", !!txOn));
  rx.forEach((w) => w.classList.toggle("active", !!rxOn));
}

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

  const sourceIsTx = s1State === "p1";
  const sourceIsRx = s1State === "p2";

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

  path.s1com_to_s2com = true;

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

  let s3HasValidPathToOut = false;
  if (s3State === "p1" && s2FeedsS3P1) {
    path.s3com_to_out = true;
    s3HasValidPathToOut = true;
  }
  if (s3State === "p2" && s2FeedsS3P2) {
    path.s3com_to_out = true;
    s3HasValidPathToOut = true;
  }

  const txConfigCorrect =
    sourceIsTx &&
    s1State === "p1" &&
    s2State === "p2" &&
    s3State === "p2";

  const rxConfigCorrect =
    sourceIsRx &&
    s1State === "p2" &&
    s2State === "p1" &&
    s3State === "p1";

  const pathToAntennaIsCorrect =
    s3HasValidPathToOut && (txConfigCorrect || rxConfigCorrect);

  Object.entries(wireIds).forEach(([key, id]) => {
    if (!path[key]) {
      setWireState(id, "off");
      return;
    }
    if (s3HasValidPathToOut && !pathToAntennaIsCorrect) {
      setWireState(id, "error");
    } else {
      setWireState(id, "ok");
    }
  });

  if (pathToAntennaIsCorrect) {
    setRfWaves(sourceIsTx, sourceIsRx);
  } else {
    setRfWaves(false, false);
  }
}

function updateCoaxSchematic(switches, connected) {
  const svg = document.getElementById("rf-schematic");
  if (!svg) return;

  const getVal = (sid) => {
    if (!switches) return null;
    const v = switches["S" + sid];
    return v !== undefined && v !== null ? v : null;
  };

  const s1Val = getVal(1);
  const s2Val = getVal(2);
  const s3Val = getVal(3);

  const mapToState = (v) => (v === "2" || v === 2 ? "p2" : "p1");

  const s1State = s1Val ? mapToState(s1Val) : "p1";
  const s2State = s2Val ? mapToState(s2Val) : "p1";
  const s3State = s3Val ? mapToState(s3Val) : "p1";

  const s1Blade = document.getElementById("s1_blade");
  const s2Blade = document.getElementById("s2_blade");
  const s3Blade = document.getElementById("s3_blade");

  if (connected) {
    setRfBlade(s1Blade, "left",  s1State);
    setRfBlade(s2Blade, "right", s2State);
    setRfBlade(s3Blade, "left",  s3State);
  } else {
    setRfBlade(s1Blade, "left",  "p1");
    setRfBlade(s2Blade, "right", "p1");
    setRfBlade(s3Blade, "left",  "p1");
  }

  highlightRfPath(
    connected ? s1State : null,
    connected ? s2State : null,
    connected ? s3State : null,
    connected
  );
}

async function pollCoax() {
  try {
    const r = await fetch("/coax/status", { cache: "no-store" });
    const j = await r.json();

    const connected = !!j.connected;
    const switches = j.switches || {};

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

    const connDot  = document.getElementById("coax-conn-dot");
    const connText = document.getElementById("coax-conn-text");
    if (connDot) connDot.classList.toggle("online", connected);
    if (connText) connText.textContent = connected ? "Online" : "Offline";

    updateCoaxButtonsFromState(switches, connected);

    ["1", "2", "3"].forEach((sid) => {
      const current = switches["S" + sid];
      ["1", "2"].forEach((side) => {
        const pill = document.getElementById(`coax-view-${sid}-${side}`);
        if (!pill) return;
        pill.classList.remove("coax-pill--active-1", "coax-pill--active-2");
        if (connected && current === side) {
          pill.classList.add(side === "1" ? "coax-pill--active-1" : "coax-pill--active-2");
        }
      });
    });

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

    ["1", "2", "3"].forEach((sid) => {
      ["1", "2"].forEach((side) => {
        const pill = document.getElementById(`coax-view-${sid}-${side}`);
        if (pill) pill.classList.remove("coax-pill--active-1", "coax-pill--active-2");
      });
    });

    updateCoaxButtonsFromState({}, false);
    updateCoaxSchematic({}, false);
  }
}

setInterval(pollCoax, 2000);
pollCoax();

// ==================== Data page: charts ====================
let distChart = null;
let snrChart = null;

function buildCharts(ctxDist, ctxSnr) {
  distChart = new Chart(ctxDist, {
    type: "line",
    data: {
      labels: [],
      datasets: [{ label: "Earth–Moon distance [km]", data: [], borderWidth: 2, tension: 0.25, pointRadius: 2 }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: "#e5e7eb" } } },
      scales: {
        x: { ticks: { color: "#9ca3af", maxRotation: 45, minRotation: 0 }, grid: { display: false } },
        y: { ticks: { color: "#9ca3af" }, grid: { color: "rgba(55,65,81,0.4)" } },
      },
    },
  });

  snrChart = new Chart(ctxSnr, {
    type: "line",
    data: {
      labels: [],
      datasets: [{ label: "SNR [dB]", data: [], borderWidth: 2, tension: 0.25, pointRadius: 2 }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: "#e5e7eb" } } },
      scales: {
        x: { ticks: { color: "#9ca3af", maxRotation: 45, minRotation: 0 }, grid: { display: false } },
        y: { ticks: { color: "#9ca3af" }, grid: { color: "rgba(55,65,81,0.4)" } },
      },
    },
  });
}

async function refreshMeasurements() {
  const distCanvas = document.getElementById("distChart");
  const snrCanvas  = document.getElementById("snrChart");
  if (!distCanvas || !snrCanvas) return;

  if (!distChart || !snrChart) {
    buildCharts(distCanvas.getContext("2d"), snrCanvas.getContext("2d"));
  }

  try {
    const res = await fetch("/api/measurements", { cache: "no-store" });
    const data = await res.json();
    const meas = data.measurements || [];

    meas.sort((a, b) => (a.timestamp || "").localeCompare(b.timestamp || ""));

    const labels = meas.map((m) => (m.timestamp || "").replace("T", " ").slice(0, 19));
    const dist = meas.map((m) => m.distance_km);
    const snr  = meas.map((m) => m.snr_db);

    distChart.data.labels = labels;
    distChart.data.datasets[0].data = dist;
    distChart.update("none");

    snrChart.data.labels = labels;
    snrChart.data.datasets[0].data = snr;
    snrChart.update("none");
  } catch (e) {
    console.warn("Error fetching measurements:", e);
  }
}

// Called from data_page.html
function initDataPage() {
  refreshMeasurements();
  setInterval(refreshMeasurements, 5000);
}

// ==================== Measurement SSE Console (only) ====================
let measES = null;

function appendMeasLine(line) {
  const pre = document.getElementById("console");
  if (!pre) return;

  if (pre.textContent.trim() === "—") pre.textContent = "";
  pre.textContent += line + "\n";
  pre.scrollTop = pre.scrollHeight;
}

function clearMeasConsole() {
  const pre = document.getElementById("console");
  if (!pre) return;
  pre.textContent = "—";
}

function startMeasurementConsoleStream() {
  const pre = document.getElementById("console");
  if (!pre) return;

  if (measES) return;

  measES = new EventSource("/measurement/stream");

  measES.onmessage = (ev) => {
    if (!ev.data) return;
    appendMeasLine(ev.data);
  };

  measES.onerror = () => {
    // quiet; browser retries
  };
}

document.addEventListener("DOMContentLoaded", () => {
  const clearBtn = document.getElementById("consoleClearBtn");
  if (clearBtn) clearBtn.addEventListener("click", clearMeasConsole);

  startMeasurementConsoleStream();
});
