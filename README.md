---
title: AI Startup Ideas
emoji: 🚀
colorFrom: blue
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

# AI-генератор ідей стартапів

Практична робота №9 «Створення веб-застосунку за допомогою ШІ».

Користувач обирає тему, а ШІ (безкоштовні моделі через OpenRouter) видає ідею стартапу, назву, слоган
і кольори з емодзі для логотипа. Результат показується карткою.

## Технології

- **Backend:** Python, Flask (`app.py`), запуск через gunicorn
- **ШІ:** OpenRouter API, безкоштовна модель Google Gemma 4 із запасними моделями (запит із сервера, відповідь у форматі JSON); запасний варіант — Google Gemini
- **Frontend:** HTML, CSS, JavaScript (`templates/`, `static/`)
- **Публікація:** Render (Web Service, з GitHub)

## Файли

| Файл | Призначення |
|---|---|
| `app.py` | сервер: сторінка `/` та API `/api/generate` |
| `templates/index.html` | розмітка сторінки |
| `static/app.js` | запит до сервера, побудова картки й логотипа |
| `static/style.css` | оформлення |
| `requirements.txt` | бібліотеки Python |
| `gunicorn.conf.py` | налаштування сервера (таймаут 120 с для повільних моделей) |
| `Dockerfile` | запасний варіант запуску через Docker |

## Локальний запуск

```
pip install -r requirements.txt
set OPENROUTER_API_KEY=ваш_ключ
python app.py
```

Після цього відкрити http://localhost:7860

## Ключ API

Ключ не зберігається в коді. На Render його додано в Environment →
Environment Variables з назвою `OPENROUTER_API_KEY`.
