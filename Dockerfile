# Інструкція для Hugging Face Spaces: як зібрати й запустити застосунок.
FROM python:3.12-slim

# Spaces запускає контейнер від користувача з ID 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR $HOME/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user . .

# Spaces очікує веб-сервер на порту 7860
EXPOSE 7860
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--workers", "2", "--timeout", "90", "app:app"]
