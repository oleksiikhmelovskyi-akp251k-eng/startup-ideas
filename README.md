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

Користувач обирає тему, а ШІ (Google Gemini) видає ідею стартапу, назву, слоган
і кольори з емодзі для логотипа. Результат показується карткою.

## Технології

- **Backend:** Python, Flask (`app.py`), запуск через gunicorn
- **ШІ:** Google Gemini API (запит із сервера, відповідь у форматі JSON)
- **Frontend:** HTML, CSS, JavaScript (`templates/`, `static/`)
- **Публікація:** Hugging Face Spaces (Docker)

## Файли

| Файл | Призначення |
|---|---|
| `app.py` | сервер: сторінка `/` та API `/api/generate` |
| `templates/index.html` | розмітка сторінки |
| `static/app.js` | запит до сервера, побудова картки й логотипа |
| `static/style.css` | оформлення |
| `requirements.txt` | бібліотеки Python |
| `Dockerfile` | збирання для Hugging Face Spaces |

## Локальний запуск

```
pip install -r requirements.txt
set GEMINI_API_KEY=ваш_ключ
python app.py
```

Після цього відкрити http://localhost:7860

## Ключ API

Ключ не зберігається в коді. На Hugging Face Spaces його треба додати в
Settings → Variables and secrets → New secret з назвою `GEMINI_API_KEY`.
