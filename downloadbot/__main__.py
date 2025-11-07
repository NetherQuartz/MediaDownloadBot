import os
import asyncio
import re
import hashlib
import logging

import telebot

from telebot.async_telebot import AsyncTeleBot
from telebot import types

from .download import get_video

telebot.logger.setLevel(logging.DEBUG if os.getenv("LOGGING_LEVEL") == "DEBUG" else logging.INFO)
bot = AsyncTeleBot(token=os.getenv("TOKEN"))

welcome_text = """
Hello there 👋

I can download videos from X/Twitter 🐦, Pinterest 📍, Instagram 📸 and TikTok ♪. Just send me a link

Also you can add me to a group or use me in any chat with `@QuartzMediaBot <your link>`
"""


@bot.message_handler(commands=["start"])
async def start(message: types.Message) -> None:
    await bot.send_message(message.chat.id, text=welcome_text, parse_mode="markdown")


twitter_pattern = r"(?:https?://)?(?:x\.com|twitter\.com)/.+/status/\d+"
pinterest_pattern = r"(?:https?://)?(?:www\.)?(?:\w+\.)?(?:pin\.it|pinterest\.com)/\S+"
instagram_pattern = r"(?:https?://)?(?:www\.)?instagram\.com/\S+"
tiktok_pattern = r"(?:https?://)?(?:www\.)?(?:\w+\.)?tiktok\.com/\S+"

combined_pattern = "|".join([twitter_pattern, pinterest_pattern, instagram_pattern, tiktok_pattern])


@bot.message_handler(regexp=combined_pattern)
async def download_video(message: types.Message) -> None:
    progress_msg = await bot.reply_to(message, "🔎")
    try:
        url = re.findall(combined_pattern, message.text)[0]
        video = await get_video(url)

        if video.buffer:
            if not video.is_image and video.has_audio:
                telebot.logger.debug("Sending video")
                await bot.send_video(
                    message.chat.id,
                    video=video.buffer,
                    height=video.height,
                    width=video.width,
                    supports_streaming=True,
                    reply_parameters=types.ReplyParameters(message_id=message.id)
                )
            elif video.is_image:
                telebot.logger.debug("Sending photo")
                await bot.send_photo(
                    message.chat.id,
                    photo=video.buffer,
                    reply_parameters=types.ReplyParameters(message_id=message.id)
                )
            elif not video.has_audio:
                telebot.logger.debug("Sending gif")
                await bot.send_animation(
                    message.chat.id,
                    animation=video.buffer,
                    height=video.height,
                    width=video.width,
                    reply_parameters=types.ReplyParameters(message_id=message.id)
                )
        elif message.chat.type == "private":
            await bot.reply_to(message, text="It seems not to be a link to video 😔")

    except Exception as e:
        telebot.logger.exception(e)
        await bot.reply_to(message, text="⚠️ An error occured, please contact the administrator")

    await bot.delete_message(message.chat.id, progress_msg.id)


@bot.inline_handler(lambda query: re.match(combined_pattern, query.query))
async def inline_download_instagram(query: types.InlineQuery) -> None:
    url = re.findall(combined_pattern, query.query)[0]
    video = await get_video(url, download=False)

    await bot.answer_inline_query(
        query.id,
        results=[
            types.InlineQueryResultVideo(
                id=hashlib.md5(video.url.encode()).hexdigest(),
                video_url=video.url,
                mime_type="video/mp4",
                thumbnail_url=video.thumbnail_url,
                title="Click here to send"
            )
        ]
    )


if __name__ == "__main__":
    asyncio.run(bot.infinity_polling())
