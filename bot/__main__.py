import os
import asyncio
import re

from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message

from .download import get_twitter_video

bot = AsyncTeleBot(token=os.getenv("TOKEN"))


@bot.message_handler(commands=["start"])
async def start(message: Message) -> None:
    await bot.send_message(message.chat.id, "Привет")
    

twitter_pattern = r"(?:https?://)?(?:x.com|twitter.com)/.+/status/\d+"


@bot.message_handler(regexp=twitter_pattern)
async def download_twitter(message: Message) -> None:
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


asyncio.run(bot.infinity_polling())
