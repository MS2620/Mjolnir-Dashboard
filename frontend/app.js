const API_BASE = "";

let currentTheme = "default";
let themes = [];

async function fetchThemes() {
  const res = await fetch(`${API_BASE}/themes`);
  if (!res.ok) return [];
  return await res.json();
}

async function loadTheme(name) {
  const cssLink = document.getElementById("theme-css");
  cssLink.href = `${API_BASE}/static/themes/${name}/styles.css`;

  const video = document.getElementById("bg-video");
  video.style.display = "none";
  video.src = "";

  const res = await fetch(`${API_BASE}/static/themes/${name}/config.json`);
  if (!res.ok) return;
  const cfg = await res.json();

  if (cfg.background === "video") {
    if (cfg.videoLocal) {
      video.src = `${API_BASE}/static/themes/${name}/${cfg.videoLocal}`;
    } else if (cfg.videoUrl) {
      video.src = cfg.videoUrl;
    }
    video.style.display = "block";
    await video.play().catch(() => {});
  }

  currentTheme = name;
  localStorage.setItem("mjolnir_theme", name);
}

async function initThemes() {
  themes = await fetchThemes();
  const select = document.getElementById("theme-select");
  select.innerHTML = "";

  for (const t of themes) {
    const opt = document.createElement("option");
    opt.value = t;
    opt.textContent = t;
    select.appendChild(opt);
  }

  const saved = localStorage.getItem("mjolnir_theme") || "default";
  if (themes.includes(saved)) {
    select.value = saved;
    await loadTheme(saved);
  } else if (themes.length) {
    await loadTheme(themes[0]);
  }

  select.addEventListener("change", () => loadTheme(select.value));
}

async function fetchSensors() {
  try {
    const res = await fetch(`${API_BASE}/sensors`);
    if (!res.ok) throw new Error("Bad status");
    return await res.json();
  } catch (e) {
    console.warn("Failed to fetch sensors", e);
    return null;
  }
}

function updateUI(data) {
  if (!data) return;

  const cpuTempEl = document.getElementById("cpu-temp");
  const gpuTempEl = document.getElementById("gpu-temp");
  const cpuLoadEl = document.getElementById("cpu-load");
  const gpuLoadEl = document.getElementById("gpu-load");

  if (data.cpu_temp != null) {
    cpuTempEl.textContent = `${data.cpu_temp.toFixed(1)} °C`;
    cpuTempEl.classList.toggle("warning", data.cpu_temp >= 80);
    cpuTempEl.classList.toggle("critical", data.cpu_temp >= 90);
  } else {
    cpuTempEl.textContent = "-- °C";
  }

  if (data.gpu_temp != null) {
    gpuTempEl.textContent = `${data.gpu_temp.toFixed(1)} °C`;
    gpuTempEl.classList.toggle("warning", data.gpu_temp >= 80);
    gpuTempEl.classList.toggle("critical", data.gpu_temp >= 90);
  } else {
    gpuTempEl.textContent = "-- °C";
  }

  if (data.cpu_load != null) {
    cpuLoadEl.textContent = `${(data.cpu_load * 100).toFixed(0)} %`;
  } else {
    cpuLoadEl.textContent = "-- %";
  }

  if (data.gpu_load != null) {
    gpuLoadEl.textContent = `${(data.gpu_load * 100).toFixed(0)} %`;
  } else {
    gpuLoadEl.textContent = "-- %";
  }
}

async function loop() {
  const data = await fetchSensors();
  updateUI(data);
  setTimeout(loop, 1000);
}

Promise.all([initThemes(), loop()]);