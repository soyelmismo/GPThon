FROM python:3.11.6-alpine3.18

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=0
WORKDIR /

COPY bot/ /bot
COPY requirements.txt /requirements.txt
# Instalar dependencias
RUN apk update && \
    apk add --no-cache --virtual .build-deps \
        py3-pip && \
    apk add --no-cache \
        sox  && \
    pip3 install --no-cache-dir -r requirements.txt && \
    apk del .build-deps && \
    rm -rf /var/cache/apk/*

CMD ["python", "-m", "bot"]
