FROM python:3.11-slim

# Instalar dependências do sistema
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Verificar FFmpeg
RUN ffmpeg -version

WORKDIR /app

# Copiar arquivos de configuração do Node.js
COPY package.json tailwind.config.js ./

# Instalar Tailwind
RUN npm install

# Copiar arquivos CSS e templates
COPY static/ ./static/
COPY templates/ ./templates/

# Build do CSS do Tailwind
RUN npx tailwindcss -i ./static/css/tw.dev.css -o ./static/css/tw.css --minify

# Copiar requirements e instalar dependências Python
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar aplicação Python
COPY app.py ./

# Variáveis de ambiente
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8080

# Comando para iniciar
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:8080", "--timeout", "300", "app:app"]
