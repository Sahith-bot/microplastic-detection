FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PORT=7860
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 7860
# One worker keeps memory low (the model is loaded once); threads handle several users at once.
CMD gunicorn -b 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 180 app:app
