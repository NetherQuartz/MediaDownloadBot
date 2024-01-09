import urllib.parse

import aiohttp

from io import BytesIO
from bs4 import BeautifulSoup


async def get_twitter_video(tweet_url: str) -> BytesIO | None:
    
    tweet_url = urllib.parse.quote(tweet_url, safe="")
    query_url = f"https://twitsave.com/info?url={tweet_url}"
    
    async with aiohttp.ClientSession() as session, session.get(query_url) as response:
        text = await response.text()
        data = BeautifulSoup(text, "html.parser")
        download_button_candidates = data.find_all("div", class_="origin-top-right")
        if download_button_candidates:
            download_button = download_button_candidates[0]
        else:
            return None
        quality_buttons = download_button.find_all("a")
        highest_quality_url = quality_buttons[0].get("href")
    
        async with session.get(highest_quality_url) as video_response:
            video_buffer = BytesIO()
            video_buffer.write(await video_response.read())
            video_buffer.seek(0)
            
            return video_buffer
