FROM python:3.11-slim

# Instalar ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar todos os arquivos e pastas da raiz do projeto para /app no container
COPY . /app/

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

ENV PORT=8080
EXPOSE 8080

# Comando para iniciar a aplicação Flask via Gunicorn
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8080", "app:app"]
