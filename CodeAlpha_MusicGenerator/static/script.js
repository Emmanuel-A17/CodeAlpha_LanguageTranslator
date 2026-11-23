// Si la page est ouverte autrement que via http://127.0.0.1:5000 (Live Server, double-clic), on vise le serveur Flask.
const API_BASE = location.port === "5000" ? "" : "http://127.0.0.1:5000";

const $ = (id) => document.getElementById(id);
const els = {
  model: $("model"), seconds: $("seconds"), tempo: $("tempo"), temperature: $("temperature"), seed: $("seed"),
  button: $("generate"), message: $("message"), player: $("player"), roll: $("roll"), audio: $("audio"),
  dlMidi: $("dlMidi"), dlWav: $("dlWav"), meta: $("meta"),
};

let current = null;   // dernier morceau généré
let raf = null;

function bindOutput(input, out, format) {
  const update = () => { out.textContent = format(input.value); };
  input.addEventListener("input", update);
  update();
}
bindOutput(els.seconds, $("secondsOut"), (v) => `${v} s`);
bindOutput(els.tempo, $("tempoOut"), (v) => `${v} BPM`);
bindOutput(els.temperature, $("temperatureOut"), (v) => Number(v).toFixed(2));

function setMessage(text, isError = false) {
  els.message.textContent = text;
  els.message.classList.toggle("error", isError);
}

async function loadStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/status`);
    const data = await res.json();
    els.model.innerHTML = data.models.map((m) => `<option value="${m.id}">${m.label}</option>`).join("");
    if (!data.models.length) {
      els.button.disabled = true;
      setMessage("Aucun modèle entraîné. Lancez : python collect_data.py --demo puis python train.py", true);
    } else if (data.lstm_error) {
      setMessage("LSTM indisponible (PyTorch manquant ?) — modèle de référence utilisé.", true);
    }
  } catch {
    els.button.disabled = true;
    setMessage("Le serveur Python ne répond pas. Lancez « python app.py » puis ouvrez http://127.0.0.1:5000", true);
  }
}

async function compose() {
  els.button.disabled = true;
  els.button.querySelector(".spinner").hidden = false;
  els.button.querySelector(".label").textContent = "Composition en cours…";
  setMessage("");
  try {
    const res = await fetch(`${API_BASE}/api/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: els.model.value,
        seconds: Number(els.seconds.value),
        tempo: Number(els.tempo.value),
        temperature: Number(els.temperature.value),
        seed: els.seed.value === "" ? null : Number(els.seed.value),
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erreur de génération");
    show(data);
  } catch (err) {
    setMessage(err.message === "Failed to fetch" ? "Le serveur Python ne répond pas." : err.message, true);
  } finally {
    els.button.disabled = false;
    els.button.querySelector(".spinner").hidden = true;
    els.button.querySelector(".label").textContent = "Composer";
  }
}

function show(data) {
  current = data;
  els.player.hidden = false;
  els.audio.src = API_BASE + data.wav;
  els.dlMidi.href = API_BASE + data.midi;
  els.dlWav.href = API_BASE + data.wav;
  els.meta.textContent = `${data.notes.length} notes · ${data.duration.toFixed(1)} s · ${data.tempo} BPM`;
  draw(0);
  els.audio.play().catch(() => {});   // le navigateur peut refuser la lecture automatique : le lecteur reste utilisable
}

// ---- Piano roll ---------------------------------------------------------------------------
function draw(time) {
  if (!current) return;
  const canvas = els.roll;
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
  }
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);

  const pitches = current.notes.map((n) => n[2]);
  const low = Math.min(...pitches) - 2, high = Math.max(...pitches) + 2;
  const rowH = h / (high - low + 1);
  const x = (t) => (t / current.duration) * w;

  // lignes d'octave (Do)
  ctx.strokeStyle = "rgba(255,255,255,0.07)";
  ctx.lineWidth = 1;
  for (let p = low; p <= high; p++) {
    if (p % 12 === 0) {
      const y = h - (p - low + 0.5) * rowH;
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
    }
  }

  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, "#f9a8d4");
  grad.addColorStop(1, "#8b5cf6");
  for (const [start, end, pitch] of current.notes) {
    const playing = time >= start && time < end;
    ctx.fillStyle = playing ? "#ffffff" : grad;
    ctx.globalAlpha = playing ? 1 : 0.85;
    const nx = x(start), nw = Math.max(2, x(end) - nx - 1);
    const ny = h - (pitch - low + 1) * rowH;
    ctx.beginPath();
    ctx.roundRect(nx, ny + 0.5, nw, Math.max(2, rowH - 1), 2);
    ctx.fill();
  }
  ctx.globalAlpha = 1;

  // curseur de lecture
  ctx.strokeStyle = "rgba(255,255,255,0.9)";
  ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(x(time), 0); ctx.lineTo(x(time), h); ctx.stroke();
}

function loop() {
  draw(els.audio.currentTime);
  raf = requestAnimationFrame(loop);
}
els.audio.addEventListener("play", () => { cancelAnimationFrame(raf); loop(); });
els.audio.addEventListener("pause", () => cancelAnimationFrame(raf));
els.audio.addEventListener("ended", () => { cancelAnimationFrame(raf); draw(0); });
els.audio.addEventListener("seeked", () => draw(els.audio.currentTime));
window.addEventListener("resize", () => draw(els.audio.currentTime || 0));

// Clic sur le rouleau : se déplacer dans le morceau
els.roll.addEventListener("click", (e) => {
  if (!current) return;
  const rect = els.roll.getBoundingClientRect();
  els.audio.currentTime = ((e.clientX - rect.left) / rect.width) * current.duration;
});

els.button.addEventListener("click", compose);
loadStatus();
