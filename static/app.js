// Клієнтська частина: надсилає тему на сервер і малює картку стартапу.

const form = document.getElementById("form");
const topicInput = document.getElementById("topic");
const extraInput = document.getElementById("extra");
const goBtn = document.getElementById("go");
const statusEl = document.getElementById("status");
const resultEl = document.getElementById("result");
const historyBox = document.getElementById("history-box");
const historyEl = document.getElementById("history");

// Створює HTML-елемент із текстом. Текст від ШІ вставляємо тільки через
// textContent, щоб у сторінку не міг потрапити чужий HTML-код.
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

// Логотип: SVG-значок із градієнтом кольорів та емодзі, які обрав ШІ.
function buildLogo(idea) {
  const NS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", "0 0 100 100");
  svg.setAttribute("class", "logo");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Логотип " + idea.name);

  const id = "g" + Date.now();
  const defs = document.createElementNS(NS, "defs");
  const grad = document.createElementNS(NS, "linearGradient");
  grad.setAttribute("id", id);
  grad.setAttribute("x1", "0"); grad.setAttribute("y1", "0");
  grad.setAttribute("x2", "1"); grad.setAttribute("y2", "1");
  [idea.color1, idea.color2].forEach((color, i) => {
    const stop = document.createElementNS(NS, "stop");
    stop.setAttribute("offset", i === 0 ? "0%" : "100%");
    stop.setAttribute("stop-color", color);
    grad.appendChild(stop);
  });
  defs.appendChild(grad);

  const rect = document.createElementNS(NS, "rect");
  rect.setAttribute("width", "100"); rect.setAttribute("height", "100");
  rect.setAttribute("rx", "24");
  rect.setAttribute("fill", `url(#${id})`);

  const text = document.createElementNS(NS, "text");
  text.setAttribute("x", "50"); text.setAttribute("y", "54");
  text.setAttribute("text-anchor", "middle");
  text.setAttribute("dominant-baseline", "middle");
  text.setAttribute("font-size", "48");
  text.textContent = idea.emoji;

  svg.append(defs, rect, text);
  return svg;
}

function buildCard(idea) {
  const card = el("article", "card");

  const head = el("div", "card-head");
  const titles = el("div");
  titles.append(el("span", "tag", idea.topic), el("h3", "", idea.name), el("p", "slogan", "«" + idea.slogan + "»"));
  head.append(buildLogo(idea), titles);

  const body = el("div", "card-body");
  body.append(el("p", "", idea.idea));
  const dl = el("dl");
  [
    ["Проблема", idea.problem],
    ["Аудиторія", idea.audience],
    ["Монетизація", idea.monetization],
    ["Перший крок", idea.first_step],
  ].forEach(([label, value]) => {
    if (!value) return;
    const box = el("div");
    box.append(el("dt", "", label), el("dd", "", value));
    dl.appendChild(box);
  });
  body.appendChild(dl);

  const foot = el("div", "card-foot");
  const copyBtn = el("button", "ghost", "Скопіювати текст");
  copyBtn.type = "button";
  copyBtn.addEventListener("click", async () => {
    const text = `${idea.name} — ${idea.slogan}\n\n${idea.idea}\n\nПроблема: ${idea.problem}\nАудиторія: ${idea.audience}\nМонетизація: ${idea.monetization}\nПерший крок: ${idea.first_step}`;
    try {
      await navigator.clipboard.writeText(text);
      copyBtn.textContent = "Скопійовано";
    } catch {
      copyBtn.textContent = "Не вдалося скопіювати";
    }
    setTimeout(() => (copyBtn.textContent = "Скопіювати текст"), 1500);
  });
  foot.append(el("span", "", "Згенеровано моделлю " + idea.model), copyBtn);

  card.append(head, body, foot);
  return card;
}

function addToHistory(idea) {
  const li = el("li");
  li.append(el("b", "", idea.emoji + " " + idea.name), el("span", "muted", "— " + idea.slogan));
  historyEl.prepend(li);
  historyBox.hidden = false;
}

function setStatus(text, isError) {
  statusEl.textContent = text;
  statusEl.classList.toggle("error", Boolean(isError));
}

// Кнопки-теми: клік підставляє тему в поле.
document.getElementById("chips").addEventListener("click", (event) => {
  const chip = event.target.closest(".chip");
  if (!chip) return;
  document.querySelectorAll(".chip").forEach((c) => c.classList.toggle("active", c === chip));
  topicInput.value = chip.dataset.topic;
});

topicInput.addEventListener("input", () => {
  document.querySelectorAll(".chip").forEach((c) =>
    c.classList.toggle("active", c.dataset.topic === topicInput.value.trim()));
});

let lastIdea = null;

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const topic = topicInput.value.trim();
  if (!topic) return;

  goBtn.disabled = true;
  setStatus("ШІ думає над ідеєю…");

  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic, extra: extraInput.value.trim() }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Помилка сервера.");

    if (lastIdea) addToHistory(lastIdea); // попередню картку переносимо в історію
    lastIdea = data;
    resultEl.replaceChildren(buildCard(data));
    setStatus("");
    goBtn.textContent = "Згенерувати ще одну";
  } catch (error) {
    setStatus(error.message || "Щось пішло не так. Спробуйте ще раз.", true);
  } finally {
    goBtn.disabled = false;
  }
});
