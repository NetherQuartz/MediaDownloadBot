import os
import tempfile
import asyncio
import subprocess
import json

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
    is_image: bool
    has_audio: bool | None


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
        tmp.flush()
        logger.debug(f"{tmp.name=}")

        capture = cv2.VideoCapture(tmp.name)
        _, image = capture.read()
        height, width, _ = image.shape
        video_data.height = height
        video_data.width = width
        video_data.is_image = not capture.grab()
        capture.release()

        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "a",
            "-show_entries", "stream=index",
            "-of", "json",
            tmp.name
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        info = json.loads(result.stdout or r"{}")
        video_data.has_audio = bool(info.get("streams"))

        if not video_data.has_audio and not video_data.is_image:
            gif_path = tmp.name + ".gif"
            convert_cmd = [
                "ffmpeg", "-y",
                "-i", tmp.name,
                "-f", "gif",
                gif_path
            ]
            subprocess.run(convert_cmd, check=True)
            with open(gif_path, "rb") as f:
                video_buffer.write(f.read())
                video_buffer.seek(0)

    logger.info(f"{video_data=}")
    return video_data


async def get_video(post_url: str, download: bool = True) -> Video:
    logger.debug(post_url)

    video_data = Video(
        url=None,
        buffer=None,
        thumbnail_url=DEFAULT_THUMBNAIL,
        height=None,
        width=None,
        is_image=False,
        has_audio=None
    )

    async with aiohttp.ClientSession() as session:

        for _ in range(10):
            response = await session.post(
                url=API_URL,
                json={
                    "url": post_url,
                    "alwaysProxy": download,
                    "convertGif": False  # FIXME: send an error message if only proxy mode available in inline query
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
