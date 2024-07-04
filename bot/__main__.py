import os
import asyncio
import re
import hashlib
import logging

import telebot

from telebot.async_telebot import AsyncTeleBot
from telebot import types

from .download import get_twitter_video, get_pinterest_video, get_instagram_video

telebot.logger.setLevel(logging.DEBUG if os.getenv("LOGGING_LEVEL") == "DEBUG" else logging.INFO)
bot = AsyncTeleBot(token=os.getenv("TOKEN"))

welcome_text = """
Hello there 👋

I can download videos from Twitter 🐦 and Pinterest 📍. Just send me twitter.com, x.com or pin.it link

Also you can add me to a group or use me in any chat with `@QuartzMediaBot <your link>`
"""


@bot.message_handler(commands=["start"])
async def start(message: types.Message) -> None:
    await bot.send_message(message.chat.id, text=welcome_text, parse_mode="markdown")


twitter_pattern = r"(?:https?://)?(?:x.com|twitter.com)/.+/status/\d+"
pinterest_pattern = r"(?:https?://)?pin.it/\w+"
instagram_pattern = r"(?:https?://)?(?:www\.)?instagram.com/\S+"


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


@bot.message_handler(regexp=pinterest_pattern)
async def download_pinterest(message: types.Message) -> None:
    progress_msg = await bot.reply_to(message, "🔎")

    url = re.findall(pinterest_pattern, message.text)[0]
    video_buffer = await get_pinterest_video(url)

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


@bot.inline_handler(lambda query: re.match(pinterest_pattern, query.query))
async def inline_download_pinterest(query: types.InlineQuery) -> None:
    url = re.findall(pinterest_pattern, query.query)[0]
    video = await get_pinterest_video(url, return_url=True)

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


@bot.message_handler(regexp=instagram_pattern)
async def download_instagram(message: types.Message) -> None:
    progress_msg = await bot.reply_to(message, "🔎")

    url = re.findall(instagram_pattern, message.text)[0]
    video_buffer = await get_instagram_video(url)

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


@bot.inline_handler(lambda query: re.match(instagram_pattern, query.query))
async def inline_download_instagram(query: types.InlineQuery) -> None:
    url = re.findall(instagram_pattern, query.query)[0]
    video = await get_instagram_video(url, return_url=True)

    if video:
        await bot.answer_inline_query(
            query.id,
            results=[
                types.InlineQueryResultVideo(
                    id=hashlib.md5(video.video_url.encode()).hexdigest(),
                    video_url=video.video_url,
                    mime_type="video/mp4",
                    thumbnail_url="",
                    title="Click here to send"
                )
            ]
        )


asyncio.run(bot.infinity_polling())
