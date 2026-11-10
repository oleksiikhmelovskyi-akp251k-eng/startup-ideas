"""
Практична робота №9. Веб-застосунок "AI-генератор ідей стартапів".

Як це працює:
1. Користувач у браузері обирає тему (освіта, здоров'я, ігри...) і тисне кнопку.
2. Браузер надсилає запит POST /api/generate на цей Flask-сервер.
3. Сервер формує запит (prompt) і звертається до ШІ-моделі
   (безкоштовні моделі через OpenRouter або Google Gemini).
4. Модель повертає JSON: назву, слоган, опис ідеї, емодзі та кольори логотипа.
5. Сервер перевіряє відповідь і віддає її браузеру, а той малює картку.

Ключ до API НЕ пишемо в код: він береться зі змінної середовища
OPENROUTER_API_KEY (або GEMINI_API_KEY) — на Render це Environment Variables.
"""

import json
import os
import re

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

API_URL = "https://generativelanguage.googleapis.com/v1beta"
API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
# Назву моделі можна змінити змінною середовища, не чіпаючи код.
PREFERRED_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest").strip()

# Альтернатива Gemini: OpenRouter (безкоштовні моделі). Якщо задано цей ключ,
# використовується він. Основна модель — Google Gemma 4 (добре пише українською);
# якщо вона зайнята, OpenRouter сам переходить до наступної зі списку
# (основну модель можна змінити змінною OPENROUTER_MODEL на Render).
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "google/gemma-4-31b-it:free").strip()
OPENROUTER_FALLBACKS = ["google/gemma-4-26b-a4b-it:free", "nvidia/nemotron-3-ultra-550b-a55b:free"]

TOPICS = [
    "Освіта", "Здоров'я", "Ігри", "Екологія", "Фінанси",
    "Подорожі", "Їжа", "Спорт", "Автоматизація", "Розумний дім",
]

PROMPT = """Ти — досвідчений стартап-ментор. Придумай одну оригінальну, реалістичну
ідею стартапу на тему: "{topic}".{extra}

Усі тексти пиши ТІЛЬКИ українською мовою (крім назви). Поверни ТІЛЬКИ JSON-об'єкт з такими полями:
- "name": коротка назва стартапу (1-2 слова, можна латиницею);
- "slogan": слоган до 8 слів;
- "idea": суть ідеї, 2-3 речення;
- "problem": яку проблему вирішує, 1 речення;
- "audience": цільова аудиторія, 1 речення;
- "monetization": як заробляє, 1 речення;
- "first_step": перший крок для запуску, 1 речення;
- "emoji": один емодзі для логотипа;
- "color1" і "color2": два кольори логотипа у форматі #RRGGBB, що пасують до теми.
"""

_model_cache = {"name": None}


class AIError(Exception):
    """Помилка звернення до ШІ з текстом, який можна показати користувачу."""


def _call_gemini(model, prompt):
    """Один запит до моделі. Повертає текст відповіді."""
    resp = requests.post(
        f"{API_URL}/models/{model}:generateContent",
        headers={"x-goog-api-key": API_KEY, "Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",  # просимо чистий JSON
                "temperature": 1.1,  # вища "креативність" — ідеї не повторюються
            },
        },
        timeout=60,
    )
    if resp.status_code == 404:
        raise LookupError(model)  # такої моделі немає — спробуємо іншу
    if resp.status_code == 429:
        raise AIError("Вичерпано безкоштовний ліміт запитів до ШІ. Спробуйте за хвилину.")
    if resp.status_code in (400, 401, 403):
        try:
            reason = resp.json()["error"]["message"]
        except (ValueError, KeyError, TypeError):
            reason = resp.text[:200]
        app.logger.error("Gemini %s: %s", resp.status_code, reason)
        raise AIError(f"ШІ-сервіс відхилив запит (код {resp.status_code}): {reason}")
    if not resp.ok:
        raise AIError(f"ШІ-сервіс тимчасово недоступний (код {resp.status_code}).")

    data = resp.json()
    try:
        parts = data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError):
        raise AIError("Модель не повернула відповідь. Спробуйте іншу тему.")
    # Беремо лише текст відповіді, без службових "роздумів" моделі.
    return "".join(p.get("text", "") for p in parts if not p.get("thought"))


def _find_flash_model():
    """Питає в API список моделей і обирає доступну Flash-модель."""
    resp = requests.get(
        f"{API_URL}/models",
        headers={"x-goog-api-key": API_KEY},
        params={"pageSize": 200},
        timeout=30,
    )
    if not resp.ok:
        raise AIError("Не вдалося отримати список моделей ШІ.")
    names = [
        m["name"].split("/", 1)[1]
        for m in resp.json().get("models", [])
        if "generateContent" in m.get("supportedGenerationMethods", [])
    ]
    skip = ("image", "tts", "audio", "live", "embedding")
    flash = [n for n in names if "flash" in n and not any(s in n for s in skip)]
    if not flash:
        raise AIError("Для цього ключа немає доступної текстової моделі.")
    stable = [n for n in flash if "preview" not in n and "exp" not in n]
    return sorted(stable or flash)[-1]  # найновіша за назвою


def _call_openrouter(prompt):
    """Запит до безкоштовних моделей OpenRouter (формат як в OpenAI)."""
    last_error = AIError("ШІ-сервіс не відповів. Спробуйте ще раз.")
    for _ in range(2):  # безкоштовні моделі іноді збоять — даємо другу спробу
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_KEY}",
                    "Content-Type": "application/json",
                    "X-Title": "AI Startup Ideas (PR9)",
                },
                json={
                    "models": [OPENROUTER_MODEL] + OPENROUTER_FALLBACKS,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 1.0,
                },
                timeout=50,  # дві спроби по 50 с — менше за таймаут gunicorn (120 с)
            )
        except requests.RequestException:
            last_error = AIError("Немає зв'язку з ШІ-сервісом.")
            continue
        if resp.status_code in (401, 403):
            raise AIError("OpenRouter відхилив ключ: перевірте OPENROUTER_API_KEY.")
        if resp.status_code == 429:
            raise AIError("Вичерпано безкоштовний ліміт запитів до ШІ. Спробуйте за хвилину.")
        if not resp.ok:
            last_error = AIError(f"ШІ-сервіс тимчасово недоступний (код {resp.status_code}).")
            continue
        data = resp.json()
        try:
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            continue
        if "{" in text:
            return text, data.get("model", OPENROUTER_MODEL)
    raise last_error


def ask_ai(prompt):
    """Обирає сервіс: OpenRouter (якщо є його ключ) або Google Gemini."""
    if OPENROUTER_KEY:
        return _call_openrouter(prompt)
    model = _model_cache["name"] or PREFERRED_MODEL
    try:
        text = _call_gemini(model, prompt)
    except LookupError:
        model = _find_flash_model()
        try:
            text = _call_gemini(model, prompt)
        except LookupError:
            raise AIError("Модель ШІ недоступна.")
    except requests.RequestException:
        raise AIError("Немає зв'язку з ШІ-сервісом.")
    _model_cache["name"] = model
    return text, model


def _color(value, default):
    """Пропускає лише коректний колір #RRGGBB (захист від сміття у відповіді)."""
    value = str(value or "").strip()
    return value if re.fullmatch(r"#[0-9a-fA-F]{6}", value) else default


def _emoji(value):
    """Пропускає лише справжній емодзі (без звичайних літер і цифр)."""
    value = str(value or "").strip()[:8]
    if not value or re.search(r"[0-9A-Za-zА-Яа-яІіЇїЄєҐґ]", value):
        return "🚀"
    return value


def parse_idea(text):
    """Перетворює відповідь моделі на охайний словник для картки."""
    # Деякі моделі спершу пишуть "роздуми" в <think>...</think> — прибираємо їх.
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    match = re.search(r"\{.*\}", text, re.S)  # на випадок ```json ... ```
    try:
        raw = json.loads(match.group(0) if match else text)
    except (json.JSONDecodeError, AttributeError):
        raise AIError("Модель повернула відповідь у неправильному форматі. Спробуйте ще раз.")
    if isinstance(raw, list) and raw:
        raw = raw[0]
    if not isinstance(raw, dict):
        raise AIError("Модель повернула відповідь у неправильному форматі. Спробуйте ще раз.")

    def field(key, limit):
        return str(raw.get(key) or "").strip()[:limit]

    idea = {
        "name": field("name", 40),
        "slogan": field("slogan", 120),
        "idea": field("idea", 700),
        "problem": field("problem", 300),
        "audience": field("audience", 300),
        "monetization": field("monetization", 300),
        "first_step": field("first_step", 300),
        "emoji": _emoji(raw.get("emoji")),
        "color1": _color(raw.get("color1"), "#6C4DF6"),
        "color2": _color(raw.get("color2"), "#F6A44D"),
    }
    if not idea["name"] or not idea["idea"]:
        raise AIError("Модель повернула неповну ідею. Спробуйте ще раз.")
    return idea


@app.get("/")
def index():
    return render_template("index.html", topics=TOPICS)


@app.post("/api/generate")
def generate():
    body = request.get_json(silent=True) or {}
    topic = str(body.get("topic") or "").strip()[:60]
    extra = str(body.get("extra") or "").strip()[:200]

    if not topic:
        return jsonify(error="Оберіть або введіть тему."), 400
    if not (OPENROUTER_KEY or API_KEY):
        return jsonify(error="На сервері не задано ключ OPENROUTER_API_KEY."), 503

    prompt = PROMPT.format(
        topic=topic,
        extra=f"\nПобажання користувача: {extra}" if extra else "",
    )
    try:
        text, model = ask_ai(prompt)
        idea = parse_idea(text)
    except AIError as err:
        return jsonify(error=str(err)), 502

    idea["topic"] = topic
    idea["model"] = model
    return jsonify(idea)


@app.get("/health")
def health():
    return jsonify(status="ok", openrouter=bool(OPENROUTER_KEY), gemini=bool(API_KEY))


if __name__ == "__main__":
    # Локальний запуск: python app.py  →  http://localhost:7860
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)), debug=False)
