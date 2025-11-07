FROM alpine:3.20

WORKDIR /usr/app

ENV TZ Europe/Moscow

RUN apk add --no-cache python3 py3-pip py3-opencv ffmpeg && \
    pip3 install --break-system-packages --no-cache-dir pytelegrambotapi aiohttp && \
    apk del py3-pip

ADD downloadbot downloadbot

ENTRYPOINT [ "python3", "-m", "downloadbot" ]
