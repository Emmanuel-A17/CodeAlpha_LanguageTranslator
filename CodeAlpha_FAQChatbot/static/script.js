const $ = (id) => document.getElementById(id);

// Adresse du serveur Flask (utile si la page est ouverte via Live Server)
const API_BASE = location.port === "5000" ? "" : "http://127.0.0.1:5000";
const SERVER_HELP =
  "Le serveur Python ne répond pas. Lancez « python app.py » puis ouvrez http://127.0.0.1:5000";

const els = {
  messages: $("messages"),
  chips: $("chips"),
  form: $("chatForm"),
  input: $("messageInput"),
  sendBtn: $("sendBtn"),
  clearBtn: $("clearBtn"),
  themeBtn: $("themeBtn"),
  menuBtn: $("menuBtn"),
  closePanel: $("closePanel"),
  panel: $("faqPanel"),
  overlay: $("overlay"),
  faqList: $("faqList"),
  statusDot: $("statusDot"),
  statusText: $("statusText"),
  toast: $("toast"),
};

const WELCOME =
  "Bonjour ! 👋 Je suis l'assistant virtuel de Nova Shop.\n" +
  "Posez-moi une question sur vos commandes, la livraison, le paiement, les retours ou votre compte, " +
  "ou choisissez une question ci-dessous.";

let busy = false;
let history = [];
try { history = JSON.parse(localStorage.getItem("faq_chat") || "[]"); } catch { history = []; }

/* ---------- Utilitaires ---------- */
function toast(message, isError = false) {
  els.toast.textContent = message;
  els.toast.classList.toggle("error", isError);
  els.toast.classList.add("show");
  clearTimeout(toast.t);
  toast.t = setTimeout(() => els.toast.classList.remove("show"), 2600);
}

function nowTime() {
  return new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

function scrollDown() {
  els.messages.scrollTop = els.messages.scrollHeight;
}

function save() {
  try { localStorage.setItem("faq_chat", JSON.stringify(history.slice(-40))); } catch { /* ignoré */ }
}

async function api(path, options) {
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, options);
  } catch {
    throw new Error(SERVER_HELP);
  }
  const raw = await res.text();
  let data = {};
  try { data = raw ? JSON.parse(raw) : {}; } catch { data = {}; }
  if (!res.ok || Object.keys(data).length === 0) throw new Error(data.error || SERVER_HELP);
  return data;
}

/* ---------- Affichage des messages ---------- */
function makeAvatar(role) {
  const a = document.createElement("div");
  a.className = "avatar";
  a.textContent = role === "user" ? "Moi" : "AI";
  return a;
}

function chipButton(item) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = "chip";
  b.textContent = item.question;
  b.addEventListener("click", () => send(item.question, item.id));
  return b;
}

function renderMessage(m, animate = true) {
  const row = document.createElement("div");
  row.className = `msg ${m.role}${m.error ? " error" : ""}`;
  if (!animate) row.style.animation = "none";

  const wrap = document.createElement("div");
  wrap.className = "bubble-wrap";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = m.text;
  wrap.appendChild(bubble);

  // Informations de correspondance (similarité cosinus)
  if (m.role === "bot" && m.matched_question) {
    const meta = document.createElement("div");
    meta.className = "meta";
    const pct = Math.min(100, Math.round((m.confidence || 0) * 100));
    const conf = document.createElement("span");
    conf.className = `tag ${m.type === "answer" ? "good" : "mid"}`;
    conf.textContent = m.type === "answer" ? `Correspondance ${pct} %` : `Réponse incertaine · ${pct} %`;
    meta.appendChild(conf);
    if (m.category) {
      const cat = document.createElement("span");
      cat.className = "tag";
      cat.textContent = m.category;
      meta.appendChild(cat);
    }
    const q = document.createElement("span");
    q.className = "matched";
    q.textContent = `Question reconnue : « ${m.matched_question} »`;
    meta.appendChild(q);
    wrap.appendChild(meta);
  }

  if (m.role === "bot" && m.suggestions && m.suggestions.length) {
    const title = document.createElement("div");
    title.className = "suggest-title";
    title.textContent = m.type === "fallback" ? "Essayez plutôt :" : "Questions liées :";
    const chips = document.createElement("div");
    chips.className = "chips";
    m.suggestions.forEach((s) => chips.appendChild(chipButton(s)));
    wrap.append(title, chips);
  }

  const time = document.createElement("span");
  time.className = "meta time";
  time.textContent = m.time;
  wrap.appendChild(time);

  row.append(makeAvatar(m.role), wrap);
  els.messages.appendChild(row);
  scrollDown();
}

function addMessage(m) {
  m.time = nowTime();
  history.push(m);
  save();
  renderMessage(m);
}

function showTyping() {
  const row = document.createElement("div");
  row.className = "msg bot typing";
  row.id = "typing";
  const wrap = document.createElement("div");
  wrap.className = "bubble-wrap";
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = "<span></span><span></span><span></span>";
  wrap.appendChild(bubble);
  row.append(makeAvatar("bot"), wrap);
  els.messages.appendChild(row);
  scrollDown();
}

function hideTyping() {
  const t = $("typing");
  if (t) t.remove();
}

/* ---------- Envoi d'une question ---------- */
async function send(text, faqId = null) {
  text = (text || "").trim();
  if (!text || busy) return;

  busy = true;
  els.sendBtn.disabled = true;
  els.chips.innerHTML = "";
  closePanel();

  addMessage({ role: "user", text });
  els.input.value = "";
  showTyping();

  try {
    const [data] = await Promise.all([
      api("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(faqId ? { message: text, faq_id: faqId } : { message: text }),
      }),
      new Promise((r) => setTimeout(r, 450)), // petit délai naturel
    ]);
    hideTyping();
    addMessage({
      role: "bot",
      text: data.reply,
      type: data.type,
      confidence: data.confidence,
      matched_question: data.matched_question,
      category: data.category,
      suggestions: data.suggestions,
    });
    setStatus(true);
  } catch (err) {
    hideTyping();
    addMessage({ role: "bot", text: err.message || SERVER_HELP, error: true });
    setStatus(false);
  } finally {
    busy = false;
    els.sendBtn.disabled = false;
    els.input.focus();
  }
}

/* ---------- Initialisation ---------- */
function setStatus(online, text) {
  els.statusDot.className = `dot ${online ? "online" : "offline"}`;
  els.statusText.textContent = text || (online ? "En ligne" : "Serveur injoignable");
}

function renderFaqPanel(catalog) {
  els.faqList.innerHTML = "";
  Object.entries(catalog).forEach(([category, items], index) => {
    const details = document.createElement("details");
    if (index === 0) details.open = true;
    const summary = document.createElement("summary");
    summary.innerHTML = "";
    const name = document.createElement("span");
    name.textContent = category;
    const count = document.createElement("span");
    count.className = "count";
    count.textContent = items.length;
    name.appendChild(count);
    summary.appendChild(name);
    details.appendChild(summary);
    items.forEach((item) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "faq-q";
      b.textContent = item.question;
      b.addEventListener("click", () => send(item.question, item.id));
      details.appendChild(b);
    });
    els.faqList.appendChild(details);
  });
}

function showWelcome() {
  history = [];
  els.messages.innerHTML = "";
  addMessage({ role: "bot", text: WELCOME });
}

async function init() {
  applyTheme(localStorage.getItem("faq_theme") || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));

  if (history.length) {
    history.forEach((m) => renderMessage(m, false));
    scrollDown();
  } else {
    showWelcome();
  }

  try {
    const health = await api("/api/health");
    setStatus(true, `En ligne · ${health.faqs} FAQ · NLP ${health.nlp}`);
    renderFaqPanel(await api("/api/faqs"));
    if (history.length <= 1) {
      (await api("/api/suggestions")).forEach((s) => els.chips.appendChild(chipButton(s)));
    }
  } catch (err) {
    setStatus(false);
    toast(err.message, true);
  }
}

/* ---------- Panneau mobile, thème, nouvelle conversation ---------- */
function openPanel() { els.panel.classList.add("open"); els.overlay.classList.add("show"); }
function closePanel() { els.panel.classList.remove("open"); els.overlay.classList.remove("show"); }

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  try { localStorage.setItem("faq_theme", theme); } catch { /* ignoré */ }
  $("themeIcon").innerHTML =
    theme === "dark"
      ? '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>'
      : '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>';
}

els.form.addEventListener("submit", (e) => { e.preventDefault(); send(els.input.value); });
els.menuBtn.addEventListener("click", openPanel);
els.closePanel.addEventListener("click", closePanel);
els.overlay.addEventListener("click", closePanel);
els.themeBtn.addEventListener("click", () =>
  applyTheme(document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark")
);
els.clearBtn.addEventListener("click", async () => {
  showWelcome();
  els.chips.innerHTML = "";
  try { (await api("/api/suggestions")).forEach((s) => els.chips.appendChild(chipButton(s))); } catch { /* ignoré */ }
  els.input.focus();
});

init();
