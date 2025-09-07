FROM python:3.11-slim

# Instalar ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*  # [19][10]

WORKDIR /app
COPY app/ /app/
COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt  # [12]

ENV PORT=8080
EXPOSE 8080

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8080", "app:app"]  # [12]
