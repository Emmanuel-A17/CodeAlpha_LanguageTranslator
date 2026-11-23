const $ = (id) => document.getElementById(id);

const els = {
  source: $("sourceLang"),
  target: $("targetLang"),
  input: $("inputText"),
  output: $("outputText"),
  counter: $("counter"),
  detected: $("detected"),
  translateBtn: $("translateBtn"),
  swapBtn: $("swapBtn"),
  copyBtn: $("copyBtn"),
  clearBtn: $("clearBtn"),
  speakIn: $("speakInBtn"),
  speakOut: $("speakOutBtn"),
  themeBtn: $("themeBtn"),
  toast: $("toast"),
  historySection: $("historySection"),
  historyList: $("historyList"),
  clearHistory: $("clearHistory"),
};

let languages = {};
let lastResult = { text: "", lang: "" };
let history = JSON.parse(localStorage.getItem("lingua_history") || "[]");

/* ---------- Utilitaires ---------- */
function toast(message, isError = false) {
  els.toast.textContent = message;
  els.toast.classList.toggle("error", isError);
  els.toast.classList.add("show");
  clearTimeout(toast.t);
  toast.t = setTimeout(() => els.toast.classList.remove("show"), 2400);
}

function speechLang(code) {
  const map = { "zh-CN": "zh-CN", "zh-TW": "zh-TW", no: "nb-NO", tl: "fil-PH" };
  return map[code] || code;
}

/* ---------- Initialisation ---------- */
async function init() {
  applyTheme(localStorage.getItem("lingua_theme") || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));

  try {
    const res = await fetch("/api/languages");
    languages = await res.json();
  } catch {
    toast("Impossible de charger les langues.", true);
    return;
  }

  const entries = Object.entries(languages);
  const auto = entries.filter(([c]) => c === "auto");
  const rest = entries.filter(([c]) => c !== "auto").sort((a, b) => a[1].localeCompare(b[1], "fr"));

  fill(els.source, [...auto, ...rest]);
  fill(els.target, rest);

  els.source.value = localStorage.getItem("lingua_src") || "auto";
  els.target.value = localStorage.getItem("lingua_dst") || "en";

  renderHistory();
  updateCounter();
}

function fill(select, items) {
  select.innerHTML = items.map(([c, n]) => `<option value="${c}">${n}</option>`).join("");
}

/* ---------- Traduction ---------- */
async function translate() {
  const text = els.input.value.trim();
  if (!text) {
    toast("Veuillez saisir un texte à traduire.", true);
    els.input.focus();
    return;
  }

  setLoading(true);
  try {
    const res = await fetch("/api/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, source: els.source.value, target: els.target.value }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Erreur de traduction.");

    showResult(data.translation, els.target.value);

    if (els.source.value === "auto" && data.detected && languages[data.detected]) {
      els.detected.textContent = `Détecté : ${languages[data.detected]}`;
    } else {
      els.detected.textContent = "";
    }

    addHistory({
      src: text,
      dst: data.translation,
      from: els.source.value === "auto" ? (data.detected || "auto") : els.source.value,
      to: els.target.value,
    });
  } catch (err) {
    toast(err.message || "Erreur réseau.", true);
  } finally {
    setLoading(false);
  }
}

function showResult(text, lang) {
  lastResult = { text, lang };
  els.output.textContent = text;
  els.output.classList.remove("placeholder");
  els.output.classList.remove("fade");
  void els.output.offsetWidth; // relance l'animation
  els.output.classList.add("fade");
  els.copyBtn.disabled = false;
  els.speakOut.disabled = false;
}

function resetResult() {
  lastResult = { text: "", lang: "" };
  els.output.textContent = "La traduction apparaîtra ici";
  els.output.classList.add("placeholder");
  els.detected.textContent = "";
  els.copyBtn.disabled = true;
  els.speakOut.disabled = true;
}

function setLoading(on) {
  els.translateBtn.disabled = on;
  els.translateBtn.classList.toggle("loading", on);
  els.translateBtn.querySelector(".btn-label").textContent = on ? "Traduction…" : "Traduire";
}

function updateCounter() {
  els.counter.textContent = `${els.input.value.length} / 5000`;
}

/* ---------- Fonctions annexes ---------- */
async function copyResult() {
  if (!lastResult.text) return;
  try {
    await navigator.clipboard.writeText(lastResult.text);
    toast("Traduction copiée ✓");
  } catch {
    const ta = document.createElement("textarea");
    ta.value = lastResult.text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
    toast("Traduction copiée ✓");
  }
}

function speak(text, lang) {
  if (!("speechSynthesis" in window)) {
    toast("La synthèse vocale n'est pas supportée par ce navigateur.", true);
    return;
  }
  if (!text) return;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  if (lang && lang !== "auto") u.lang = speechLang(lang);
  speechSynthesis.speak(u);
}

function swap() {
  const src = els.source.value;
  const dst = els.target.value;
  const newTarget = src === "auto" ? "en" : src;
  els.source.value = dst;
  els.target.value = newTarget;
  if (lastResult.text) {
    els.input.value = lastResult.text;
    updateCounter();
    translate();
  }
  persistLangs();
}

function persistLangs() {
  localStorage.setItem("lingua_src", els.source.value);
  localStorage.setItem("lingua_dst", els.target.value);
}

/* ---------- Historique ---------- */
function addHistory(item) {
  history = [item, ...history.filter((h) => !(h.src === item.src && h.to === item.to))].slice(0, 8);
  localStorage.setItem("lingua_history", JSON.stringify(history));
  renderHistory();
}

function renderHistory() {
  els.historySection.hidden = history.length === 0;
  els.historyList.innerHTML = "";
  history.forEach((h, i) => {
    const li = document.createElement("li");
    li.dataset.index = i;
    const langs = document.createElement("div");
    langs.className = "h-langs";
    langs.textContent = `${languages[h.from] || h.from} → ${languages[h.to] || h.to}`;
    const src = document.createElement("div");
    src.className = "h-src";
    src.textContent = h.src;
    const dst = document.createElement("div");
    dst.className = "h-dst";
    dst.textContent = h.dst;
    li.append(langs, src, dst);
    els.historyList.appendChild(li);
  });
}

/* ---------- Thème ---------- */
function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("lingua_theme", theme);
  $("themeIcon").innerHTML =
    theme === "dark"
      ? '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>'
      : '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>';
}

/* ---------- Événements ---------- */
els.translateBtn.addEventListener("click", translate);
els.swapBtn.addEventListener("click", swap);
els.copyBtn.addEventListener("click", copyResult);
els.speakIn.addEventListener("click", () => speak(els.input.value, els.source.value));
els.speakOut.addEventListener("click", () => speak(lastResult.text, lastResult.lang));
els.clearBtn.addEventListener("click", () => {
  els.input.value = "";
  updateCounter();
  resetResult();
  els.input.focus();
});
els.input.addEventListener("input", updateCounter);
els.input.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") translate();
});
els.source.addEventListener("change", persistLangs);
els.target.addEventListener("change", () => {
  persistLangs();
  if (els.input.value.trim() && lastResult.text) translate();
});
els.themeBtn.addEventListener("click", () =>
  applyTheme(document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark")
);
els.historyList.addEventListener("click", (e) => {
  const li = e.target.closest("li");
  if (!li) return;
  const h = history[li.dataset.index];
  els.input.value = h.src;
  els.source.value = h.from in languages ? h.from : "auto";
  els.target.value = h.to;
  updateCounter();
  showResult(h.dst, h.to);
  window.scrollTo({ top: 0, behavior: "smooth" });
});
els.clearHistory.addEventListener("click", () => {
  history = [];
  localStorage.removeItem("lingua_history");
  renderHistory();
});

init();
