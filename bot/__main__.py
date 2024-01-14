import os
import asyncio
import re
import hashlib
import logging

import telebot

from telebot.async_telebot import AsyncTeleBot
from telebot import types

from .download import get_twitter_video

telebot.logger.setLevel(logging.DEBUG if os.getenv("LOGGING_LEVEL") == "DEBUG" else logging.INFO)
bot = AsyncTeleBot(token=os.getenv("TOKEN"))


@bot.message_handler(commands=["start"])
async def start(message: types.Message) -> None:
    await bot.send_message(message.chat.id, "Привет")
    

twitter_pattern = r"(?:https?://)?(?:x.com|twitter.com)/.+/status/\d+"


@bot.message_handler(regexp=twitter_pattern)
async def download_twitter(message: types.Message) -> None:
    progress_msg = await bot.reply_to(message, "🔎")
    
    url = re.findall(twitter_pattern, message.text)[0]
    video_buffer = await get_twitter_video(url)
    
    if video_buffer:
        await bot.send_video(
            message.chat.id,
            video=video_buffer,
            supports_streaming=True,
            reply_to_message_id=message.id
        )
    elif message.chat.type == "private":
        await bot.reply_to(message, text="It seems not to be a link to video 😔")
    
    await bot.delete_message(message.chat.id, progress_msg.id)


@bot.inline_handler(lambda query: re.match(twitter_pattern, query.query))
async def inline_download_twitter(query: types.InlineQuery) -> None:
    url = re.findall(twitter_pattern, query.query)[0]
    video = await get_twitter_video(url, return_url=True)

    if video:
        await bot.answer_inline_query(
            query.id,
            results=[
                 types.InlineQueryResultVideo(
                    id=hashlib.md5(video.video_url.encode()).hexdigest(),
                    video_url=video.video_url,
                    mime_type="video/mp4",
                    thumbnail_url=video.thumbnail_url,
                    title="Click here to send"
                 )
            ]
        )


asyncio.run(bot.infinity_polling())
