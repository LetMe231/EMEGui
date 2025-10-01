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

    // label (skip 360° so 0° appears only once)
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

  const r = 100;
  const cx = c.width / 2, cy = c.height / 2;

  const isDark = document.body.classList.contains("dark-mode");
  const color = isDark ? "white" : "black";

  // circle
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, 2 * Math.PI);
  ctx.lineWidth = 2;
  ctx.strokeStyle = color;
  ctx.stroke();

  // ticks + labels
  drawTicks(ctx, cx, cy, r, 0, 360, 30, 90, color, false, false);

  // label
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

    // moon pointer (dashed)
    let radMoon = (azMoon - 90) * Math.PI / 180;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + r * Math.cos(radMoon), cy + r * Math.sin(radMoon));
    ctx.strokeStyle = isDark ? "yellow" : "orange";
    ctx.setLineDash([5, 5]);
    ctx.stroke();
    ctx.setLineDash([]);

    let radPark = (18 - 90) * Math.PI / 180; // 0° up
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
  const c = document.getElementById("elCanvas");
  if (!c) return;
  const ctx = c.getContext("2d");
  ctx.clearRect(0, 0, c.width, c.height);

  // Large quarter circle so it matches the full-circle footprint visually
  const Rq = 200;                      // quarter radius
  const cxCanvas = c.width / 2;        // 150 (canvas is 300)
  const cyCanvas = c.height / 2;       // 150
  const left = cxCanvas - 100;         // left of 200x200 box
  const top = cyCanvas - 100;          // top of 200x200 box
  const bottom = top + 200;
  const cx = left;                     // quarter center at bottom-left
  const cy = bottom;

  const isDark = document.body.classList.contains("dark-mode");
  const color = isDark ? "white" : "black";

  // quarter arc (top to right)
  ctx.beginPath();
  ctx.arc(cx, cy, Rq, -Math.PI / 2, 0);
  ctx.lineWidth = 2;
  ctx.strokeStyle = color;
  ctx.stroke();

  // ticks + labels OUTSIDE the arc
  drawTicks(ctx, cx, cy, Rq, 0, 90, 15, 30, color, true, true);

  // label
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
  const isDark = document.body.classList.contains("dark-mode");

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
    const isDark = document.body.classList.contains("dark-mode");
    const normalText = isDark ? "white" : "black";
    const moonText   = isDark ? "yellow" : "orange";
  try {
    const res = await fetch("/status");
    const data = await res.json();

    updateStatusBar(data.status, data.connected);

    // Numbers under the canvases (if you have those elements)
    const azText = document.getElementById("azText");
    const azMoonText = document.getElementById("azMoonText");
    const elText = document.getElementById("elText");
    const elMoonText = document.getElementById("elMoonText");

    if (azText) {
    azText.innerText = data.connected ? `Current angle: ${(+data.az).toFixed(1)}°` : "Current angle: --°";
    azText.style.color = normalText;
    }

    if (azMoonText) {
    azMoonText.innerText = `Moon angle: ${(+data.az_moon).toFixed(1)}°`;
    azMoonText.style.color = moonText;
    }

    if (elText) {
    elText.innerText = data.connected ? `Current angle: ${(+data.el).toFixed(1)}°` : "Current angle: --°";
    elText.style.color = normalText;
    }

    if (elMoonText) {
    elMoonText.innerText = `Moon angle: ${(+data.el_moon).toFixed(1)}°`;
    elMoonText.style.color = moonText;
    }
    
    if (isDark) {
    azMoonText.style.textShadow = "0 0 8px yellow";
    elMoonText.style.textShadow = "0 0 8px yellow";
    } else {
    azMoonText.style.textShadow = "";
    elMoonText.style.textShadow = "";
    }


    drawAzimuth(data.az, data.az_moon, data.connected);
    drawElevation(data.el, data.el_moon, data.connected);
  } catch (e) {
    // optional: show error on status bar
    updateStatusBar(`Fehler: ${e}`, false);
  }
}

// ==================== Init & Event Wiring ====================
document.addEventListener("DOMContentLoaded", () => {
  // Restore dark-mode preference
  const saved = localStorage.getItem("darkMode");
  if (saved === "true") document.body.classList.add("dark-mode");

  // Dark mode toggle (ensure type="button" in HTML to avoid submitting a form)
  const darkBtn = document.getElementById("darkModeBtn");
  if (darkBtn) {
    darkBtn.addEventListener("click", () => {
      document.body.classList.toggle("dark-mode");
      localStorage.setItem("darkMode", document.body.classList.contains("dark-mode") ? "true" : "false");
      refreshStatus(); // redraw dials with new colors
    });
  }

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

  // Setzen
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

 // Tracker toggle
document.getElementById("trackerBtn").onclick = async () => {
  let res = await fetch("/tracker", { method: "POST" });
  let data = await res.json();
  updateStatusBar(data.status, data.success);

  // Change button text
  const btn = document.getElementById("trackerBtn");
  if (data.tracking) {
    btn.innerText = "Tracker Stop";
    btn.classList.remove("btn-success");
    btn.classList.add("btn-danger");
  } else {
    btn.innerText = "Tracker Start";
    btn.classList.remove("btn-danger");
    btn.classList.add("btn-success");
  }

  refreshStatus();
};

// Stop button
document.getElementById("stopBtn").onclick = async () => {
  let res = await fetch("/stop", { method: "POST" });
  let data = await res.json();
  updateStatusBar(data.status, data.success);
  refreshStatus();
};

document.getElementById("parkBtn").onclick = async () => {
  const res = await fetch("/park", { method: "POST" });
  const data = await res.json();
  updateStatusBar(data.status, data.success);
  refreshStatus();
};



  // First draw + poll
  refreshStatus();
  setInterval(refreshStatus, 2000);
});
