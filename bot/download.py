import os

import urllib.parse

import aiohttp

from dataclasses import dataclass
from io import BytesIO
from bs4 import BeautifulSoup

from telebot import logger


@dataclass
class WebVideo:
    video_url: str
    thumbnail_url: str


async def download_video(session: aiohttp.ClientSession, url: str) -> BytesIO:
    async with session.get(url) as video_response:
        video_buffer = BytesIO()
        video_buffer.write(await video_response.read())
        video_buffer.seek(0)

    return video_buffer


async def get_twitter_video(tweet_url: str, return_url: bool = False) -> BytesIO | WebVideo | None:

    tweet_url = urllib.parse.quote(tweet_url, safe="")
    query_url = f"https://twitsave.com/info?url={tweet_url}"

    async with aiohttp.ClientSession() as session, session.get(query_url) as response:
        text = await response.text()
        data = BeautifulSoup(text, "html.parser")

        if return_url:
            videos = data.find_all("video", class_="aspect-video")
            if not videos:
                return None
            return WebVideo(video_url=videos[0].get("src"), thumbnail_url=videos[0].get("poster"))

        download_button_candidates = data.find_all("div", class_="origin-top-right")
        if download_button_candidates:
            download_button = download_button_candidates[0]
        else:
            return None
        quality_buttons = download_button.find_all("a")
        highest_quality_url = quality_buttons[0].get("href")

        return await download_video(session, highest_quality_url)


async def get_pinterest_video(pin_url: str, return_url: bool = False) -> BytesIO | WebVideo | None:

    pin_url = urllib.parse.quote(pin_url, safe="")
    query_url = f"https://dlpanda.com/ru/pinterest?url={pin_url}"

    async with aiohttp.ClientSession() as session, session.get(query_url) as response:

        text = await response.text()
        data = BeautifulSoup(text, "html.parser")

        video_div = data.find_all("div", class_="card-body")
        if not video_div:
            return None

        videos = video_div[0].find_all("source", attrs={"type": "video/mp4"})
        if not videos:
            return None
        video_url = videos[0].get("src")

        if return_url:
            thumbnail_url = video_div[0].find_all("img")[0].get("src")
            return WebVideo(video_url=video_url, thumbnail_url=thumbnail_url)

        return await download_video(session, video_url)


async def get_pinterest_video_api(pin_url: str, return_url: bool = False) -> BytesIO | WebVideo | None:

    url = "https://pinterest-video-and-image-downloader.p.rapidapi.com/pinterest"
    querystring = {"url": pin_url}
    headers = {
        "x-rapidapi-key": os.getenv("RAPIDAPI_TOKEN"),
        "x-rapidapi-host": "pinterest-video-and-image-downloader.p.rapidapi.com"
    }
    logger.debug(f"{pin_url=}")
    async with aiohttp.ClientSession() as session, session.get(url, headers=headers, params=querystring) as response:
        data = await response.json()
        logger.debug(data)
        if not data:
            return await get_pinterest_video(pin_url, return_url)
        data = data.get("data", {})
        video_url = data.get("url")
        thumbnail_url = data.get("thumbnail", "")

        if not video_url:
            return await get_pinterest_video(pin_url, return_url)

        if return_url:
            return WebVideo(video_url=video_url, thumbnail_url=thumbnail_url)

        return await download_video(session, video_url)


async def get_tiktok_video(tiktok_url: str, return_url: bool = False) -> BytesIO | WebVideo | None:
    url = "https://all-video-downloader1.p.rapidapi.com/tiktokdl"
    payload = f"-----011000010111000001101001\r\nContent-Disposition: form-data; name=\"url\"\r\n\r\n{tiktok_url}\r\n-----011000010111000001101001--\r\n\r\n"
    headers = {
        "x-rapidapi-key": os.getenv("RAPIDAPI_TOKEN"),
        "x-rapidapi-host": "all-video-downloader1.p.rapidapi.com",
        "Content-Type": "multipart/form-data; boundary=---011000010111000001101001"
    }
    logger.debug(f"{tiktok_url=}")
    async with aiohttp.ClientSession() as session, session.post(url, data=payload, headers=headers) as response:

        data = await response.json()
        logger.debug(data)
        if not data:
            return None
        data = data.get("result", {}).get("data", {})
        video_url = data.get("play")
        thumbnail_url = data.get("cover")
        if not video_url:
            return None

        if return_url:
            return WebVideo(video_url=video_url, thumbnail_url=thumbnail_url)

        return await download_video(session, video_url)


async def get_instagram_video(instagram_url: str, return_url: bool = False) -> BytesIO | WebVideo | None:

    url = "https://all-media-downloader.p.rapidapi.com/download"
    payload = f"-----011000010111000001101001\r\nContent-Disposition: form-data; name=\"url\"\r\n\r\n{instagram_url}\r\n-----011000010111000001101001--\r\n\r\n"
    headers = {
        'x-rapidapi-key': os.getenv("RAPIDAPI_TOKEN"),
        'x-rapidapi-host': "all-media-downloader.p.rapidapi.com",
        'Content-Type': "multipart/form-data; boundary=---011000010111000001101001"
    }
    logger.debug(f"{instagram_url=}")
    async with aiohttp.ClientSession() as session, session.post(url, data=payload, headers=headers) as response:

        data = await response.json()
        logger.debug(data)
        if not data:
            return None
        video_url = data[0]

        if return_url:
            return WebVideo(video_url=video_url, thumbnail_url=None)

        return await download_video(session, video_url)
