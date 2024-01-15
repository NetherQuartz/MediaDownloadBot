import urllib.parse

import aiohttp

from dataclasses import dataclass

from io import BytesIO
from bs4 import BeautifulSoup


@dataclass
class WebVideo:
    video_url: str
    thumbnail_url: str


async def download_video(session: aiohttp.ClientSession(), url: str) -> BytesIO:
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
