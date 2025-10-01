FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN ffmpeg -version

WORKDIR /app

COPY package.json tailwind.config.js ./

RUN npm install

COPY static/ ./static/
COPY templates/ ./templates/

RUN npx tailwindcss -i ./static/css/tw.dev.css -o ./static/css/tw.css --minify

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY app.py ./

ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8080

CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:8080", "--timeout", "300", "app:app"]
