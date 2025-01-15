import os
import tempfile
import asyncio

import aiohttp
import cv2

from dataclasses import dataclass
from io import BytesIO

from telebot import logger

API_URL = os.getenv("COBALT_URL")


@dataclass
class Video:
    url: str | None
    buffer: BytesIO | None
    thumbnail_url: str | None
    height: int | None
    width: int | None


HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}
DEFAULT_THUMBNAIL = "https://avatars.mds.yandex.net/i?id=f8e7cca4d77040af7b7a642f2ee39c81_l-4902542-images-thumbs&n=13"


async def download_video(session: aiohttp.ClientSession, video_data: Video) -> Video:
    async with session.get(video_data.url) as video_response:
        video_buffer = BytesIO()
        video_buffer.write(await video_response.read())
        video_buffer.seek(0)

    video_data.buffer = video_buffer

    with tempfile.NamedTemporaryFile(dir="/dev/shm") as tmp:
        tmp.write(video_buffer.getvalue())
        logger.debug(f"{tmp.name=}")

        capture = cv2.VideoCapture(tmp.name)
        _, image = capture.read()
        height, width, _ = image.shape

    video_data.height = height
    video_data.width = width
    return video_data


async def get_video(post_url: str, download: bool = True) -> Video:
    logger.debug(post_url)

    video_data = Video(
        url=None,
        buffer=None,
        thumbnail_url=DEFAULT_THUMBNAIL,
        height=None,
        width=None
    )

    async with aiohttp.ClientSession() as session:

        for _ in range(10):
            response = await session.post(
                url=API_URL,
                json={
                    "url": post_url,
                    "alwaysProxy": False,
                    "twitterGif": False  # FIXME: send an error message if only proxy mode available in inline query
                },
                headers=HEADERS
            )
            response = await response.json()

            logger.debug(response)
            video_url: str | None = response.get("url")
            if not video_url:
                await asyncio.sleep(1)
                continue

            # not sure how often this may occur
            if video_url.startswith(API_URL):
                logger.info(f"COBALT URL FOUND: {post_url=} {video_url=}")

            video_data.url = video_url
            if not download:
                return video_data

            return await download_video(session, video_data)

    # TODO: add message if couldn't get video url
    return video_data
