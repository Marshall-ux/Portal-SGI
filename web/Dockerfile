FROM python:3.12-slim

# tzdata: "Última actualización" y el reporte se muestran en la zona horaria de TZ
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY config ./config

# Sin privilegios: la app solo lee la copia del disco (volumen montado en solo lectura)
RUN useradd --system --no-create-home portal
USER portal

ENV PORTAL_DATOS=/data \
    PYTHONUNBUFFERED=1
EXPOSE 5001

# /salud responde 503 hasta que termina la primera sincronización
HEALTHCHECK --interval=60s --timeout=5s --start-period=30s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5001/salud', timeout=4)"

# Hilos para atender varias descargas a la vez (la Guía de Acceso pesa ~50 MB)
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "2", "--threads", "8", "--timeout", "120", \
     "--access-logfile", "-", "app:create_app()"]
