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
    skipped_download: bool
    content_type: str | None
    merge_urls: list[str] | None
    filename: str | None


HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}
DEFAULT_THUMBNAIL = "https://avatars.mds.yandex.net/i?id=f8e7cca4d77040af7b7a642f2ee39c81_l-4902542-images-thumbs&n=13"


async def download_video(session: aiohttp.ClientSession, video_data: Video) -> Video:
    async with session.get(video_data.url, headers={"Range": "bytes=0-"}) as video_response:
        logger.info(f"Response headers: {video_response.headers}")
        video_data.content_type = video_response.headers.get("Content-Type")
        logger.info(f"Content type: {video_data.content_type}")

        video_buffer = BytesIO()
        while True:
            chunk = None
            try:
                chunk = await video_response.content.readany()
            except:
                break
            if not chunk:
                break
            video_buffer.write(chunk)
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

    logger.info(f"{video_data=}")
    return video_data


async def download_and_merge_video(session: aiohttp.ClientSession, video_data: Video) -> Video:
    buffers = {}
    suffix = video_data.filename.rsplit(".")[-1] if video_data.filename else "mp4"
    logger.debug(f"{video_data.filename=} {suffix=}")
    for url in video_data.merge_urls:
        async with session.get(url, headers={"Range": "bytes=0-"}) as video_response:
            logger.info(f"Response headers: {video_response.headers}")
            video_buffer = BytesIO()
            while True:
                chunk = None
                try:
                    chunk = await video_response.content.readany()
                except:
                    break
                if not chunk:
                    break
                video_buffer.write(chunk)
            video_buffer.seek(0)

        with tempfile.NamedTemporaryFile(dir="/dev/shm") as tmp:
            tmp.write(video_buffer.getvalue())
            tmp.flush()
            logger.debug(f"{tmp.name=}")

            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                tmp.name,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            data = json.loads(result.stdout or r"{}")
            has_video = False
            has_audio = False
            for stream in data.get("streams", []):
                codec_type = stream.get("codec_type")
                if codec_type == "video":
                    has_video = True
                if codec_type == "audio":
                    has_audio = True
            if has_audio and has_video:
                video_data.buffer = video_buffer
                return video_data

            if has_audio:
                buffers["audio"] = video_buffer
            elif has_video:
                buffers["video"] = video_buffer

    logger.info(f"Buffers: {buffers.keys()}")
    if len(buffers) < 2:
        return video_data

    with (
        tempfile.NamedTemporaryFile(dir="/dev/shm", suffix=f".{suffix}") as tmp_audio,
        tempfile.NamedTemporaryFile(dir="/dev/shm", suffix=f".{suffix}") as tmp_video,
        tempfile.NamedTemporaryFile(dir="/dev/shm", suffix=f".{suffix}") as tmp_final
    ):
        tmp_audio.write(buffers["audio"].getvalue())
        tmp_audio.flush()
        tmp_video.write(buffers["video"].getvalue())
        tmp_video.flush()
        logger.debug(f"{tmp_video.name=} {tmp_audio.name=} {tmp_final.name=}")

        cmd = [
            "ffmpeg",
            "-y",
            "-i", tmp_video.name,
            "-i", tmp_audio.name,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c", "copy",
            "-shortest",
            tmp_final.name,
        ]

        subprocess.run(cmd, check=True)
        video_data.buffer = open(tmp_final.name, "rb").read()

        video_size = len(video_data.buffer) / 1e6
        logger.info("Final video size: %s MB", video_size)

        if video_size > 50:
            raise ValueError("File is too big")

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
        has_audio=None,
        skipped_download=False,
        content_type=None,
        merge_urls=None,
        filename=None,
    )

    async with aiohttp.ClientSession() as session:

        for _ in range(5):
            response = await session.post(
                url=API_URL,
                json={
                    "url": post_url,
                    "alwaysProxy": True,
                    "convertGif": False  # FIXME: send an error message if only proxy mode available in inline query
                },
                headers=HEADERS
            )
            response = await response.json()

            logger.debug(response)

            match response.get("status"):

                case "tunnel" | "redirect" if video_url := response.get("url"):
                    video_data.url = video_url

                    result_response = await session.get(video_url)
                    if result_response.status != 200:
                        continue

                    logger.debug("Headers: %s", result_response.headers)

                    video_size = int(result_response.headers.get("Content-Length", 0)) / 1e6
                    logger.info("Video size: %s MB", video_size)

                    if video_size > 50:
                        raise ValueError("File is too big")

                    if video_size > 20:
                        return await download_video(session, video_data)

                    if not download:
                        return video_data

                    return await download_video(session, video_data)

                case "local-processing" if response.get("type") == "merge":
                    video_data.merge_urls = response.get("tunnel", [])
                    video_data.filename = response.get("output", {}).get("filename")
                    return await download_and_merge_video(session, video_data)

                case _:
                    await asyncio.sleep(1)
                    continue

    # TODO: add message if couldn't get video url
    return video_data
