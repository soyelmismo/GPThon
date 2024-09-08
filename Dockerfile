FROM python:slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=0
WORKDIR /

COPY bot/ /bot
COPY requirements.txt /requirements.txt
# Instalar dependencias
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3-pip \
    python3-numpy \
    sox \
    && \
    pip3 install --no-cache-dir -r requirements.txt \
    && \
    apt-get remove -y \
    && \
    rm -rf /var/lib/apt/lists/*
CMD ["python", "-m", "bot"]
