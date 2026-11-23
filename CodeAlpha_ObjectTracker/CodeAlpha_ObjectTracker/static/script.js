const API_BASE = location.port === "5000" ? "" : "http://127.0.0.1:5000";
const $ = (id) => document.getElementById(id);
let mode = "camera", timer = null;

function setMessage(text, error = false) {
  $("message").textContent = text;
  $("message").classList.toggle("error", error);
}

function setMode(next) {
  mode = next;
  $("tabCam").classList.toggle("active", next === "camera");
  $("tabFile").classList.toggle("active", next === "file");
  $("camBox").hidden = next !== "camera";
  $("fileBox").hidden = next !== "file";
}
$("tabCam").onclick = () => setMode("camera");
$("tabFile").onclick = () => setMode("file");
$("conf").oninput = () => { $("confOut").textContent = Number($("conf").value).toFixed(2); };

fetch(`${API_BASE}/api/classes`).then((r) => r.json()).then((list) => {
  $("classList").innerHTML = list.map((c) => `<option value="${c}">`).join("");
}).catch(() => {});

async function start() {
  setMessage("");
  $("start").disabled = true;
  const classes = $("classes").value.split(",").map((s) => s.trim()).filter(Boolean).join(",");
  try {
    let res;
    if (mode === "file") {
      const file = $("video").files[0];
      if (!file) throw new Error("Choisissez d'abord un fichier vidéo.");
      const form = new FormData();
      form.append("video", file);
      form.append("conf", $("conf").value);
      form.append("classes", classes);
      setMessage("Envoi de la vidéo…");
      res = await fetch(`${API_BASE}/api/start`, { method: "POST", body: form });
    } else {
      res = await fetch(`${API_BASE}/api/start`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ camera: $("camera").value, conf: $("conf").value, classes }),
      });
    }
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erreur");
    setMessage("Chargement du modèle…");
    $("feed").hidden = false;
    $("placeholder").hidden = true;
    $("feed").src = `${API_BASE}/stream?t=${Date.now()}`;
    $("stop").disabled = false;
    clearInterval(timer);
    timer = setInterval(pollStats, 700);
  } catch (err) {
    setMessage(err.message === "Failed to fetch" ? "Le serveur Python ne répond pas. Lancez « python app.py »." : err.message, true);
  } finally {
    $("start").disabled = false;
  }
}

async function pollStats() {
  try {
    const s = await (await fetch(`${API_BASE}/api/stats`)).json();
    if (s.error) { setMessage(s.error, true); halt(false); return; }
    if (!s.frame) return;
    setMessage("");
    const chips = [`<span class="chip"><b>${s.fps}</b> FPS</span>`];
    for (const [name, n] of Object.entries(s.visible || {})) chips.push(`<span class="chip">${name} visibles : <b>${n}</b></span>`);
    const totals = Object.entries(s.total || {}).map(([k, v]) => `${k} ${v}`).join(" · ");
    if (totals) chips.push(`<span class="chip">Objets distincts : <b>${totals}</b></span>`);
    if (s.ended) { chips.push('<span class="chip">Vidéo terminée</span>'); halt(false); }
    $("stats").innerHTML = chips.join("");
  } catch { /* on réessaie au prochain tour */ }
}

function halt(callServer = true) {
  clearInterval(timer);
  $("stop").disabled = true;
  if (callServer) fetch(`${API_BASE}/api/stop`, { method: "POST" }).catch(() => {});
}
$("stop").onclick = () => halt();
$("start").onclick = start;
