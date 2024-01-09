FROM python:3.12-alpine

WORKDIR /usr/app

ENV TZ Europe/Moscow

ADD requirements.txt .

RUN apk update && apk add gcc musl-dev && \
    pip install --no-cache-dir -r requirements.txt && \
    apk del gcc musl-dev && apk cache clean

ADD bot bot

ENTRYPOINT [ "python", "-m", "bot" ]
